import math
import unittest
import water_supported_transmission as t
import water_supported_rgb_cpu as r
from test_water_supported_transmission import N,V,C

class ReflectionTests(unittest.TestCase):
    def test_source_not_assumed_black(self):
        p=t.prepare(N,V,C);node=r.reflected_forward(p,0,0)
        self.assertTrue(node['supported']);self.assertGreater(node['kernel'],0)
        self.assertGreater(node['transfer'],0)

    def test_opposite_medium_not_used(self):
        p=t.prepare(N,V,C)
        self.assertFalse(r.reflected_inverse(p,(0,1,0))['supported'])

    def test_raw_view_inverse_matches_forward(self):
        p=t.prepare(N,V,C);a=r.reflected_forward(p,.4,-.3)
        length=math.sqrt(t.dot(V,V));target=tuple(v/length for v in a['target'])
        b=r.reflected_inverse(p,target)
        self.assertTrue(b['supported']);self.assertAlmostEqual(a['transfer'],b['transfer'],places=12)
        self.assertAlmostEqual(b['slope'][0],p['meanSlope'][0]+p['rootX']*.4,places=12)

    def test_partition_independent_forward_classes(self):
        p=t.prepare(N,V,C)
        for x in (-3,-1,0,1,3):
            intervals=r.reflected_intervals(p,x,8)
            for i in range(1001):
                z=-8+16*(i+.5)/1001
                self.assertEqual(any(lo<z<hi for lo,hi in intervals),r.reflected_forward(p,x,z)['supported'])

    def test_reflection_jacobian_finite_difference(self):
        p=t.prepare(N,V,C);f=r.reflected_forward(p,.4,-.3);l=math.sqrt(t.dot(V,V));w=tuple(x/l for x in f['target'])
        a=(-w[2],0,w[0]);al=math.sqrt(t.dot(a,a));a=tuple(x/al for x in a)
        b=(w[1]*a[2]-w[2]*a[1],w[2]*a[0]-w[0]*a[2],w[0]*a[1]-w[1]*a[0]);ds=[];h=1e-5
        for axis in (a,b):
            plus=tuple(math.cos(h)*w[i]+math.sin(h)*axis[i] for i in range(3))
            minus=tuple(math.cos(h)*w[i]-math.sin(h)*axis[i] for i in range(3))
            sp=r.reflected_inverse(p,plus)['slope'];sm=r.reflected_inverse(p,minus)['slope']
            ds.append(tuple((x-y)/(2*h) for x,y in zip(sp,sm)))
        numerical=abs(ds[0][0]*ds[1][1]-ds[0][1]*ds[1][0]);actual=r.reflected_inverse(p,w)['jacobian']
        self.assertLessEqual(abs(numerical-actual),2e-8+2e-7*actual)
if __name__=='__main__':unittest.main()
