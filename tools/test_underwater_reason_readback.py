"""CPU-only acceptance of saved reason readback; never performs GL/game I/O.

A snapshotFrame is not a before/after frame-counter proof. Comparisons require
both real saved snapshots and separately explicit expected pack identities.
"""
import hashlib
from copy import deepcopy
import json
import math
from pathlib import Path
import re
import struct
import sys
import unittest


BEFORE = Path(__file__).resolve().parents[1] / "reports/2026-10-02-underwater-reasons/before-near-reasons.json"
BEFORE_PACK_SHA = "0a987cc4b716e2e54f20f4b428ba7dca4d8d1cc39e0cd5c49b55be3a1a868a2d"
AFTER = BEFORE.with_name("after-near-reasons.json")
AFTER_PACK_SHA = "c1d5f1a0215fbd71416475d11b73e85b9e82e7318494aa1fae3cdfe26ad1dab7"
STATE_FIELDS = {"active", "binding", "packBuffer", "alignment", "rowLength",
                "imageHeight", "skipPixels", "skipRows", "skipImages", "swap", "lsb"}
SELECTED_POINTS = {(800,450),(400,450),(1200,450),(100,450),(1500,450),
                   (800,100),(800,800),(100,100),(1500,100),(100,800),
                   (1500,800),(400,250),(1200,250),(400,650),(1200,650),(800,250)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def finite_vector(value, size):
    return (isinstance(value, list) and len(value) == size and
            all(type(x) in (int, float) and math.isfinite(x) for x in value))


def audit_file(path, expected_pack_sha=BEFORE_PACK_SHA):
    """Return a CPU evidence summary for a bounded saved JSON, not a render test."""
    with Path(path).open("rb") as source:
        raw = source.read(256 * 1024 + 1)
    if len(raw) > 256 * 1024:
        raise ValueError("Readback JSON exceeds bounded size")
    result = audit_readback(json.loads(raw), expected_pack_sha)
    result["source_json_sha256"] = hashlib.sha256(raw).hexdigest()
    return result


def audit_readback(document, expected_pack_sha=BEFORE_PACK_SHA):
    """Accept typed observed data, without requiring a particular optical outcome."""
    require(isinstance(document, dict), "Missing readback object")
    for key in ("available", "stateRestored", "scopeAuthorized", "timingAcceptanceExcluded",
                "selectedTexelsFiniteOnly"):
        require(document.get(key) is True, "Missing successful readback guard: " + key)
    require(document.get("worldId") == "b22dbccb-2970-41e6-847f-f183b1ec923d" and
            document.get("world") == "AqualumenNaturalV2" and
            type(document.get("seed")) is int and document["seed"] == 308060 and
            document.get("dimension") == "minecraft:overworld", "Wrong approved world")
    require(isinstance(expected_pack_sha, str) and re.fullmatch(r"[0-9a-f]{64}", expected_pack_sha) and
            document.get("packSha256") == expected_pack_sha and
            document.get("packName") in {"Aqualumen-ShoreProbe-world-underwater-reasons-084-v1.zip",
                                         "Aqualumen-ShoreProbe-world-underwater-reasons-085-v1.zip"},
            "Wrong reasons pack identity")
    require(document.get("observerVersion") == "0.3.9" and document.get("tag") == "DEBUG-shore-sampler",
            "Wrong observer identity")
    require(integer(document.get("program"), 1) and document["program"] == document.get("expectedProgram") and
            integer(document.get("expectedProgram"), 1), "Current/expected program mismatch")
    require(type(document.get("width")) is int and document["width"] == 1600 and
            type(document.get("height")) is int and document["height"] == 900, "Wrong full-size target")
    require(document.get("renderer") == "NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2", "Unexpected renderer")
    require(document.get("seam") == "FinalPassRenderer.renderFinalPass before FullScreenQuadRenderer.renderQuad; after Program.use and CustomUniforms.push",
            "Unknown prepared-program seam")
    require(integer(document.get("snapshotFrame"), 1) and
            type(document.get("frameTimeCounter")) in (int, float) and
            math.isfinite(document["frameTimeCounter"]), "Missing finite snapshot metadata")
    require(finite_vector(document.get("unshiftedCameraPosition"), 3) and
            math.dist(document["unshiftedCameraPosition"], [448.5,62.38899988555908,-383.5]) < .05,
            "Wrong near-camera snapshot")
    require(document.get("geometryAttributionAccepted") is False and
            document.get("runtimeIntegrationAccepted") is False and
            document.get("visualQualityAccepted") is False, "Overclaimed source acceptance")
    before, after = document.get("stateBefore"), document.get("stateAfter")
    require(isinstance(before, dict) and isinstance(after, dict) and
            set(before) == STATE_FIELDS and set(after) == STATE_FIELDS and
            all(type(v) is int for v in before.values()) and
            all(type(v) is int for v in after.values()) and before == after,
            "Eleven saved GL state fields were not restored")
    require(type(document.get("maximumSelectedTexels")) is int and
            document["maximumSelectedTexels"] == 16 and
            document.get("texelCoordinateConvention") == "integer level-zero texture coordinates; bottom-left origin",
            "Unknown selected-texel boundary")
    require(document.get("samplingInterpretation") == "unfiltered level-zero texels, not tone-mapped or reconstructed FINAL texture() values",
            "Unknown raw sample interpretation")
    entries = document.get("samplers")
    require(isinstance(entries, list) and all(isinstance(x, dict) for x in entries), "Missing samplers")
    names = [x.get("name") for x in entries]
    require(all(isinstance(n, str) for n in names) and len(set(names)) == len(names), "Duplicate sampler names")
    samplers = dict(zip(names, entries))
    require(sum(x.get("active") is True for x in entries) == 3, "Expected exactly three active reason samplers")
    points, units, textures, locations = {}, [], [], []
    for name in ("colortex9", "colortex10", "colortex11"):
        sampler = samplers.get(name)
        require(isinstance(sampler, dict) and sampler.get("active") is True and
                integer(sampler.get("location")) and type(sampler.get("type")) is int and
                sampler["type"] == 35678 and type(sampler.get("size")) is int and sampler["size"] == 1,
                "Missing active scalar sampler2D: " + name)
        require(integer(sampler.get("unit")) and integer(sampler.get("textureId"), 1) and
                sampler.get("textureExists") is True and type(sampler.get("actualFormat")) is int and
                sampler["actualFormat"] == 34836 and type(sampler.get("width")) is int and
                sampler["width"] == 1600 and type(sampler.get("height")) is int and sampler["height"] == 900,
                "Missing full-size actual RGBA32F binding: " + name)
        units.append(sampler["unit"]); textures.append(sampler["textureId"]); locations.append(sampler["location"])
        samples = sampler.get("samples")
        require(isinstance(samples, list) and len(samples) == 16, "Missing selected points: " + name)
        rows = {}
        for sample in samples:
            require(isinstance(sample, dict) and integer(sample.get("x")) and integer(sample.get("y")),
                    "Missing integer texel coordinate")
            coordinate = (sample["x"], sample["y"])
            require(coordinate in SELECTED_POINTS and coordinate not in rows, "Unexpected/duplicate texel coordinate")
            rgba = sample.get("rgba")
            require(finite_vector(rgba, 4), "Nonfinite/missing RGBA at " + name)
            try:
                exact_float32 = all(struct.unpack("<f", struct.pack("<f", x))[0] == x for x in rgba)
            except (OverflowError, struct.error):
                exact_float32 = False
            require(exact_float32, "RGBA values do not roundtrip source float32")
            rows[coordinate] = rgba
        require(set(rows) == SELECTED_POINTS, "Sampler coordinate sets differ")
        points[name] = rows
    require(len(set(units)) == len(set(textures)) == len(set(locations)) == 3,
            "Reason samplers alias units, textures or locations")
    metadata = document.get("samplerMetadata")
    require(isinstance(metadata, list) and len(metadata) == 3 and
            all(isinstance(x, dict) and integer(x.get("unit")) for x in metadata) and
            len({x["unit"] for x in metadata}) == 3, "Missing distinct effective-binding metadata")
    by_unit = {x["unit"]: x for x in metadata}
    for name in ("colortex9", "colortex10", "colortex11"):
        sampler = samplers[name]; actual = by_unit.get(sampler["unit"])
        require(isinstance(actual, dict) and actual.get("textureId") == sampler["textureId"] and
                type(actual.get("textureBaseLevel")) is int and actual["textureBaseLevel"] == 0 and
                actual.get("samplerObjectObserved") is True and actual.get("effectiveFilteringObserved") is True and
                type(actual.get("wholeTargetReadbackBytes")) is int and actual["wholeTargetReadbackBytes"] == 1600*900*16 and
                type(actual.get("exportedTexelCount")) is int and actual["exportedTexelCount"] == 16,
                "Effective binding/raw readback metadata mismatch: " + name)
    counts = {"downward_normal":0, "unknown_weight_nonzero":0, "raw_column_known":0,
              "final_column_known":0, "underwater_water_points":0, "SSR_hit":0, "SSR_miss":0}
    for coordinate in sorted(SELECTED_POINTS):
        normal, unknown, raw_known, final_known = points["colortex9"][coordinate]
        fresnel, underwater, water, alpha = points["colortex10"][coordinate]
        path, hit, miss, reflection_alpha = points["colortex11"][coordinate]
        require(abs(normal) <= 1.00001 and -.00001 <= unknown <= 1.00001 and
                raw_known in (0.0,1.0) and final_known in (0.0,1.0), "Invalid reason vector")
        require(final_known == float(raw_known == 1.0 and unknown == 0.0), "Inconsistent known-column guard")
        require(0.0 <= fresnel <= 1.0 and (underwater,water,alpha) == (1.0,1.0,1.0),
                "Selected point is not an observed underwater water fragment")
        require(hit == float(path > 0) and miss == float(path < 0) and reflection_alpha == 1.0,
                "Inconsistent reflected path/hit/miss vector")
        counts["downward_normal"] += normal < -.5
        counts["unknown_weight_nonzero"] += unknown != 0.0
        counts["raw_column_known"] += raw_known == 1.0
        counts["final_column_known"] += final_known == 1.0
        counts["underwater_water_points"] += 1
        counts["SSR_hit"] += hit == 1.0; counts["SSR_miss"] += miss == 1.0
    return {
        "accepted": True, "acceptance_scope": "saved raw named-sampler reason readback only",
        "request_id": document.get("requestId"), "pack_sha256": document["packSha256"],
        "pack_name": document["packName"], "camera_position": document["unshiftedCameraPosition"],
        "world_id": document["worldId"], "observer_version": document["observerVersion"],
        "program": document["program"], "size": [1600,900], "active_reason_samplers": 3,
        "sampler_units": units, "texture_ids": textures, "actual_format": "RGBA32F",
        "selected_points": 16, "restored_state_fields": 11, "counts": counts,
        "reason_vectors_unique": [list(x) for x in sorted({tuple(x) for x in points["colortex9"].values()})],
        "fresnel_range": [min(x[0] for x in points["colortex10"].values()), max(x[0] for x in points["colortex10"].values())],
        "snapshot_frame_observed": document["snapshotFrame"],
        "frame_time_counter_observed": document["frameTimeCounter"], "comparison": "single_snapshot_only",
        "claims": {"frame_counter_unchanged_proven":False, "same_frame_PNG_proven":False,
                   "geometry_attribution_accepted":False, "natural_visual_acceptance":False,
                   "shipping_fix_accepted":False, "full_goal_complete":False}}


def audit_pair(before_path, after_path, before_pack_sha, after_pack_sha):
    before = audit_file(before_path, before_pack_sha)
    after = audit_file(after_path, after_pack_sha)
    require(before["request_id"] != after["request_id"] and
            before["world_id"] == after["world_id"] and before["size"] == after["size"] and
            before["camera_position"] == after["camera_position"], "Snapshots do not share the fixed near comparison")
    return {"accepted":True, "acceptance_scope":"paired saved raw reason readback only",
            "comparison":"actual_before_after_saved_readbacks", "before":before, "after":after,
            "count_changes":{key:[value,after["counts"][key]] for key,value in before["counts"].items()},
            "claims":dict(before["claims"]),
            "limits":["Sixteen selected texels, not the whole target",
                      "Snapshot indices/counters are observations, not before/after invariance",
                      "Separate captures and dynamic wave phases are not a pixel-exact visual A/B",
                      "SSR miss/round window/dark rim is not accepted as fixed"]}


class UnderwaterReasonReadbackTest(unittest.TestCase):
    def test_actual_before_is_accepted_only_as_saved_sampler_readback(self):
        summary = audit_file(BEFORE)
        self.assertTrue(summary["accepted"])
        self.assertEqual(summary["active_reason_samplers"], 3)
        self.assertEqual(summary["selected_points"], 16)
        self.assertEqual(summary["restored_state_fields"], 11)
        self.assertEqual(summary["counts"], {
            "downward_normal": 16, "unknown_weight_nonzero": 16,
            "raw_column_known": 16, "final_column_known": 0,
            "underwater_water_points": 16, "SSR_hit": 0, "SSR_miss": 16})
        self.assertFalse(summary["claims"]["frame_counter_unchanged_proven"])
        self.assertFalse(summary["claims"]["natural_visual_acceptance"])
        self.assertEqual(summary["comparison"], "single_snapshot_only")

    def test_actual_after_is_compared_without_requiring_the_before_outcome(self):
        after = audit_file(AFTER, AFTER_PACK_SHA)
        self.assertEqual(after["counts"]["unknown_weight_nonzero"], 0)
        self.assertEqual(after["counts"]["raw_column_known"], 16)
        self.assertEqual(after["counts"]["final_column_known"], 16)
        compared = audit_pair(BEFORE, AFTER, BEFORE_PACK_SHA, AFTER_PACK_SHA)
        self.assertTrue(compared["accepted"])
        self.assertEqual(compared["comparison"], "actual_before_after_saved_readbacks")
        self.assertEqual(compared["count_changes"]["final_column_known"], [0,16])
        self.assertEqual(compared["count_changes"]["SSR_miss"], [16,16])
        self.assertFalse(compared["claims"]["frame_counter_unchanged_proven"])
        self.assertFalse(compared["claims"]["natural_visual_acceptance"])

    def test_rejects_failed_scope_world_program_and_wrong_expected_pack(self):
        actual = json.loads(BEFORE.read_text())
        for key,value in (("available",False),("stateRestored",False),("scopeAuthorized",False),
                          ("worldId","wrong"),("seed",0),("dimension","minecraft:the_nether"),
                          ("expectedProgram",22),("visualQualityAccepted",True)):
            with self.subTest(key=key):
                damaged = deepcopy(actual); damaged[key] = value
                with self.assertRaises(ValueError):
                    audit_readback(damaged)
        with self.assertRaises(ValueError):
            audit_file(AFTER)  # A different pack requires its explicit expected SHA.

    def test_rejects_incomplete_or_changed_saved_GL_state(self):
        actual = json.loads(BEFORE.read_text())
        for operation in ("changed", "missing", "extra"):
            with self.subTest(operation=operation):
                damaged = deepcopy(actual)
                if operation == "changed": damaged["stateAfter"]["active"] += 1
                elif operation == "missing": del damaged["stateBefore"]["binding"]
                else: damaged["stateAfter"]["unobserved"] = 0
                with self.assertRaises(ValueError):
                    audit_readback(damaged)

    def test_rejects_inactive_non_scalar_wrong_storage_or_aliased_binding(self):
        actual = json.loads(BEFORE.read_text())
        for key,value in (("active",False),("type",0),("size",2),("location",-1),
                          ("actualFormat",34842),("width",800),("textureId",73)):
            with self.subTest(key=key):
                damaged = deepcopy(actual); damaged["samplers"][0][key] = value
                with self.assertRaises(ValueError):
                    audit_readback(damaged)
        for key,value in (("textureBaseLevel",1),("exportedTexelCount",15),
                          ("wholeTargetReadbackBytes",0),("textureId",1)):
            with self.subTest(metadata=key):
                damaged = deepcopy(actual); damaged["samplerMetadata"][0][key] = value
                with self.assertRaises(ValueError):
                    audit_readback(damaged)

    def test_rejects_nonfinite_duplicate_missing_or_inconsistent_points(self):
        actual = json.loads(BEFORE.read_text())
        for failure in ("nonfinite", "duplicate", "missing", "false_water", "false_hit", "false_known"):
            with self.subTest(failure=failure):
                damaged = deepcopy(actual)
                if failure == "nonfinite": damaged["samplers"][0]["samples"][0]["rgba"][0] = float("nan")
                elif failure == "duplicate": damaged["samplers"][0]["samples"][1] = deepcopy(damaged["samplers"][0]["samples"][0])
                elif failure == "missing": damaged["samplers"][1]["samples"].pop()
                elif failure == "false_water": damaged["samplers"][1]["samples"][0]["rgba"][2] = 0.0
                elif failure == "false_hit": damaged["samplers"][2]["samples"][0]["rgba"][1] = 1.0
                else: damaged["samplers"][0]["samples"][0]["rgba"][3] = 1.0
                with self.assertRaises(ValueError):
                    audit_readback(damaged)

    def test_missing_after_cannot_be_reported_as_accepted_pair(self):
        with self.assertRaises(FileNotFoundError):
            audit_pair(BEFORE, AFTER.with_name("not-obtained.json"), BEFORE_PACK_SHA, AFTER_PACK_SHA)

    def test_rejects_final_known_disagreement_in_both_directions(self):
        for path,expected,wrong_final in ((BEFORE,BEFORE_PACK_SHA,1.0),(AFTER,AFTER_PACK_SHA,0.0)):
            with self.subTest(path=path.name):
                damaged = json.loads(path.read_text())
                damaged["samplers"][0]["samples"][0]["rgba"][3] = wrong_final
                with self.assertRaises(ValueError):
                    audit_readback(damaged, expected)


if __name__ == "__main__":
    if "--audit" in sys.argv:
        import argparse
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--audit", type=Path, required=True)
        parser.add_argument("--expected-pack-sha", default=BEFORE_PACK_SHA)
        parser.add_argument("--after", type=Path)
        parser.add_argument("--after-pack-sha")
        args = parser.parse_args()
        if args.after and not args.after_pack_sha:
            parser.error("--after requires its explicit --after-pack-sha")
        result = (audit_pair(args.audit,args.after,args.expected_pack_sha,args.after_pack_sha) if args.after
                  else audit_file(args.audit,args.expected_pack_sha))
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    else:
        unittest.main()
