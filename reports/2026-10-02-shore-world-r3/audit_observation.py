"""CPU-only audit of exactly one frozen shore capture and FINAL observation.

Uses strict PNG and frame-metric helpers, not the 2560x1440 release validator.
Default is read-only JSON on stdout; --write exclusively creates this report's
observation-audit.json. No Minecraft, OpenGL, process or config operations.
"""
import argparse
import copy
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from tools.report import check_png, metrics

RUN_ID = "shore-world-r3-20261002-1231"
REQUEST_ID = "259d112e-d967-4cd3-9aaf-148b28c53a4c"
WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d"
PACK_NAME = "Aqualumen-ShoreProbe-world-r3.zip"
PACK_SHA = "ccd937b89156df9104e6bd1106bae1100f163498242ab1ec8e0ddc89dfe98180"
OBSERVER_SHA = "e89739cb92f65d55309187fc2e58f8e4cfaeb3395167c9fb1b37b39299d045dd"
OBSERVATION_SHA = "4e07fcc74e25ce5b530d03e6b76a029dbc5623928357ca258cb38519d848379c"
SHIPPING_WATER_SHA = "231546b85e2317ba11d458b8033cca83301d779c8e92121f0545cd6805062f87"
SIZE = (1600, 900)
CAMERA = [-191.5, 65.71999988555908, 320.5]
POINTS = [(800, 450), (800, 350), (800, 250), (800, 150), (800, 50),
          (450, 150), (1200, 150), (640, 250), (960, 250), (600, 50),
          (1000, 50), (400, 50), (1200, 50), (800, 550), (800, 650), (800, 750)]
HITS = {(800, 350), (800, 250), (640, 250), (960, 250)}
STATE_FIELDS = {"active", "binding", "packBuffer", "alignment", "rowLength",
                "imageHeight", "skipPixels", "skipRows", "skipImages", "swap", "lsb"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("Nonfinite JSON constant: " + value)


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=reject_constant)


