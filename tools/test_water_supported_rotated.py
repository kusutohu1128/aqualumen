import json
import math
import unittest
import water_supported_rotated as r


class RotatedProposalTests(unittest.TestCase):
    def context(self):
        a=json.loads((r.c.ROOT/'reports/2026-10-06-water-supported-transmission/actual-iris-inputs.json').read_text())['points'][2]['raw']
        return r.c.t.prepare(a['normal'][:3],a['view'][:3],a['covariance'][:3])

    def test_covariance_exact_orthogonal_coordinates(self):
        p=self.context();q,b=r.basis(p)
        self.assertAlmostEqual(q[0]*q[3]-q[1]*q[2],1,delta=1e-15)
        for actual,want in ((sum(v*v for v in b[0]),p['covariance'][0]),
            (sum(a*z for a,z in zip(b[0],b[1])),p['covariance'][1]),
            (sum(v*v for v in b[1]),p['covariance'][2])):
            self.assertAlmostEqual(actual,want,delta=2e-18)
        for x,z in ((.7,-.9),(-2,1.4),(0,0)):
            ox=q[0]*x+q[1]*z;oz=q[2]*x+q[3]*z
            self.assertAlmostEqual(ox*ox+oz*oz,x*x+z*z,delta=2e-15)

    def test_general_partition_matches_independent_forward_nodes(self):
        p=self.context();q,b=r.basis(p)
        for branch in (0,1):
            for i in range(21):
                x=-5+i*.5;parts=r.intervals(p,q,b,x,branch)
                for j in range(51):
                    z=-5+j*.2
                    contained=any(lo<z<hi for lo,hi in parts)
                    self.assertEqual(contained,r.node(p,q,x,z,branch)['supported'],(branch,x,z,parts))


if __name__=='__main__':unittest.main()
