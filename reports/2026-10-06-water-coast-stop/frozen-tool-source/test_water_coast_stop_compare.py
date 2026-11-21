"""Reader regressions using the saved actual observer records, not GPU tests."""
import json
import unittest
from water_coast_stop_pack import OUT
from water_coast_stop_compare import compare

class Comparison(unittest.TestCase):
    def setUp(self):
        self.a,self.b=[json.loads((OUT/n).read_text()) for n in
            ('selected-raw-audit.json','selected-raw-refine32-audit.json')]
    def test_actual_negative_ablation(self):
        self.assertFalse(compare(self.a,self.b)['increasingBudgetAloneResolvesSelectedDiscontinuity'])
    def test_rejects_residual_as_hit(self):
        self.b['points'][0]['finalResidual']=0
        with self.assertRaises(AssertionError): compare(self.a,self.b)
    def test_rejects_mismatched_texel(self):
        self.b['points'][0]['texel']=[0,0]
        with self.assertRaises(AssertionError): compare(self.a,self.b)

if __name__=='__main__': unittest.main()
