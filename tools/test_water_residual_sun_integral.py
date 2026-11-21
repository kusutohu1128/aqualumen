"""Public CPU units/integral tests; not GLSL, pixel coverage, or adoption."""
import unittest
from water_residual_sun_integral import solar_beam,cap_projected_irradiance,sun_integral,legendre_rule
from water_residual_light_integral import light_kernel


class SunIntegralTests(unittest.TestCase):
    def test_off_axis_cap_integrates_to_the_once_weathered_perpendicular_beam(self):
        beam=solar_beam((.5,.25,.125),.4)
        expected=(9*.66,4.4*.66,2.125*.66)
        actual=cap_projected_irradiance(beam,(.2,1.,-.13))
        for value,target in zip(actual,expected):
            self.assertLessEqual(abs(value-target),2e-13*abs(target))

    def test_smooth_cap_has_a_positive_resolved_response_not_a_point_or_zero(self):
        fixture=dict(mean_normal=(0.,-1.,0.),view_to_eye=(0.,-1.,0.),covariance=(.0064,0.,.0064))
        center=light_kernel(fixture,(0.,1.,0.))['kernel']
        result=sun_integral(fixture,(0.,1.,0.),(1.,.5,.25))
        self.assertTrue(result['domain_qualified'])
        self.assertGreater(result['source_difference_C0'][0],.9*center)
        self.assertLess(result['source_difference_C0'][0],.9999*center)
        self.assertEqual(result['source_difference_C0'][1],result['source_difference_C0'][0]/2)
        self.assertEqual(result['source_difference_C0'][2],result['source_difference_C0'][0]/4)

    def test_positive_radial_rules_preserve_q_moments_without_renormalization(self):
        import math
        for order in (4,8,12):
            rule=legendre_rule(order)
            self.assertTrue(all(0<q<1 and weight>0 for q,weight in rule))
            for degree in range(2*order):
                self.assertLessEqual(abs(math.fsum(weight*q**degree for q,weight in rule)-1/(degree+1)),2e-14)

    def test_unsupported_covariance_rejects_whole_source_without_mutating_inputs(self):
        fixture=dict(mean_normal=[0.,-1.,0.],view_to_eye=[0.,-.99999998,0.],covariance=[.0064,0.,0.])
        saved={key:list(value) for key,value in fixture.items()}
        result=sun_integral(fixture,(.1,1.,-.1),(1.,.5,.25))
        self.assertFalse(result['domain_qualified'])
        self.assertIsNone(result['source_difference_C0'])
        self.assertEqual(fixture,saved)


if __name__=='__main__':unittest.main()
