"""Public CPU arithmetic-reference tests, not shader/GPU regressions."""
import unittest
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import struct
from fractions import Fraction

from water_snell_boundary_reference import diagnose, f32


class SnellBoundaryTests(unittest.TestCase):
    def test_public_normal_incidence_reconstructs_supported_direction(self):
        result = diagnose((0, -1, 0), (0, 1, 0))
        self.assertTrue(result['physical']['supported'])
        self.assertEqual(list(map(Decimal, result['physical']['forward'])), [0, 1, 0])
        self.assertFalse(result['GPUQualified'])

    def test_fixed_supported_boundary_can_replay_float_discriminant_rejection(self):
        eta = f32(1.333)
        vy = f32(-1/eta-2**-13)
        vx = f32((1-vy*vy)**.5)
        result = diagnose((vx, vy, 0), (0, 1, 0))
        self.assertTrue(all(r['supported'] for r in result['references']))
        self.assertGreater(Decimal(result['physical']['discriminant']), 0)
        self.assertEqual(result['old_binary32']['unfused']['discriminant'], 0)
        self.assertEqual(result['classification'], 'POSITIVE_SUPPORTED_NUMERIC_REJECTION')

    def test_public_cli_exports_entire_predeclared_family_without_gpu_acceptance(self):
        command = [sys.executable, '-B', str(Path(__file__).with_name('water_snell_boundary_reference.py')), '--family']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        report = json.loads(result.stdout)
        self.assertEqual(len(report['cases']), 18)
        self.assertEqual({case['j'] for case in report['cases']}, set(range(12, 21)))
        self.assertGreater(report['positive_supported_numeric_rejections'], 0)
        self.assertTrue(all(case['result']['precision_agreement'] for case in report['cases']))
        self.assertFalse(report['GPUQualified'])

    def test_raw_binary32_negative_zero_is_preserved_without_normalizing_view(self):
        result = diagnose((0.0, -1.0, -0.0), (-0.0, 1.0, 0.0))
        self.assertEqual(result['raw_v_bits'][2], struct.pack('<f', -0.0).hex())
        self.assertEqual(result['raw_t_bits'][0], struct.pack('<f', -0.0).hex())

    def test_zero_target_is_invalid_input_not_a_physical_support_failure(self):
        result = diagnose((0, -1, 0), (0, 0, 0))
        self.assertEqual(result['classification'], 'INVALID_INPUT')
        self.assertEqual(result['physical']['reason'], 'zero_target')
        self.assertFalse(result['physical']['supported'])

    def test_precision_qualification_includes_normal_discriminant_and_jacobian(self):
        eta = f32(1.333)
        vy = f32(-1/eta-2**-13)
        result = diagnose((f32((1-vy*vy)**.5), vy, 0), (0, 1, 0))
        self.assertTrue(result['precision_agreement'])
        self.assertTrue({'normal','discriminant','jacobian_slope_per_solid_angle'} <= set(result['precision_comparisons']))
        self.assertGreater(Decimal(result['physical']['raw_cosine_transmission']), 0)

    def test_public_rounding_uses_nearest_even_at_normal_and_subnormal_ties(self):
        self.assertEqual(f32(1+Fraction(1,2**24)), 1)
        self.assertEqual(f32(1+Fraction(3,2**24)), 1+2**-22)
        self.assertEqual(f32(Fraction(1,2**150)), 0)
        self.assertEqual(f32(Fraction(3,2**150)), 2**-148)

    def test_rounded_target_interpretation_keeps_raw_view_norm_and_reconstructs(self):
        v = (f32((1-.95**2)**.5), f32(-.95), 0)
        t = (f32(-.4), f32((1-.4**2)**.5), 0)
        result = diagnose(v, t)
        self.assertEqual(result['raw_v'], list(v))
        self.assertEqual(result['raw_t'], list(t))
        self.assertNotEqual(Decimal(result['physical']['raw_v_norm_squared']), 1)
        self.assertNotEqual(Decimal(result['physical']['raw_t_norm_squared']), 1)
        self.assertTrue(result['physical']['supported'])
        self.assertLess(Decimal(result['physical']['reconstruction_error']), Decimal('1e-60'))
        self.assertTrue(result['precision_agreement'])

    def test_wrong_hemisphere_cli_rejects_as_invalid_not_physical_tir(self):
        command = [sys.executable, '-B', str(Path(__file__).with_name('water_snell_boundary_reference.py')),
                   '--v', '0', '1', '0', '--t', '0', '1', '0']
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['classification'], 'INVALID_DOMAIN')

    def test_exact_zero_replay_preserves_ieee_operation_signs(self):
        result = diagnose((-0.0,-1.0,-0.0),(-0.0,1.0,-0.0))
        for replay in result['old_binary32'].values():
            self.assertEqual(struct.pack('<f',replay['normal'][0]),struct.pack('<f',-0.0))


if __name__ == '__main__':
    unittest.main()
