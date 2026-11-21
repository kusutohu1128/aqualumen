"""Fixed GPU-input matrix tests; no GL execution."""
import unittest
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

from water_snell_boundary_cases import fixtures


class FixedNodeInputs(unittest.TestCase):
    def test_normal_incidence_is_an_explicit_supported_control(self):
        cases = fixtures(include_saved=False)
        normal = next(case for case in cases if case['name'] == 'normal')
        self.assertEqual(normal['input'], [0., -1., 0., 0., 1., 0., 1.3329999446868896])
        self.assertTrue(normal['reference']['precision_agreement'])
        self.assertTrue(normal['reference']['physical']['supported'])

    def test_both_predeclared_boundary_families_keep_every_side_and_exponent(self):
        cases = fixtures(include_saved=False)
        self.assertEqual(len(cases), 37)
        for name in ('up', 'tilted'):
            selected = [case for case in cases if case.get('family') == name]
            self.assertEqual({(case['j'], case['side']) for case in selected},
                             {(j, side) for j in range(12, 21) for side in (-1, 1)})
            self.assertTrue(all(case['reference']['precision_agreement'] for case in selected))
            self.assertTrue(all(case['reference']['physical']['supported'] == (case['side'] == -1)
                                for case in selected))
        tilted = next(case for case in cases if case.get('family') == 'tilted'
                      and case['j'] == 13 and case['side'] == -1)
        self.assertEqual(tilted['input'][:6], [.31224989891052246, -.949999988079071, 0.,
                                            -.862316370010376, .506369948387146, 0.])

    def test_saved_six_controls_preserve_raw_inputs_and_all_48_nodes(self):
        cases = fixtures()
        self.assertEqual(len(cases), 325)
        saved = [case for case in cases if case.get('family') == 'saved']
        self.assertEqual(len(saved), 288)
        expected_pixels = {(128, 128), (132, 131), (123, 127),
                           (132, 135), (132, 127), (142, 134)}
        self.assertEqual({tuple(case['pixel']) for case in saved}, expected_pixels)
        for pixel in expected_pixels:
            group = [case for case in saved if tuple(case['pixel']) == pixel]
            self.assertEqual(len(group), 48)
            self.assertEqual({case['node'] for case in group}, set(range(48)))
            self.assertTrue(all(case['weight'] > 0 for case in group))
            self.assertTrue(all(case['reference']['precision_agreement']
                                and case['reference']['physical']['supported'] for case in group))
        self.assertTrue(all(case['input'][:3] == case['saved_fixture']['view_to_eye'] for case in saved))

    def test_public_export_links_exact_binary_inputs_to_the_reference_matrix(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-snell-cases-') as directory:
            output = Path(directory)/'new'
            command = [sys.executable, '-B', str(Path(__file__).with_name('water_snell_boundary_cases.py')),
                       '--export', str(output)]
            subprocess.run(command, check=True, capture_output=True, text=True)
            metadata = json.loads((output/'cases.json').read_text())
            raw = (output/'inputs.f32').read_bytes()
            self.assertEqual(metadata['count'], 325)
            self.assertEqual(len(raw), 325*7*4)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), metadata['inputSHA256'])
            self.assertEqual(list(struct.unpack_from('<7f', raw)), metadata['cases'][0]['input'])
            self.assertEqual(subprocess.run(command, capture_output=True, text=True).returncode, 2)


if __name__ == '__main__':
    unittest.main()
