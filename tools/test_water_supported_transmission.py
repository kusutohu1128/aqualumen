"""Independent support/visibility arithmetic tests, not Minecraft acceptance."""
import math
import unittest
import water_supported_transmission as model

N=(-.024761740118265152,-.9978660345077515,.06041766330599785)
V=(-.21253617107868195,-.6171247363090515,-.7576183080673218)
C=(.006807451602071524,.0027949956711381674,.002802651608362794)

class SupportedTransmissionTests(unittest.TestCase):
    def test_actual_view_has_positive_supported_air_light(self):
        ctx=model.prepare(N,V,C)
        target=(.2,.15,math.sqrt(1-.2**2-.15**2))
        node=model.inverse_kernel(ctx,target)
        self.assertTrue(node['supported'])
        self.assertGreater(node['kernel'],0)
        self.assertLess(node['reconstructionError'],1e-11)
        self.assertGreater(node['maskingShadowing'],0)
        self.assertLessEqual(node['maskingShadowing'],1)

    def test_absent_direction_is_zero_not_whole_integral_error(self):
        ctx=model.prepare(N,V,C)
        self.assertEqual(model.inverse_kernel(ctx,(0,1,0))['kernel'],0)
        self.assertEqual(model.inverse_kernel(ctx,(0,-1,0))['kernel'],0)
        self.assertEqual(model.forward_kernel(ctx,0,0)['kernel'],0) # mean facet TIR

    def test_input_not_repaired(self):
        with self.assertRaises(ValueError):model.prepare(N,V,(.01,.04,.01))
        with self.assertRaises(ValueError):model.prepare(N,(0,-2,0),C)
        with self.assertRaises(ValueError):model.prepare(N,V,(0,0,0))
        with self.assertRaises(ValueError):model.inverse_kernel(model.prepare(N,V,C),(0,2,0))

    def test_exact_gaussian_masking_projection(self):
        # Standard slope sigma1, horizontal direction gives a=mean/sigma=1.
        ctx=model.prepare((0,-1,0),V,(1,0,1))
        direction=(1/math.sqrt(2),-1/math.sqrt(2),0)
        expected=math.exp(-.5)/math.sqrt(2*math.pi)-.5*math.erfc(1/math.sqrt(2))
        self.assertAlmostEqual(model.masking_lambda(ctx,direction),expected,places=14)
        self.assertEqual(model.masking_lambda(ctx,(0,-1,0)),0)
        self.assertTrue(math.isinf(model.masking_lambda(ctx,(1,0,0))))

    def test_inverse_and_forward_same_supported_node(self):
        ctx=model.prepare(N,V,C)
        t=(.2,.15,math.sqrt(1-.2**2-.15**2))
        node=model.inverse_kernel(ctx,t)
        # Jacobian and Gaussian slope density are tested independently here.
        sx,sz=node['slope']
        x=(sx-ctx['meanSlope'][0])/math.sqrt(C[0])
        z=(sz-ctx['meanSlope'][1]-C[1]/math.sqrt(C[0])*x)/math.sqrt(C[2]-C[1]**2/C[0])
        other=model.forward_kernel(ctx,x,z)
        self.assertTrue(other['supported'])
        self.assertAlmostEqual(other['transfer'],node['transfer'],places=11)
        self.assertLess(max(abs(a-b) for a,b in zip(other['target'],t)),1e-11)

    def test_near_critical_inverse_reconstruction_is_stable(self):
        ctx=model.prepare(N,V,C);u=.25
        center=math.atan2(-V[2],-V[0]);r=math.sqrt(1-u*u)
        half=math.acos((ctx['k']/ctx['eta']+V[1]*u)/(math.hypot(V[0],V[2])*r))
        phi=center+half*(1-1e-9)
        t=(r*math.cos(phi),u,r*math.sin(phi))
        node=model.inverse_kernel(ctx,t)
        self.assertTrue(node['supported'])
        self.assertLess(node['reconstructionError'],1e-10)

    def test_analytic_support_partitions_match_forward_classification(self):
        ctx=model.prepare(N,V,C)
        for x in (-3,-1,0,1,3):
            intervals=model.slope_intervals(ctx,x,8)
            for i in range(1001):
                z=-8+16*(i+.5)/1001
                covered=any(lo<z<hi for lo,hi in intervals)
                self.assertEqual(covered,model.forward_kernel(ctx,x,z)['supported'])

    def test_smith_visible_projection_area_identity(self):
        ctx=model.prepare((0,-1,0),V,(1,0,1))
        w=(1/math.sqrt(2),-1/math.sqrt(2),0)
        integral=math.fsum(weight*(1+x)*math.exp(-.5*x*x)/math.sqrt(2*math.pi)
            for x,weight in model.interval_nodes(model.legendre(64),-1,8))
        self.assertAlmostEqual(integral/(1+model.masking_lambda(ctx,w)),1,places=12)

    def test_actual_raw_view_slope_solid_angle_jacobian(self):
        ctx=model.prepare(N,V,C);t=(.2,.15,math.sqrt(1-.2**2-.15**2))
        a=(-t[2],0,t[0]);length=math.sqrt(model.dot(a,a));a=tuple(x/length for x in a)
        b=(t[1]*a[2]-t[2]*a[1],t[2]*a[0]-t[0]*a[2],t[0]*a[1]-t[1]*a[0])
        h=1e-5;derivatives=[]
        for tangent in (a,b):
            plus=tuple(math.cos(h)*t[i]+math.sin(h)*tangent[i] for i in range(3))
            minus=tuple(math.cos(h)*t[i]-math.sin(h)*tangent[i] for i in range(3))
            sp=model.inverse_kernel(ctx,plus)['slope'];sm=model.inverse_kernel(ctx,minus)['slope']
            derivatives.append(tuple((p-m)/(2*h) for p,m in zip(sp,sm)))
        numerical=abs(derivatives[0][0]*derivatives[1][1]-derivatives[0][1]*derivatives[1][0])
        analytical=model.inverse_kernel(ctx,t)['jacobian']
        self.assertLessEqual(abs(numerical-analytical),2e-8+2e-7*abs(analytical))

if __name__=='__main__':unittest.main()
