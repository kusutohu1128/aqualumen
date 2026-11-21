"""Synthetic independent support checks, not GPU or physical acceptance."""
import copy
import math
import unittest
import water_legacy_branch_replay as b


class ReplayTests(unittest.TestCase):
    def specimen(self):
        n=[0,-1,0];v=[.8,-.6,0];c=[.2,0,.2]
        model=b.forward(n,v,c,45)
        mask=model['mask'];first=model['first'];node=model['firstNode']
        t=model['nodes'][node]['transmitted'];r=model['nodes'][node]['reflected']
        return dict(normal=[*n,1],view=[*v,.6],covariance=[*c,1],
                    status=[0,0,model['minimumFacing'],0],
                    failure=[mask,first,node,16+model['failedNodes']],
                    transmitted=[*t,float(model['nodes'][node]['tir'])],
                    reflected=[*r,model['nodes'][node]['facing']])

    def test_positive_failed_hemisphere_and_raw_view_not_normalized(self):
        p=self.specimen();self.assertEqual(p['failure'][1],128)
        self.assertGreater(p['reflected'][1],0)
        self.assertAlmostEqual(p['reflected'][1],3/55,delta=1e-14)
        result=b.replay(p,45)
        self.assertTrue(result['forwardRayCorrespondenceQualified'])
        self.assertEqual(result['firstPredicate'],'reflectedHemisphere')
        self.assertFalse(result['physicalAccepted'])

    def test_changed_first_ray_and_inactive_ledger_rejected(self):
        for field,index,value in (('reflected',1,-.2),('failure',1,256),('failure',3,0),('normal',0,.1)):
            p=self.specimen();p[field][index]=value
            with self.assertRaises(ValueError):b.replay(p,45)

    def test_wrong_phase_rejected_by_direction_and_mask_correspondence(self):
        with self.assertRaises(ValueError):b.replay(self.specimen(),0)

    def test_no_failure_has_no_fake_first_node(self):
        m=b.forward([0,-1,0],[0,-1,0],[.0001,0,.0001],0)
        self.assertEqual(m['mask'],0)
        p=dict(normal=[0,-1,0,1],view=[0,-1,0,1],covariance=[.0001,0,.0001,1],
               status=[1,1,m['minimumFacing'],0],failure=[0,0,-2,16],
               transmitted=[0,0,0,0],reflected=[0,0,0,0])
        self.assertEqual(b.replay(p,0)['firstPredicate'],'none')
        p['failure'][2]=0
        with self.assertRaises(ValueError):b.replay(p,0)


if __name__=='__main__':unittest.main()
