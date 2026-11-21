"""Synthetic audit-plumbing contracts, not shader/native numerical evidence."""
import unittest
from water_residual_light_integral import gaussian_integral
from water_residual_light_audit import classify,source_reference,erase_blocks,controlled_source


class LightAuditTests(unittest.TestCase):
    def test_unsupported_domain_is_not_success_and_valid_missing_apply_is_red(self):
        self.assertEqual(classify(False, [False]), 'INCONCLUSIVE')
        self.assertEqual(classify(True, [False]), 'RED')
        self.assertEqual(classify(True, [True]), 'PASS')

    def test_cached_math_replays_the_frozen_public_integrator_without_mutation(self):
        fixture=dict(mean_normal=(0.,-1.,0.),view_to_eye=(0.,-1.,0.),covariance=(.0064,0.,.0064))
        actual=source_reference(fixture)
        expected=gaussian_integral(fixture)['source_difference_C0']
        self.assertGreater(actual[0],.001)
        for x,y in zip(actual,expected):self.assertAlmostEqual(x,y,places=13)

    def test_source_recovery_rejects_orphan_marker_instead_of_false_success(self):
        recovered,count=erase_blocks('a BEGINpayloadEND b BEGINpayloadEND','BEGIN','END')
        self.assertEqual((recovered,count),('a  b ',2))
        with self.assertRaises(ValueError):erase_blocks('a BEGINpayload','BEGIN','END')

    def test_controlled_source_is_the_exact_public_fixed_peak_chord_input(self):
        narrow=controlled_source(1)
        self.assertIn('vec3(0.25,0.125,0.0625)*exp(-dot(normalize(ray)',narrow)
        self.assertIn('2.0*0.0046499999999999996*0.0046499999999999996',narrow)
        self.assertIn('2.0*0.080000000000000002*0.080000000000000002',controlled_source(2))
        self.assertIn('sampleSky(lut,ray)+vec3(0.0);',controlled_source(4))


if __name__ == '__main__':
    unittest.main()