def load(path):
    return decode(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite_vector(value, count):
    return (isinstance(value, list) and len(value) == count and
            all(type(part) in (int, float) and math.isfinite(part) for part in value))


def validate_observation(row):
    for key in ("available", "scopeAuthorized", "stateRestored", "timingAcceptanceExcluded", "selectedTexelsFiniteOnly"):
        require(row.get(key) is True, "Missing actual observation flag: " + key)
    for key in ("visualQualityAccepted", "geometryAttributionAccepted", "geometryUniformsAvailable", "runtimeIntegrationAccepted"):
        require(row.get(key) is False, "Unexpected stronger acceptance claim: " + key)
    require((row.get("requestId"), row.get("worldId"), row.get("world"), row.get("seed"), row.get("dimension")) ==
            (REQUEST_ID, WORLD_ID, "AqualumenNaturalV2", 308060, "minecraft:overworld"), "Wrong exact TEST identity")
    require(row.get("packName") == PACK_NAME and row.get("packSha256") == PACK_SHA and row.get("observerVersion") == "0.3.7",
            "Wrong diagnostic pack or observer identity")
    require(row.get("program") == row.get("expectedProgram") == 21 and row.get("snapshotFrame") == 11329,
            "Wrong actual/independently-derived final program or frame")
    require((row.get("width"), row.get("height")) == SIZE and row.get("unshiftedCameraPosition") == CAMERA,
            "Wrong actual FINAL extent or unshifted camera")
    require(row.get("frameTimeCounter") == 91.464226 and row.get("utc") == "2026-10-02T03:32:01.833835719Z",
            "Wrong frozen observation phase")
    require(row.get("renderer") == "NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2", "Wrong actual renderer")
    require(row.get("seam") == "FinalPassRenderer.renderFinalPass before FullScreenQuadRenderer.renderQuad; after Program.use and CustomUniforms.push",
            "Wrong runtime hook")
    require(row.get("maximumRequestsPerJvm") == 8 and row.get("minimumRequestIntervalSeconds") == 1 and row.get("maximumSelectedTexels") == 16,
            "Wrong one-shot bounds")
    require("bottom-left" in row.get("texelCoordinateConvention", "") and "GL3.2 glGetTexImage level0" in row.get("rawReadPolicy", ""),
            "Wrong raw coordinate/readback contract")
    before, after = row.get("stateBefore"), row.get("stateAfter")
    require(isinstance(before, dict) and isinstance(after, dict) and set(before) == set(after) == STATE_FIELDS,
            "Incomplete eleven-state evidence")
    require(all(type(value) is int for value in before.values()) and all(type(value) is int for value in after.values()) and before == after,
            "Actual caller state was not fully restored")
    sources, metadata = row.get("samplers"), row.get("samplerMetadata")
    require(isinstance(sources, list) and len(sources) == 7 and isinstance(metadata, list) and len(metadata) == 7,
            "Incomplete diagnostic channel inventory")
    channels = {}
    for offset, (source, detail) in enumerate(zip(sources, metadata)):
        index, unit, texture = 9 + offset, 3 + offset, 71 + 2 * offset
        require(source.get("name") == f"colortex{index}" and source.get("active") is True and source.get("textureExists") is True,
                "Missing named active texture")
        require(source.get("type") == 35678 and source.get("size") == 1 and type(source.get("location")) is int and source["location"] >= 0,
                "Source is not an actual typed sampler2D")
        require((source.get("unit"), source.get("textureId"), source.get("actualFormat"), source.get("width"), source.get("height")) ==
                (unit, texture, 34836, *SIZE), "Live named unit/binding/storage mismatch")
        require(detail.get("unit") == unit and detail.get("textureId") == texture, "Sampler metadata refers to a different source")
        expected_detail = {"textureMinFilter": 9729, "textureMagFilter": 9729, "textureWrapS": 33071,
                           "textureWrapT": 33071, "textureBaseLevel": 0, "textureMaxLevel": 1000,
                           "samplerObjectId": 0, "effectiveMinFilter": 9729, "effectiveMagFilter": 9729,
                           "effectiveWrapS": 33071, "effectiveWrapT": 33071,
                           "wholeTargetReadbackBytes": 1600 * 900 * 16, "exportedTexelCount": 16}
        require(all(detail.get(key) == value for key, value in expected_detail.items()) and
                detail.get("samplerObjectObserved") is True and detail.get("effectiveFilteringObserved") is True,
                "Unverified effective sampler/base-level state")
        samples = source.get("samples")
        require(isinstance(samples, list) and len(samples) == 16 and "rawRgba32f" not in source, "Wrong selected-only export")
        require([(sample.get("x"), sample.get("y")) for sample in samples] == POINTS,
                "Requested coordinates do not join across channels")
        require(all(type(sample["x"]) is int and type(sample["y"]) is int and finite_vector(sample.get("rgba"), 4) for sample in samples),
                "Invalid selected RGBA floats/coordinates")
        channels[index] = [sample["rgba"] for sample in samples]
    geometry = row.get("geometryUniforms")
    require(isinstance(geometry, dict), "Missing optional geometry-uniform dispositions")
    inverse = geometry.get("gbufferModelViewInverse", {})
    require(inverse.get("available") is True and inverse.get("type") == 35676 and inverse.get("size") == 1 and finite_vector(inverse.get("values"), 16),
            "Missing actual active inverse model-view")
    for name in ("gbufferProjectionInverse", "cameraPosition"):
        require(geometry.get(name) == {"available": False, "reason": "inactive_uniform"}, "Missing geometry must remain unavailable")
    normal_error = ray_error = 0.0
    for i, point in enumerate(POINTS):
        if i >= 13:
            require(all(channels[index][i] == [0, 0, 0, 0] for index in channels), "Expected cleared sky point has diagnostic water data")
            continue
        color, surface, ray, receiver, paths, original, normal = [channels[index][i] for index in range(9, 16)]
        require(color[3] == 1 and all(value >= 0 for value in color[:3]) and surface[3] == 1 and abs(surface[1] - 62.8889) < .30,
                "Selected upper-water source is not confirmed/coherent")
        normal_error = max(normal_error, abs(math.sqrt(sum(value * value for value in normal[:3])) - 1))
        ray_error = max(ray_error, abs(math.sqrt(sum(value * value for value in ray[:3])) - 1))
        require(normal_error < 1e-5 and ray_error < 1e-5 and normal[1] > 0 and ray[1] < 0 and 0 <= normal[3] <= 1,
                "Nonunit or invalid physical interface direction/Fresnel")
        require(all(0 < value <= 48 for value in paths) and 0 < original[3] <= 128,
                "Invalid selected optical path or confirmed local-column depth")
        require(receiver[3] == int(point in HITS) and 0 <= ray[3] <= 1, "Wrong frozen receiver-kind/confidence disposition")
        if point not in HITS:
            require(ray[3] == 0 and receiver[:3] == original[:3] and paths[0] == paths[1],
                    "A miss/fallback must not become a proved receiver")
        else:
            require(ray[3] > 0 and receiver[1] <= surface[1] + .08, "Confirmed-hit fields violate their source guards")
    return {"joined_selected_coordinates": [list(point) for point in POINTS], "selected_texels_per_channel": 16,
            "same_frame_cross_channel_join_verified": True, "snapshot_frame": row["snapshotFrame"],
            "actual_final_program": row["program"], "independent_expected_program": row["expectedProgram"],
            "known_upper_water_outputs": 13, "receiver_kind1_outputs": 4, "receiver_kind0_outputs": 9,
            "cleared_nonwater_sky_points": 3, "maximum_normal_unit_length_error": normal_error,
            "maximum_transmitted_unit_length_error": ray_error, "eleven_state_fields_equal": True,
            "units": list(range(3, 10)), "texture_ids": list(range(71, 84, 2)),
            "actual_format": "RGBA32F", "effective_sampler_objects": "zero; LINEAR texture filters, CLAMP_TO_EDGE, base level0",
            "whole_target_bytes_read": 7 * 1600 * 900 * 16,
            "qualification_limit": "Observed known upper-water flags and unit directions only; no independent world first-receiver raycast or C0-neutrality proof."}


def audit():
    observation = ROOT / "observations" / (REQUEST_ID + ".json")
    directory = ROOT / "captures" / RUN_ID
    pack = ROOT / "tools" / PACK_NAME
    observer = ROOT / "tools" / "aqualumen-benchmark-0.3.7.jar"
    require(sha(pack) == PACK_SHA and sha(observer) == OBSERVER_SHA and sha(observation) == OBSERVATION_SHA, "Frozen artifact hash mismatch")
    with ZipFile(observer) as jar:
        descriptor = decode(jar.read("fabric.mod.json"))
        mixins = decode(jar.read("aqualumen-benchmark.mixins.json"))
        require(descriptor["id"] == "aqualumen_benchmark" and descriptor["version"] == "0.3.7" and descriptor["depends"]["iris"] == "1.8.8",
                "Wrong archived observer descriptor")
        require(mixins["package"] == "dev.aqualumen.bench.mixin" and "ShoreFinalMixin" in mixins["client"], "Archived final hook is not registered")
        for name in ("dev/aqualumen/bench/ShoreRuntimeObserver.class", "dev/aqualumen/bench/ShoreSamplerSnapshot.class", "dev/aqualumen/bench/mixin/ShoreFinalMixin.class"):
            require(name in jar.namelist(), "Archived observer class missing")
    with ZipFile(pack) as archive:
        water = archive.read("shaders/gbuffers_water.fsh").decode()
        require("/* RENDERTARGETS:0,9,10,11,12,13,14,15 */" in water, "Wrong diagnostic output mapping")
        recovered = re.sub(r"/\* SHORE_PROBE_BEGIN \*/.*?/\* SHORE_PROBE_END \*/\n", "", water, flags=re.S)
        recovered = recovered.replace("/* RENDERTARGETS:0,9,10,11,12,13,14,15 */", "/* DRAWBUFFERS:0 */")
        require(hashlib.sha256(recovered.encode()).hexdigest() == SHIPPING_WATER_SHA, "Diagnostic changes altered production water arithmetic")
        properties = archive.read("shaders/shaders.properties").decode()
        final = archive.read("shaders/final.fsh").decode()
        prepare = archive.read("shaders/prepare.fsh").decode()
        for index in range(9, 16):
            require(f"blend.gbuffers_water.colortex{index}=off" in properties and
                    f"const int colortex{index}Format = RGBA32F;" in prepare and f"const bool colortex{index}Clear = true;" in prepare,
                    "Missing diagnostic format/clear/nonblend declaration")
            require(f"texelFetch(colortex{index},p,0)" in final, "Diagnostic display does not use integer level-zero fetch")
    row = load(observation)
    observed = validate_observation(row)
    run, complete, capture = [load(directory / name) for name in ("run.json", "complete.json", "coast-day.json")]
    require(not (directory / "aborted.json").exists() and run["run_id"] == complete["run_id"] == capture["run_id"] == RUN_ID,
            "Wrong or aborted fixed capture")
    require(run["scenarios"] == complete["scenarios"] == ["coast-day"] and complete["status"] == "complete" and complete["fixture_cleanup_complete"] is True,
            "Incomplete fixed capture/cleanup metadata")
    for record in (run, capture):
        require(record["world_id"] == WORLD_ID and record["pack_name"] == PACK_NAME and record["pack_sha256"] == PACK_SHA and
                record["shader_active"] is True and record["shader_fallback"] is False and record["resolution"] == record["framebuffer_resolution"] == list(SIZE),
                "Capture shader/world/extent changed")
    require(run["expected_resolution"] == list(SIZE) and run["expected_pack_sha256"] == PACK_SHA and
            run["schema"] == 2 and run["seed"] == 308060 and run["world_generator"] == "minecraft:noise/overworld" and
            Path(run["world_directory"]).name == "AqualumenNaturalV2" and run["terrain_fixture"] == "No terrain placement",
            "Wrong original natural TEST world")
    require(run["mods"]["aqualumen_benchmark"] == "0.3.7" and run["mods"]["aqualumen_physics"] == "0.3.0" and
            run["mods"]["iris"] == "1.8.8+mc1.21.1" and run["mods"]["fabricloader"] == "0.19.5" and run["minecraft"] == "1.21.1",
            "Wrong recorded runtime versions")
    require(run["gl_renderer"] == row["renderer"] and run["gl_version"] == "3.2.0 NVIDIA 580.173.02" and run["frame_limit"] == 120,
            "Wrong Minecraft renderer/context/cap")
    require(capture["window_focused"] is True and capture["actual_camera_position"] == CAMERA and
            capture["actual_player_position"] == [-191.5, 64.1, 320.5] and capture["actual_camera_rotation"] == capture["actual_player_rotation"] == capture["expected_camera_rotation"] == [0, 9] and
            capture["camera_follows_local_player"] is True and capture["player_dimension"] == "minecraft:overworld",
            "Wrong actual fixed coast camera")
    physics = load(directory / "coast-day-physics.json")
    require(decode(capture["physics_status_json"]) == physics and physics["bathymetry"]["frame"] == 6443 and
            physics["bathymetry"]["known_columns"] == 2417 and physics["active"] == 1 and physics["contacts"] == 2 and physics["max_force"] > 0,
            "Wrong separately recorded mixed coast physics")
    require(physics["bathymetry"]["frame"] != row["snapshotFrame"], "Earlier capture metadata was relabeled same-frame")
    check_png(directory / "coast-day.png", SIZE)
    with (directory / "coast-day.csv").open(newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == ["frame", "ns", "ms"], "Wrong raw interval columns")
        records = list(reader)
    require(len(records) == 592, "Wrong frozen interval count")
    ns, intervals = [], []
    for index, item in enumerate(records):
        require(item["frame"] == str(index) and re.fullmatch(r"[1-9][0-9]*", item["ns"]) is not None, "Invalid sequential integer-ns interval")
        duration = int(item["ns"])
        value = duration * 1e-6
        require(math.isfinite(value) and value > 0 and float(item["ms"]) == value, "CSV milliseconds do not exactly equal integer ns conversion")
        ns.append(duration)
        intervals.append(value)
    recomputed = metrics(intervals)
    differences = {}
    for key, value in recomputed.items():
        differences[key] = value - capture[key]
        require(abs(differences[key]) <= (0 if type(value) is int else 2 * math.ulp(value)), "Metric exceeds two-ULP recalculation difference: " + key)
    require(sum(ns) == 4995852324 and capture["recorded_seconds"] == sum(ns) / 1e9 and
            capture["warmup_seconds"] == 10 and capture["sample_seconds_requested"] == 5 and capture["sample_seconds_actual"] >= 5,
            "Wrong duration/warmup boundary")
    delay = (datetime.fromisoformat(row["utc"].replace("Z", "+00:00")) -
             datetime.fromisoformat(complete["utc"].replace("Z", "+00:00"))).total_seconds()
    require(delay > 40, "Observation is not the separately requested later frame")
    inputs = [observation, pack, observer] + [directory / name for name in
             ("run.json", "complete.json", "coast-day.json", "coast-day.csv", "coast-day.png", "coast-day-physics.json", "coast-day-physics-samples.json")]
    return {"evidence_audit_pass": True, "fixed_capture": RUN_ID, "fixed_observation": REQUEST_ID,
            "actual_final_sampler_readback_verified": True, "observation": observed,
            "capture": {"strict_png_integrity": True, "resolution": list(SIZE), "window_focused": True,
                        "context": run["gl_version"], "frame_limit": 120, "integer_ns_sum": sum(ns),
                        "recomputed_metrics": recomputed, "recalculation_minus_recorded": differences,
                        "comparison_tolerance": "CSV ns-to-ms equality exact; summary metrics at most two IEEE754 ULP"},
            "joins": {"observation_camera_equals_capture_camera": True, "screenshot_same_frame_as_observation": False,
                      "capture_physics_same_frame_as_observation": False, "capture_physics_frame": 6443,
                      "observation_after_capture_complete_seconds": delay, "wind_contact_cloud_phase_equivalence_claimed": False},
            "identity_limits": {"observer_jar_artifact_sha256_verified": True, "runtime_observer_version_matches_artifact": True,
                               "loaded_observer_jar_sha256_independently_observed": False},
            "production_water_arithmetic_source_recovered_exactly": True, "gpu_c0_observational_neutrality_proved": False,
            "release_or_1440p_acceptance": False, "shoreline_visual_quality_accepted": False,
            "independent_world_first_receiver_geometry_accepted": False, "full_realism_goal_complete": False,
            "scope_limit": "One later-frame raw input snapshot and one earlier 1600x900 diagnostic capture; no game/GL rerun, no shipping fix or universal FPS-floor claim.",
            "artifact_sha256": {path.relative_to(ROOT).as_posix(): sha(path) for path in inputs}}


def self_test():
    row = load(ROOT / "observations" / (REQUEST_ID + ".json"))
    mutations = [lambda value: value.update(packSha256="0" * 64),
                 lambda value: value["stateAfter"].update(rowLength=1),
                 lambda value: value["samplers"][0].update(unit=4),
                 lambda value: value["samplers"][0]["samples"][0].update(x=801),
                 lambda value: value["samplers"][0]["samples"][0]["rgba"].__setitem__(0, math.nan),
                 lambda value: value["samplers"][3]["samples"][0]["rgba"].__setitem__(3, 1)]
    for mutation in mutations:
        changed = copy.deepcopy(row)
        mutation(changed)
        try:
            validate_observation(changed)
        except ValueError:
            continue
        raise ValueError("Corrupted observation unexpectedly passed the CPU audit")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Create this report's new observation-audit.json exclusively")
    parser.add_argument("--self-test", action="store_true", help="Reject six in-memory corrupted observation variants; no GL")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    result = audit()
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.write:
        with (ROOT / "observation-audit.json").open("x") as stream:
            stream.write(text)
    print(text, end="")


if __name__ == "__main__":
    main()
