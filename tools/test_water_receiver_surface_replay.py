import copy
import json
from pathlib import Path
import unittest
from water_receiver_surface_replay import unique_descriptors

class SurfaceRequestDedupTest(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[1]/"reports/2026-10-06-water-receiver-texture/actual-texture-readback.json"
        self.faces=json.loads(path.read_text())["observations"][0]["actualClientFaces"]
    def test_same_actual_face_with_different_ray_points_is_one_material(self):
        self.assertEqual(len(unique_descriptors(self.faces)),14)
    def test_conflicting_actual_face_descriptor_is_not_resolved_by_last_entry(self):
        conflicting=copy.deepcopy(self.faces[0]);conflicting["uvS"][0]+=.01
        with self.assertRaises(ValueError):unique_descriptors([self.faces[0],conflicting])

if __name__=="__main__":unittest.main()
