"""Two bounded CPU public contracts, saved inputs only; no GL."""
import json
import math
from pathlib import Path
import unittest
from water_residual_light_integral import gaussian_integral, laguerre_rule

FROZEN = Path(__file__).resolve().parents[1] / 'reports/2026-10-03-water-residual-angular/CPU-reference/actual-supplemental-oracle.json'


class LightIntegralTests(unittest.TestCase):
    def test_center_narrow_response_matches_saved_qualified_slope_integral(self):
        report = json.loads(FROZEN.read_text())
        sample = next(entry for entry in report['dense_references']
                      if entry['pixel'] == [128, 128] and entry['source'] == 'narrow')
        expected = sample['reference']['source_difference_C0']
        self.assertTrue(sample['reference']['reference_qualified'])
        observed = gaussian_integral(sample['actual_fixture'])
        for actual, wanted in zip(observed['source_difference_C0'], expected):
            self.assertLessEqual(abs(actual - wanted), 2e-6 + 2e-4 * max(abs(actual), abs(wanted)))
        self.assertTrue(observed['domain_qualified'])

    def test_positive_radial_rules_integrate_exponential_moments(self):
        for order in (8, 12, 16):
            rule = laguerre_rule(order)
            self.assertTrue(all(node > 0 and weight > 0 for node, weight in rule))
            for degree in range(2 * order):
                wanted = math.factorial(degree)
                actual = math.fsum(weight * node ** degree for node, weight in rule)
                self.assertLessEqual(abs(actual - wanted) / wanted, 1e-10)


if __name__ == '__main__':
    unittest.main()
