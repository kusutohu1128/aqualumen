import json
from pathlib import Path
import unittest
from water_receiver_texture_audit import audit

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/2026-10-06-water-receiver-texture"

class ActualTextureAuditTest(unittest.TestCase):
    def setUp(self):
        self.capture=json.loads((OUT/"actual-texture-readback.json").read_text())
        self.geometry=json.loads((ROOT/"reports/2026-10-06-water-coast-world/geometry-audit.json").read_text())
        self.request=(OUT/"request.properties").read_bytes()
        self.reference=json.loads((OUT/"independent-stock-reference.json").read_text())

    def test_actual_warmed_native_texels_match_independent_reference(self):
        result=audit(self.capture,self.geometry,self.request,self.reference)
        self.assertEqual(result["qualifiedFaceObservations"],48)
        self.assertEqual(result["qualifiedSparsePixelChecks"],240)
        self.assertFalse(result["sourceUploaded"])

    def test_correct_color_at_wrong_uv_does_not_qualify(self):
        face=self.capture["observations"][0]["actualClientFaces"][0]
        other=next(p for p in self.reference["samples"] if p[:2]!=face["savedPointPixel"])
        face["savedPointPixel"],face["savedPointRGBA"]=other[:2],other[2:]
        with self.assertRaises(ValueError):audit(self.capture,self.geometry,self.request,self.reference)

    def test_early_frame_is_not_a_warmed_observation(self):
        self.capture["observations"][0]["elapsedNanoseconds"]=1
        with self.assertRaises(ValueError):audit(self.capture,self.geometry,self.request,self.reference)

    def test_stale_request_or_source_promotion_cannot_qualify(self):
        self.capture["requestSHA256"]="0"*64
        with self.assertRaises(ValueError):audit(self.capture,self.geometry,self.request,self.reference)

    def test_unqualified_raw_light_is_rejected(self):
        self.capture["observations"][0]["actualClientFaces"][0]["skyLight"]=16
        with self.assertRaises(ValueError):audit(self.capture,self.geometry,self.request,self.reference)

if __name__=="__main__":unittest.main()
