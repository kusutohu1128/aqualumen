from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

import water_hit_depth_audit as audit


CAPTURE=Path('/home/kusutohu/repos/aqualumen/reports/2026-10-22-water-hit-depth/runtime-candidate2/underwater-up-near-paired-capture')


class SavedDepthAuditControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest,cls.data,cls.pin=audit.load(CAPTURE)

    def analyze(self,manifest=None):
        with patch.object(audit,'load',return_value=(manifest or self.manifest,self.data,self.pin)):
            return audit.analyze(CAPTURE,'candidate')

    def mutant(self,key,component,delta,violation):
        original=self.data[key][0,0,component]
        try:
            self.data[key][0,0,component]+=delta
            result=self.analyze()
            self.assertEqual(result[violation],1)
            self.assertFalse(result['boundedDepthEyeConsistencyPassed'])
        finally:
            self.data[key][0,0,component]=original

    def test_saved_positive_control(self):
        self.assertTrue(self.analyze()['boundedDepthEyeConsistencyPassed'])

    def test_distance_mutant_rejected(self):
        self.mutant('optics-colortex2',0,.02,'distanceViolations')

    def test_transmission_mutant_rejected(self):
        self.mutant('optics-colortex2',1,.01,'beerViolations')

    def test_stored_depth_mutant_rejected(self):
        self.mutant('depth-depthtex0',0,-.001,'storedDepthViolations')

    def test_point_mutant_rejected(self):
        self.mutant('optics-colortex3',1,.02,'distanceViolations')

    def test_opaque_tie_mutant_rejected(self):
        original=self.data['depth-depthtex1'][0,0,0]
        try:
            self.data['depth-depthtex1'][0,0,0]=self.data['depth-depthtex0'][0,0,0]
            result=self.analyze()
            self.assertEqual(result['storedOpaqueExactTies'],1)
            self.assertFalse(result['boundedDepthEyeConsistencyPassed'])
        finally:
            self.data['depth-depthtex1'][0,0,0]=original

    def test_wrong_pack_mutant_rejected(self):
        manifest=deepcopy(self.manifest);manifest['packSha256']='0'*64
        with self.assertRaises(AssertionError):
            self.analyze(manifest)


if __name__=='__main__':
    unittest.main()
