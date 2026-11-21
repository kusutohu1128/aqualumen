"""Selected saved-output arithmetic contracts; CPU only."""
import unittest
from water_residual_angular_reference import finite_rule
from water_residual_angular_oracle import compare_observation


class AngularOracleTests(unittest.TestCase):
    def test_independent_comparison_rejects_coefficients_outside_declared_gate(self):
        fixture = dict(mean_normal=(0., -1., 0.), covariance=(.0064, 0., .0064),
                       view_to_eye=(0., -1., 0.))
        source = {'kind': 'constant'}
        truth = finite_rule(fixture, source, 3)
        self.assertTrue(compare_observation(fixture, source, 3, truth['coefficients'],
                                            truth['source_difference_C0'])['accepted'])
        changed = list(truth['coefficients'])
        changed[1] += 3e-5
        self.assertFalse(compare_observation(fixture, source, 3, changed,
                                             truth['source_difference_C0'])['accepted'])

    def test_C0_gate_rejects_a_large_delta_and_nonfinite_observation(self):
        fixture = dict(mean_normal=(0., -1., 0.), covariance=(0., 0., 0.),
                       view_to_eye=(0., -1., 0.))
        source = {'kind': 'constant'}
        truth = finite_rule(fixture, source, 3)
        for perturbation in (1e-4, float('nan')):
            changed = list(truth['source_difference_C0'])
            changed[0] += perturbation
            self.assertFalse(compare_observation(fixture, source, 3, truth['coefficients'],
                                                 changed)['accepted'])


if __name__ == '__main__':
    unittest.main()
