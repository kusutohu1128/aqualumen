"""CPU-only public numerical contracts; no GL or production source edits."""
import math
import unittest

from water_residual_angular_reference import standard_normal_rule, finite_rule, reference


class AngularReferenceTests(unittest.TestCase):
    def test_zero_covariance_constant_source_matches_closed_normal_fresnel(self):
        fixture = dict(mean_normal=(0., -1., 0.), covariance=(0., 0., 0.),
                       view_to_eye=(0., -1., 0.))
        result = finite_rule(fixture, {'kind': 'constant'}, 3)
        expected = ((1.333 - 1) / (1.333 + 1)) ** 2
        self.assertTrue(result['sampled_domain_valid'])
        self.assertAlmostEqual(result['coefficients'][0], 1., places=13)
        self.assertAlmostEqual(result['coefficients'][1], expected, places=13)
        self.assertAlmostEqual(result['source_transfer'], 1 - expected, places=13)

    def test_narrow_chord_source_integrates_between_sparse_nodes(self):
        fixture = dict(mean_normal=(0., -1., 0.), covariance=(.0064, 0., .0064),
                       view_to_eye=(0., -1., 0.))
        source = {'kind': 'gaussian', 'sigma': .00465}
        dense = reference(fixture, source)
        sparse = finite_rule(fixture, source, 3)
        self.assertTrue(dense['converged'])
        self.assertTrue(dense['finite_window_domain_qualified'])
        self.assertGreater(dense['source_transfer'], .001)
        self.assertLess(dense['source_transfer'], .1)
        self.assertGreater(sparse['source_transfer'] - dense['source_transfer'], .2)
        self.assertLess(dense['outside_window_C0_absolute_bound'], 2e-9)

    def test_sparse_validity_does_not_override_dense_domain_rejection(self):
        fixture = dict(mean_normal=(0., -1., 0.), covariance=(.1, 0., .1),
                       view_to_eye=(0., -1., 0.))
        self.assertTrue(finite_rule(fixture, {'kind': 'constant'}, 3)['sampled_domain_valid'])
        dense = reference(fixture, {'kind': 'constant'})
        self.assertFalse(dense['finite_window_domain_qualified'])
        self.assertGreater(dense['invalid_sample_count'], 0)
        self.assertFalse(dense['reference_qualified'])

    def test_invalid_source_parameters_are_rejected_even_when_all_nodes_tir(self):
        angle = math.radians(66)
        fixture = dict(mean_normal=(0., -1., 0.), covariance=(0., 0., 0.),
                       view_to_eye=(-math.sin(angle), -math.cos(angle), 0.))
        with self.assertRaises(ValueError):
            finite_rule(fixture, {'kind': 'gaussian', 'sigma': float('nan')}, 3)

    def test_rules_integrate_standard_normal_moments(self):
        for order in (3, 9, 17):
            rule = standard_normal_rule(order)
            self.assertEqual(len(rule), order)
            self.assertTrue(all(weight > 0 for _, weight in rule))
            for degree in range(2 * order):
                observed = math.fsum(weight * node ** degree for node, weight in rule)
                expected = 0.0 if degree % 2 else math.prod(range(1, degree, 2))
                self.assertLessEqual(abs(observed - expected),
                                     1e-11 * max(1.0, abs(expected)))


if __name__ == '__main__':
    unittest.main()
