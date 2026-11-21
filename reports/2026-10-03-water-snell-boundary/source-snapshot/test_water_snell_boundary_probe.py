"""Public CPU CLI tracer; compiles the literal authored GLSL function."""
import json
from decimal import Decimal
import math
from pathlib import Path
import subprocess
import struct
import tempfile
import unittest

from tools.water_snell_boundary_reference import diagnose, family

ROOT = Path(__file__).resolve().parents[1]


class SnellNodeHostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='aqualumen-snell-host-')
        cls.addClassCleanup(cls.directory.cleanup)
        cls.binary = Path(cls.directory.name) / 'water_snell_boundary_probe'
        compiled = subprocess.run([
            'g++', '-std=c++17', '-O2', '-fno-fast-math', '-ffp-contract=off',
            '-fsingle-precision-constant',
            str(ROOT / 'tools/water_snell_boundary_probe.cpp'), '-o', str(cls.binary),
        ], capture_output=True, text=True)
        if compiled.returncode:
            raise RuntimeError(compiled.stderr)

    def run_node(self, view, target, eta='1.333'):
        result = subprocess.run([
            str(self.binary), '--node', *(str(x) for x in view),
            *(str(x) for x in target), eta,
        ], check=True, capture_output=True, text=True)
        return json.loads(result.stdout)

    def test_normal_incidence_has_positive_transmission_and_upward_ray(self):
        result = self.run_node((0, -1, 0), (0, 1, 0))
        self.assertTrue(result['CPUOnly'])
        self.assertFalse(result['nativeGLExecuted'])
        self.assertEqual(result['viewBits'], ['00000000', 'bf800000', '00000000'])
        node = result['candidate']
        self.assertEqual(node['status'], 1)
        self.assertEqual(node['facet'], [0, -1, 0])
        self.assertEqual(node['ray'], [0, 1, 0])
        self.assertGreater(node['transmission'], 0.97)
        self.assertLess(node['transmission'], 0.99)
        self.assertGreater(node['jacobian'], 0)

    def test_supported_tilted_critical_node_matches_independent_reference(self):
        view = (0.31224989891052246, -0.949999988079071, 0.0)
        target = (-0.862316370010376, 0.506369948387146, 0.0)
        reference = diagnose(view, target)
        self.assertTrue(reference['precision_agreement'])
        physical = reference['physical']
        self.assertTrue(physical['supported'])
        # Decimal normalizes only the generated direction, never the raw view.
        result = self.run_node(view, target)
        self.assertEqual(result['view'], list(view))
        self.assertEqual(result['generatedTargetInput'], list(target))
        node = result['candidate']
        self.assertEqual(node['status'], 1)
        for value, expected in zip(node['ray'], physical['forward']):
            self.assertLessEqual(abs(value-float(expected)), 1e-7)
        transmission = float(1-Decimal(physical['raw_cosine_fresnel']))
        jacobian = float(physical['jacobian_slope_per_solid_angle'])
        self.assertGreater(transmission, 0)
        self.assertGreater(jacobian, 0)
        self.assertLessEqual(abs(node['transmission']-transmission), 2e-4*transmission)
        self.assertLessEqual(abs(node['jacobian']-jacobian), 2e-4*jacobian)

    def test_proved_absent_downward_facet_is_zero_not_numeric_failure(self):
        view, target = (1, -0.5, 0), (0, 1, 0)
        reference = diagnose(view, target)
        self.assertTrue(reference['precision_agreement'])
        self.assertFalse(reference['physical']['supported'])
        node = self.run_node(view, target)['candidate']
        self.assertEqual(node['status'], 0)
        self.assertEqual(node['transmission'], 0)
        self.assertEqual(node['jacobian'], 0)

    def test_zero_generated_target_is_invalid_not_absent_sunlight(self):
        node = self.run_node((0, -1, 0), (0, 0, 0))['candidate']
        self.assertEqual(node['status'], -1)

    def test_fixed_tilted_family_preserves_both_supported_and_absent_sides(self):
        # Predeclared cpu-math/NOTE.md family; no target or threshold search.
        round32 = lambda x: struct.unpack('<f', struct.pack('<f', x))[0]
        view = (0.31224989891052246, -0.949999988079071, 0.0)
        eta = round32(1.333)
        norm = math.sqrt(math.fsum(x*x for x in view))
        k = math.sqrt(1+eta*eta*(norm*norm-1))
        direction = tuple(x/norm for x in view)
        perpendicular = (-view[1]/norm, view[0]/norm, 0.0)
        for j in range(12, 21):
            for side in (-1, 1):
                with self.subTest(j=j, side=side):
                    cosine = (-k/eta+side*2**-j)/norm
                    sine = math.sqrt(1-cosine*cosine)
                    target = tuple(round32(cosine*x-sine*y)
                                   for x, y in zip(direction, perpendicular))
                    if j == 13 and side == -1:
                        self.assertEqual(target,
                            (-0.862316370010376, 0.506369948387146, 0.0))
                    reference = diagnose(view, target)
                    self.assertTrue(reference['precision_agreement'])
                    physical = reference['physical']
                    self.assertEqual(physical['supported'], side == -1)
                    result = self.run_node(view, target)
                    self.assertEqual(result['view'], list(view))
                    self.assertEqual(result['generatedTargetInput'], list(target))
                    node = result['candidate']
                    self.assertEqual(node['status'], 1 if side == -1 else 0)
                    if side == 1:
                        self.assertEqual(node['transmission'], 0)
                        self.assertEqual(node['jacobian'], 0)
                        continue
                    for value, expected in zip(node['ray'], physical['forward']):
                        self.assertLessEqual(abs(value-float(expected)), 1e-7)
                    transmission = float(1-Decimal(physical['raw_cosine_fresnel']))
                    jacobian = float(physical['jacobian_slope_per_solid_angle'])
                    self.assertGreater(transmission, 0)
                    self.assertGreater(jacobian, 0)
                    self.assertLessEqual(abs(node['transmission']-transmission),
                                         2e-4*transmission)
                    self.assertLessEqual(abs(node['jacobian']-jacobian),
                                         2e-4*jacobian)

    def test_fixed_up_family_preserves_near_horizontal_support_boundary(self):
        # Public reference generator uses correctly rounded binary32 sqrt.
        cases = family()['cases']
        self.assertEqual(len(cases), 18)
        for case in cases:
            with self.subTest(j=case['j'], side=case['side']):
                reference = case['result']
                self.assertTrue(reference['precision_agreement'])
                physical = reference['physical']
                self.assertEqual(physical['supported'], case['side'] == -1)
                result = self.run_node(reference['raw_v'], reference['raw_t'])
                self.assertEqual(result['view'], reference['raw_v'])
                self.assertEqual(result['generatedTargetInput'], reference['raw_t'])
                node = result['candidate']
                self.assertEqual(node['status'], 1 if physical['supported'] else 0)
                if not physical['supported']:
                    self.assertEqual(node['transmission'], 0)
                    self.assertEqual(node['jacobian'], 0)
                    continue
                for value, expected in zip(node['ray'], physical['forward']):
                    self.assertLessEqual(abs(value-float(expected)), 1e-7)
                transmission = float(1-Decimal(physical['raw_cosine_fresnel']))
                jacobian = float(physical['jacobian_slope_per_solid_angle'])
                self.assertLessEqual(abs(node['transmission']-transmission),
                                     2e-4*transmission)
                self.assertLessEqual(abs(node['jacobian']-jacobian), 2e-4*jacobian)


if __name__ == '__main__':
    unittest.main()
