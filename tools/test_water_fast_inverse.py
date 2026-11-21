import math
from statistics import NormalDist
import unittest
import water_fast_inverse as inverse


class QuantileTests(unittest.TestCase):
    def test_direct_small_probability_inverse_matches_true_gaussian(self):
        coefficients=inverse.fit()
        probabilities=[.5,.49,.4,.1,.01]+[10**(-i/8) for i in range(3,121)]
        for p in probabilities:
            if p>.5:continue
            self.assertAlmostEqual(inverse.tail_inverse(p,coefficients,fp32=True),-NormalDist().inv_cdf(p),delta=2e-6)

    def test_endpoints_and_nonfinite_probabilities_are_rejected_not_clamped(self):
        coefficients=inverse.fit()
        for p in (0.,1.,-.1,.6,math.nan,math.inf):
            with self.assertRaises(ValueError):inverse.tail_inverse(p,coefficients)

    def test_actual_gpu_tail_inverse_meets_same_probability_gate(self):
        import water_fast_inverse_audit as audit
        root=inverse.ROOT/'reports/2026-10-06-water-fast-inverse'
        result=audit.audit(root/'quantile-gpu-01',root/'quantile-fixture-v1')
        self.assertTrue(result['allQuantileGatesPassed'],result['failures'])


if __name__=='__main__':unittest.main()
