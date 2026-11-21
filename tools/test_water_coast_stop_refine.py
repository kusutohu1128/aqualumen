import unittest
from water_coast_stop_pack import ROOT,transform
from water_coast_stop_refine import increase


class UpperBudgetTest(unittest.TestCase):
    def test_exact_single_variable_reversal(self):
        original={p.relative_to(ROOT).as_posix():p.read_bytes() for p in sorted([*(ROOT/'shaders').rglob('*'),ROOT/'LICENSE']) if p.is_file()}
        baseline=transform(original)['shaders/gbuffers_water.fsh'].decode()
        changed=increase(baseline)
        recovered=changed.replace('(upperSurface ? 32 : 8)','(upperSurface ? 9 : 8)').replace('i==31','i==8')
        self.assertEqual(recovered,baseline)
        self.assertIn('(upperSurface ? 32 : 8)',changed)
        for old in ('max(0.04,travel*0.025)','receiver.z > origin.z + 0.025','> surfaceY + 0.08'):
            self.assertIn(old,changed)


if __name__=='__main__':unittest.main()
