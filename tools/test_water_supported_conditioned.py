"""Correct-density tests of conditioned Gaussian support, not shader acceptance."""
import json
import math
from pathlib import Path
import unittest
import water_supported_conditioned as conditioned

ROOT=Path(__file__).resolve().parents[1]


class ConditionalProposalTests(unittest.TestCase):
    def test_half_gaussian_retains_half_mass(self):
        for u in (.01,.2,.5,.9,.99):
            z,mass=conditioned.conditional_z([(-8.,0.)],u)
            self.assertLess(z,0.)
            self.assertAlmostEqual(mass,.5,delta=1e-14)
        # Conditional density divides by mass; the estimator must multiply
        # by that same mass. A survivor-normalized result of1 is wrong.

    def test_disjoint_support_uses_known_probability_not_sample_counts(self):
        intervals=[(-2.,-1.),(1.,3.)]
        expected=conditioned.gaussian_mass(-2,-1)+conditioned.gaussian_mass(1,3)
        for u in (.02,.31,.6,.99):
            z,mass=conditioned.conditional_z(intervals,u)
            self.assertTrue(any(lo<z<hi for lo,hi in intervals))
            self.assertEqual(mass,expected)
        self.assertEqual(conditioned.conditional_z([], .5),(0.,0.))

    def test_positive_far_tail_does_not_subtract_from_one(self):
        mass=conditioned.gaussian_mass(7,8)
        self.assertGreater(mass,0)
        expected=.5*(math.erfc(7/math.sqrt(2))-math.erfc(8/math.sqrt(2)))
        self.assertEqual(mass,expected)
        z,p=conditioned.conditional_z([(7,8)],.4)
        self.assertTrue(7<z<8)
        self.assertEqual(p,mass)

    def test_retained_old_prototype_is_not_converged(self):
        old=json.loads((ROOT/'reports/2026-10-06-water-supported-sources/sampling-cpu-4096.json').read_text())
        self.assertTrue(all(p['branches'][0]['absoluteError']>
            2e-6+2e-4*p['branches'][0]['reference'] for p in old['points']))


if __name__=='__main__':unittest.main()
