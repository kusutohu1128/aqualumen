import json
from pathlib import Path
import unittest
from water_receiver_atlas_audit import audit
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/2026-10-06-water-receiver-atlas-v2"
class ActualAtlasAuditTest(unittest.TestCase):
    def setUp(self):
        self.capture=json.loads((OUT/"actual-texture-readback.json").read_text())
        self.geometry=json.loads((ROOT/"reports/2026-10-06-water-coast-world/geometry-audit.json").read_text())
        self.request=(OUT/"request.properties").read_bytes();self.reference=json.loads((OUT/"independent-stock-reference.json").read_text())
    def test_actual_warmed_GPU_native_stock_agreement(self):
        result=audit(self.capture,self.geometry,self.request,self.reference)
        self.assertEqual(result["actualGPUWholeSpriteMatches"],48)
        self.assertFalse(result["sourceUploaded"])
    def test_changed_GL_binding_cannot_qualify(self):
        self.capture["observations"][0]["gpuAtlas"]["after"]["texture2D"]+=1
        with self.assertRaises(ValueError):audit(self.capture,self.geometry,self.request,self.reference)
    def test_GPU_digest_difference_cannot_be_hidden_by_CPU_match(self):
        self.capture["observations"][0]["actualClientFaces"][0]["gpuTextureRGBA_SHA256"]="0"*64
        with self.assertRaises(ValueError):audit(self.capture,self.geometry,self.request,self.reference)
    def test_GPU_point_readback_difference_is_rejected(self):
        self.capture["observations"][0]["actualClientFaces"][0]["gpuSavedPointRGBA"][0]^=1
        with self.assertRaises(ValueError):audit(self.capture,self.geometry,self.request,self.reference)
    def test_unqualified_storage_cannot_be_assumed_RGBA8(self):
        self.capture["observations"][0]["gpuAtlas"]["componentBits"][0]=16
        with self.assertRaises(ValueError):audit(self.capture,self.geometry,self.request,self.reference)
    def test_failed_owned_GPU_control_mutation_cannot_qualify(self):
        self.capture["knownGPUTextureControl"]["ownGPUTextureMutationReadbackRGBA"]=[7,8,9,255]
        with self.assertRaises(ValueError):audit(self.capture,self.geometry,self.request,self.reference)
if __name__=="__main__":unittest.main()
