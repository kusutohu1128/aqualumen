"""Behavioral checks of the public actual-face evidence contract."""
import json
from pathlib import Path
import unittest

from water_receiver_faces_audit import audit

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/2026-10-06-water-receiver-faces"

class ActualFaceAuditTest(unittest.TestCase):
    def setUp(self):
        self.capture=json.loads((OUT/"actual-face-readback.json").read_text())
        self.geometry=json.loads((ROOT/"reports/2026-10-06-water-coast-world/geometry-audit.json").read_text())
        self.request=(OUT/"request.properties").read_bytes()

    def test_actual_ordered_first_faces_qualify(self):
        result=audit(self.capture,self.geometry,self.request)
        self.assertEqual(result["qualifiedFirstFaces"],16)
        self.assertEqual(result["cameraHiddenFirstFaces"],8)
        self.assertFalse(result["radianceComputed"])

    def test_stale_request_is_not_actual_scope(self):
        self.capture["requestSHA256"]="0"*64
        with self.assertRaises(ValueError):audit(self.capture,self.geometry,self.request)

    def test_out_of_sprite_uv_cannot_qualify(self):
        self.capture["actualClientFaces"][0]["uvOrigin"][0]=1.0
        with self.assertRaises(ValueError):audit(self.capture,self.geometry,self.request)

    def test_unsmoothed_inputs_must_not_be_called_radiance(self):
        self.capture["radianceComputed"]=True
        with self.assertRaises(ValueError):audit(self.capture,self.geometry,self.request)

    def test_invalid_raw_light_is_rejected(self):
        self.capture["actualClientFaces"][0]["skyLight"]=16
        with self.assertRaises(ValueError):audit(self.capture,self.geometry,self.request)

if __name__=="__main__":unittest.main()
