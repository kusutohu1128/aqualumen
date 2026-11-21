import copy
import json
import unittest
from water_coast_world_classify import OUT,classify

class Occlusion(unittest.TestCase):
    def setUp(self):self.points=json.loads((OUT/'geometry-audit.json').read_text())['points']
    def test_actual_pair_geometry_not_shader_stop(self):
        self.assertEqual(sum(classify(p)=='different_full_cube_occludes_physical_receiver' for p in self.points),8)
        p=copy.deepcopy(self.points[0]);p['stop']=0;p['priorRole']='hit'
        self.assertEqual(classify(p),'different_full_cube_occludes_physical_receiver')
    def test_no_nearest_cube_or_no_camera_evidence_is_unsupported(self):
        p=copy.deepcopy(self.points[1]);p['firstIntersection']['status']='unsupported_geometry'
        self.assertEqual(classify(p),'unsupported')
        p=copy.deepcopy(self.points[1]);p.pop('independentCameraRayToPhysicalFirstPoint')
        self.assertEqual(classify(p),'unsupported')

if __name__=='__main__':unittest.main()
