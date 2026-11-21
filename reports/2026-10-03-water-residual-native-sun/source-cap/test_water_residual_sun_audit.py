"""Public CPU audit plumbing; not actual shader/model regression evidence."""
import unittest
from water_residual_sun_audit import central_source_response,audit_sample
from water_residual_sun_integral import sun_integral


def point():
    return dict(C0=[0.,0.,0.],scatter=[0.,0.,0.],mean_normal=[0.,-1.,0.],
        covariance=[.0064,0.,.0064],view_to_eye=[0.,-1.,0.],coefficients=[1.,.02,.98,0.],
        WR_status=[1.,1.,.95,0.],flags=[1.,1.,1.,1.],eligible=1.,requested=1.,applied=0.,
        footprint=.035,sky_qualified=True)


class SunAuditTests(unittest.TestCase):
    def test_measured_reflected_scatter_is_removed_not_counted_as_solar_transmission(self):
        positive=(2.15,1.5,1.15);zero=(.1,.4,.5)
        response=central_source_response(positive,zero,.125,(.4,.8,1.2),(0.,0.,0.))
        for actual,expected in zip(response,(2.,1.,.5)):
            self.assertAlmostEqual(actual,expected,places=14)

    def test_wrong_legacy_domain_is_inconclusive_not_a_solar_success(self):
        bad=point();bad['WR_status']=[0.,0.,1.,0.]
        report=audit_sample(bad,bad,(0.,1.,0.),(1.,.5,.25),1)
        self.assertEqual(report['status'],'INCONCLUSIVE')

    def test_qualified_correct_numbers_cannot_hide_missing_actual_application(self):
        positive,zero=point(),point();beam=(1.,.5,.25)
        positive['C0']=sun_integral(positive,(0.,1.,0.),beam)['source_difference_C0']
        report=audit_sample(positive,zero,(0.,1.,0.),beam,1)
        self.assertEqual(report['status'],'RED')

    def test_positive_source_application_requires_numerical_match_and_zero_control(self):
        positive,zero=point(),point();beam=(1.,.5,.25)
        positive['C0']=sun_integral(positive,(0.,1.,0.),beam)['source_difference_C0']
        positive['applied']=1.
        self.assertEqual(audit_sample(positive,zero,(0.,1.,0.),beam,1)['status'],'PASS')
        positive['C0'][0]+=.1
        self.assertEqual(audit_sample(positive,zero,(0.,1.,0.),beam,1)['status'],'RED')
        self.assertEqual(audit_sample(positive,zero,(0.,1.,0.),(0.,0.,0.),1)['status'],'INCONCLUSIVE')

    def test_qualified_old_difference_is_a_control_not_a_filtered_sun_bug_claim(self):
        positive,zero=point(),point()
        positive['requested']=zero['requested']=0.
        report=audit_sample(positive,zero,(0.,1.,0.),(1.,.5,.25),0)
        self.assertEqual(report['status'],'CONTROL')
        self.assertTrue(report['centralsharp_negative_control'])
        self.assertFalse(report['native_pixel_filter_equivalence_accepted'])

    def test_matching_coarse_numbers_do_not_hide_selected_quadrature_error(self):
        positive,zero=point(),point();beam=(1.,.5,.25)
        positive['covariance']=zero['covariance']=[.000001,0.,.0064]
        positive['C0']=sun_integral(positive,(0.,1.,0.),beam)['source_difference_C0']
        positive['applied']=1.
        self.assertEqual(audit_sample(positive,zero,(0.,1.,0.),beam,1)['status'],'PASS')
        report=audit_sample(positive,zero,(0.,1.,0.),beam,1,refine=True)
        self.assertEqual(report['status'],'RED')
        self.assertFalse(report['selected_finite_to_refined_accepted'])
        self.assertFalse(report['selected_actual_to_refined_accepted'])

    def test_selected_coarse_and_actual_response_each_match_refined_reference(self):
        positive,zero=point(),point();beam=(1.,.5,.25)
        positive['C0']=sun_integral(positive,(0.,1.,0.),beam)['source_difference_C0']
        positive['applied']=1.
        report=audit_sample(positive,zero,(0.,1.,0.),beam,1,refine=True)
        self.assertEqual(report['status'],'PASS')
        self.assertTrue(report['convergence_accepted'])
        self.assertTrue(report['selected_finite_to_refined_accepted'])
        self.assertTrue(report['selected_actual_to_refined_accepted'])


if __name__=='__main__':unittest.main()
