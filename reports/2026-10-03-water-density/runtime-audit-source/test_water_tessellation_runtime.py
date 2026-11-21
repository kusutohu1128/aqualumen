"""CPU tests for bounded TES-output observations, not visual acceptance."""
import copy
import unittest

from water_tessellation_runtime import qualify_readback


def fixture():
    raw = {
        "available": True, "stateRestored": True, "scopeAuthorized": True,
        "worldId": "b22dbccb-2970-41e6-847f-f183b1ec923d",
        "world": "AqualumenNaturalV2", "seed": 308060,
        "dimension": "minecraft:overworld", "packName": "test.zip",
        "packSha256": "a" * 64, "observerVersion": "0.3.9",
        "program": 21, "expectedProgram": 21, "width": 1600, "height": 900,
        "renderer": "NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2",
        "stateBefore": dict.fromkeys(("active", "binding", "packBuffer", "alignment",
            "rowLength", "imageHeight", "skipPixels", "skipRows", "skipImages", "swap", "lsb"), 0),
        "geometryAttributionAccepted": False, "runtimeIntegrationAccepted": False,
        "samplers": [], "samplerMetadata": [],
    }
    raw["stateAfter"] = copy.deepcopy(raw["stateBefore"])
    for index, name in enumerate(("colortex9", "colortex10", "colortex11", "colortex12")):
        samples = []
        for p in range(16):
            rgba = ((0, -1, 0, 1), (.1, 1, 1, 1), (-1, 0, 1, 1),
                    (.1 + p / 100, .2, .7 - p / 100, 1))[index]
            samples.append({"x": 20 + p * 50, "y": 450, "rgba": list(rgba)})
        raw["samplers"].append(dict(name=name, active=True, location=index,
            type=35678, size=1, unit=index+3, textureId=index+71, textureExists=True,
            actualFormat=34836, width=1600, height=900, samples=samples))
        raw["samplerMetadata"].append(dict(unit=index+3, textureId=index+71,
            wholeTargetReadbackBytes=1600*900*16, exportedTexelCount=16))
    return raw


class ReadbackTests(unittest.TestCase):
    def audit(self, raw):
        return qualify_readback(raw, "test.zip", "a" * 64)

    def test_synthetic_stage_output_does_not_accept_geometry_or_visual_quality(self):
        result = self.audit(fixture())
        self.assertEqual(result["qualifiedUnderwaterKnownStagePoints"], 16)
        for key in ("geometryNeutralityAccepted", "stageAttachmentQueryObserved",
                    "pngSameFrameAccepted", "visualQualityAccepted", "shippingAccepted"):
            self.assertIs(result[key], False)

    def test_synthetic_tes_flag_allows_bounded_raster_interpolation_roundoff(self):
        raw=fixture()
        for p in raw["samplers"][3]["samples"]: p["rgba"][3]=1-2**-23
        self.assertEqual(self.audit(raw)["qualifiedUnderwaterKnownStagePoints"],16)
        raw["samplers"][3]["samples"][0]["rgba"][3]=.999
        with self.assertRaises(ValueError): self.audit(raw)

    def test_synthetic_missing_inactive_or_aliased_stage_sampler_rejected(self):
        for mutation in (lambda r: r["samplers"].pop(),
                         lambda r: r["samplers"][3].update(active=False),
                         lambda r: r["samplers"][3].update(textureId=71)):
            raw=fixture(); mutation(raw)
            with self.assertRaises(ValueError): self.audit(raw)

    def test_synthetic_wrong_identity_storage_or_state_rejected(self):
        for mutation in (lambda r: r.update(packSha256="b"*64),
                         lambda r: r.update(seed=0),
                         lambda r: r["samplers"][3].update(actualFormat=34842),
                         lambda r: r["stateAfter"].update(binding=5)):
            raw=fixture(); mutation(raw)
            with self.assertRaises(ValueError): self.audit(raw)

    def test_synthetic_nonfinite_bad_barycentrics_or_missing_flag_rejected(self):
        for value in ((float("nan"), .2, .7, 1), (.2, .2, .2, 1),
                      (-.1, .2, .9, 1), (.1, .2, .7, 0)):
            raw=fixture(); raw["samplers"][3]["samples"][0]["rgba"]=value
            with self.assertRaises(ValueError): self.audit(raw)

    def test_synthetic_constant_stage_output_is_not_nonvacuous(self):
        raw=fixture()
        for p in raw["samplers"][3]["samples"]: p["rgba"]=[.1,.2,.7,1]
        with self.assertRaises(ValueError): self.audit(raw)

    def test_synthetic_coordinates_must_match_and_be_unique(self):
        for mismatch in (True, False):
            raw=fixture()
            if mismatch: raw["samplers"][3]["samples"][0]["x"]=0
            else:
                for sampler in raw["samplers"]:
                    sampler["samples"][1]=copy.deepcopy(sampler["samples"][0])
            with self.assertRaises(ValueError): self.audit(raw)

    def test_synthetic_all_nonwater_is_vacuous(self):
        raw=fixture()
        for sampler in raw["samplers"]:
            for p in sampler["samples"]: p["rgba"]=[0,0,0,0]
        with self.assertRaises(ValueError): self.audit(raw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
