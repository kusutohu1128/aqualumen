import math
import unittest
import water_supported_probability_rule as rule


class ProbabilityRuleTests(unittest.TestCase):
    def test_rule_keeps_known_probability_and_never_fits_survivors(self):
        nodes=rule.probability_rule(16)
        self.assertAlmostEqual(math.fsum(w for u,w in nodes),1.,delta=2e-14)
        self.assertTrue(all(0<u<1 and w>0 for u,w in nodes))
        constant=math.fsum(.5*w for u,w in nodes)
        self.assertAlmostEqual(constant,.5,delta=2e-14)


if __name__=='__main__':unittest.main()
