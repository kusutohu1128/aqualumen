"""Bounded, read-only audit of the one completed v0.8.1 smoke evidence packet."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from tools.report import check_png_bytes, metrics, validate_underwater_up

RUN = "v081-first-bed-smoke-20261002-1335"
PACK = "e8500f10bc66b1b4bc72a3eef1d4467bbe451d421310d1ab61e4f5b6ac841257"
WORLD = "b22dbccb-2970-41e6-847f-f183b1ec923d"
REQUEST = "95eeb2d9-a31f-4b81-9b4c-3ef0e3a6da9a"
SCENES = ["coast-day", "river-day", "ocean-day", "underwater", "underwater-up-near", "underwater-up-tilt"]

def require(value, message):
    if not value:
        raise ValueError(message)

def read(path, bound=2 * 1024 * 1024):
    require(path.is_file() and not path.is_symlink(), "Evidence file missing or redirected")
    before = path.stat()
    with path.open("rb") as stream:
        raw = stream.read(bound + 1)
    after = path.stat()
    require(len(raw) <= bound and (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), "Evidence changed or exceeded read bound")
    return raw

def audit_intervals(rows, scene):
    require(len(rows) >= 10, "Insufficient raw intervals")
    ns, values = [], []
    for index, row in enumerate(rows):
        require(set(row) == {"frame", "ms", "ns"} and row["frame"] == str(index), "CSV frame/header identity failed")
        require(row["ns"].isdigit() and int(row["ns"]) > 0, "CSV interval is not a positive integer ns")
        value, integer = float(row["ms"]), int(row["ns"])
        require(math.isfinite(value) and value > 0 and math.isclose(value, integer * 1e-6, rel_tol=0, abs_tol=1e-9), "CSV ns/ms disagreement")
        ns.append(integer); values.append(integer * 1e-6)
    calculated = metrics(values)
    for key, value in calculated.items():
        require(type(scene.get(key)) in (int, float) and math.isfinite(scene[key]) and
                math.isclose(value, scene[key], rel_tol=1e-9, abs_tol=1e-9), "Reported CSV metrics disagree: " + key)
    require(math.isclose(sum(ns) * 1e-9, scene["recorded_seconds"], rel_tol=0, abs_tol=1e-10), "Recorded seconds disagree with exact ns")
    return {**calculated, "total_ns": sum(ns), "recorded_seconds_from_integer_ns": sum(ns) * 1e-9}

def identity(row):
    require(row.get("world_id") == WORLD and row.get("pack_name") == "Aqualumen-0.8.1.zip" and row.get("pack_sha256") == PACK,
            "World/pack identity failed")
    require(row.get("shader_active") is True and row.get("shader_fallback") is False and
            row.get("resolution") == row.get("framebuffer_resolution") == [1600, 900] and
            row.get("player_dimension") == "minecraft:overworld", "Active pipeline/framebuffer/dimension failed")

def audit_field(row, raw):
    require(row.get("requestId") == REQUEST and row.get("worldId") == WORLD and row.get("observerVersion") == "0.3.6",
            "Bathymetry observation identity failed")
    for key in ("available", "scopeAuthorized", "stateRestored", "timingAcceptanceExcluded"):
        require(row.get(key) is True, "Bathymetry guard failed: " + key)
    require(row.get("visualQualityAccepted") is False and row.get("pass") == "TRANSLUCENT" and
            row.get("textureId") == row.get("modStoredTextureId") and type(row.get("textureId")) is int and row["textureId"] > 0,
            "Bathymetry live texture/pass mismatch")
    require(row.get("actualFormat") == 34836 and row.get("width") == row.get("height") == 64 and
            row.get("minFilter") == row.get("magFilter") == 9728 and row.get("wrapS") == row.get("wrapT") == 33071,
            "Bathymetry actual storage/filter mismatch")
    require(row.get("fieldFile") == REQUEST + ".rgba32f" and row.get("fieldEncoding") == "RGBA float32 little-endian, row-major z then x" and
            len(raw) == row.get("readbackBytes") == 65536 and hashlib.sha256(raw).hexdigest() == row.get("fieldSha256"), "Bathymetry raw file identity failed")
    grid = row.get("grid")
    require(isinstance(grid, list) and len(grid) == 4 and all(type(v) in (int, float) and math.isfinite(v) for v in grid) and grid[2] == 64,
            "Bathymetry grid invalid")
    values = struct.unpack("<16384f", raw)
    require(all(math.isfinite(v) for v in values), "Bathymetry nonfinite raw field")
    depths = []
    for offset in range(0, len(values), 4):
        depth, surface, valid, reserved = values[offset:offset + 4]
        if valid == 1:
            require(0 < depth <= 32.001 and reserved == 0 and abs(surface - grid[3]) <= .12002, "Invalid known bathymetry column")
            depths.append(depth)
        else:
            require((depth, surface, valid, reserved) == (0, 0, 0, 0), "Unknown bathymetry column is not cleared")
    require(len(depths) == row.get("knownColumns") == 4096 and row.get("ready") == 1, "Bathymetry readiness/known count failed")
    samples = row.get("samples")
    require(isinstance(samples, list) and len(samples) == 5, "Bathymetry sample count failed")
    for sample in samples:
        x, z = sample.get("texelX"), sample.get("texelZ")
        require(type(x) is type(z) is int and 0 <= x < 64 and 0 <= z < 64, "Bathymetry sample coordinate invalid")
        offset = (z * 64 + x) * 4
        require(list(values[offset:offset + 4]) == [sample.get(k) for k in ("depth", "surfaceRelativeY", "validity", "reserved")], "Bathymetry JSON/raw sample mismatch")
    return {"request": REQUEST, "observer_version": row["observerVersion"], "known_columns": len(depths),
            "ready": 1, "frame": row["snapshotFrame"], "raw_bytes": len(raw), "raw_sha256": row["fieldSha256"],
            "minimum_depth_m": min(depths), "maximum_depth_m": max(depths), "samples_match": True,
            "visual_quality_accepted": False, "timing_acceptance_excluded": True,
            "same_frame_absolute_camera_or_run_id_available": False}

def audit():
    directory = ROOT / "captures" / RUN
    run_raw, complete_raw = read(directory / "run.json"), read(directory / "complete.json")
    run, complete = json.loads(run_raw), json.loads(complete_raw)
    identity(run)
    require(run.get("run_id") == complete.get("run_id") == RUN and run.get("scenarios") == complete.get("scenarios") == SCENES and
            complete.get("status") == "complete" and complete.get("fixture_cleanup_complete") is True and
            not (directory / "aborted.json").exists(), "Run completion/scene identity failed")
    require(run.get("expected_pack_sha256") == PACK and run.get("expected_resolution") == [1600, 900] and
            run.get("warmup_seconds") == 20 and run.get("sample_seconds") == 5 and run.get("frame_limit") == 120 and run.get("vsync") is False and
            run.get("render_chunks") == 12 and run.get("simulation_chunks") == 6 and run.get("seed") == 308060 and
            run.get("world_generator") == "minecraft:noise/overworld" and run.get("terrain_fixture") == "No terrain placement", "Run configuration failed")
    for key, version in {"aqualumen_physics": "0.3.0", "aqualumen_benchmark": "0.3.7", "iris": "1.8.8+mc1.21.1", "minecraft": "1.21.1"}.items():
        require(run.get("mods", {}).get(key) == version, "Run mod version mismatch: " + key)
    require(run.get("gl_renderer", "").startswith("NVIDIA GeForce RTX 3080 Ti"), "Run renderer mismatch")
    storage = run.get("iris_render_target_storage", {})
    require(storage.get("available") is True and storage.get("bindingRestored") is True, "Storage observer failed")
    for query in storage.get("queries", []):
        index = query["index"]
        expected = (34836, 1600, 900) if index in (0, 4) else (34842, 1024, 512) if index in (6, 7) else (34842, 1600, 900)
        for side in ("main", "alt"):
            value = query[side]
            require((value["actualFormat"], value["width"], value["height"]) == expected, "Storage actual format/size mismatch")
    require({q["index"] for q in storage.get("queries", [])} == {0, 4, 5, 6, 7, 8}, "Storage target set mismatch")
    require({p.stem for p in directory.glob("*.png")} == set(SCENES), "Scene PNG set mismatch")
    poses = {"coast-day": ([-191.5, 64.1, 320.5], [0, 9]), "river-day": ([-63.5, 64.1, -63.5], [-45, 9]),
             "ocean-day": ([448.5, 64.1, -383.5], [-45, 9]), "underwater": ([448.5, 58, -383.5], [-45, 9]),
             "underwater-up-near": ([448.5, 60.7689, -383.5], [-45, -90]), "underwater-up-tilt": ([448.5, 60.7689, -383.5], [-45, -65])}
    captures = []
    for scene in SCENES:
        metadata_raw, csv_raw, png = read(directory / (scene + ".json")), read(directory / (scene + ".csv")), read(directory / (scene + ".png"), 16 * 1024 * 1024)
        row = json.loads(metadata_raw); identity(row)
        require(row.get("run_id") == RUN and row.get("scenario") == scene and row.get("workload") == "warmed-view" and
                row.get("window_focused") is True and row.get("camera_follows_local_player") is True and row.get("physics_active_seen") is True,
                "Scene/focus/local-camera/physics gate failed")
        position, rotation = poses[scene]
        require(row.get("actual_camera_rotation") == row.get("actual_player_rotation") == row.get("expected_camera_rotation") == rotation and
                math.dist(row["actual_player_position"], position) <= .005 and
                math.dist(row["actual_camera_position"], [position[0], position[1] + 1.62, position[2]]) <= .005,
                "Fixed scene camera pose failed")
        if scene.startswith("underwater-up-"):
            validate_underwater_up(row, scene)
        require(row.get("warmup_seconds") == 20 and row.get("sample_seconds_requested") == 5 and
                5 <= row.get("sample_seconds_actual", 0) < 5.5, "Scene warmup/sample gate failed")
        check_png_bytes(png, [1600, 900])
        calculated = audit_intervals(list(csv.DictReader(io.StringIO(csv_raw.decode()))), row)
        physics = json.loads(read(directory / (scene + "-physics.json")))
        require(physics == json.loads(row["physics_status_json"]) and physics.get("version") == "0.3.0-candidate" and physics.get("active") == 1 and
                physics.get("dimension") == 0 and physics.get("bathymetry", {}).get("ready") == 1 and physics["bathymetry"].get("failed") is False,
                "Physics snapshot mismatch")
        samples = json.loads(read(directory / (scene + "-physics-samples.json")))
        require(isinstance(samples, list) and len(samples) >= 5, "Missing timed physics samples")
        last = -1
        for sample in samples:
            status = json.loads(sample["raw_json"])
            require(last < sample["elapsed_seconds"] <= row["sample_seconds_actual"] and sample.get("active") is True and
                    status.get("version") == "0.3.0-candidate" and status.get("active") == 1 and status.get("dimension") == 0 and
                    sample["contacts"] == status["contacts"] <= row["maximum_contacts"] and sample["max_force"] == status["max_force"] <= row["maximum_force"] and
                    status.get("bathymetry", {}).get("ready") == 1 and status["bathymetry"].get("failed") is False,
                    "Timed physics sample identity/summary mismatch")
            last = sample["elapsed_seconds"]
        captures.append({"scene": scene, "status": "PNG/raw metrics/identity/focus/camera/physics match", **calculated,
                         "png_sha256": hashlib.sha256(png).hexdigest(), "csv_sha256": hashlib.sha256(csv_raw).hexdigest(),
                         "metadata_sha256": hashlib.sha256(metadata_raw).hexdigest(), "physics_samples": len(samples),
                         "maximum_contacts": row["maximum_contacts"], "actual_camera_position": row["actual_camera_position"],
                         "actual_camera_rotation": row["actual_camera_rotation"], "actual_underwater_head_proof": "underwater_up" in row})
    observation_raw = read(ROOT / "observations" / (REQUEST + ".json"))
    field = read(ROOT / "observations" / (REQUEST + ".rgba32f"), 65536)
    observation = audit_field(json.loads(observation_raw), field)
    observation["metadata_sha256"] = hashlib.sha256(observation_raw).hexdigest()
    return {"schema": 1, "smoke_evidence_pass": True, "run": RUN, "pack_sha256": PACK,
            "run_metadata_sha256": hashlib.sha256(run_raw).hexdigest(), "complete_sha256": hashlib.sha256(complete_raw).hexdigest(),
            "complete_utc": complete["utc"], "resolution": [1600, 900], "recorded_frame_limit": 120,
            "warmup_seconds": 20, "sample_seconds": 5, "captures": captures, "observations": [observation],
            "total_frames": sum(r["frames"] for r in captures), "total_ns": sum(r["total_ns"] for r in captures),
            "release_or_1440p_acceptance": False, "full_visual_goal_complete": False, "FPS_floor_guaranteed": False,
            "visual_pixels_scored": False, "native_GPU_tests_reexecuted": False, "world_or_game_changes": False,
            "ordinary_handoff_verified_by_this_script": False,
            "coordinate_limit": "Bathymetry snapshot has no same-frame absolute camera, run_id or pack hash; saved-floor joins remain conditional. Underwater head proof exists for the two up scenes, not inferred for all six.",
            "timing_limit": "Six short warmed views at configured cap120; no uncapped throughput, temporal shoreline, complete compatibility suite or overall physical/visual completion is established."}

def self_test():
    base = ROOT / "captures" / RUN
    rows = list(csv.DictReader(io.StringIO(read(base / "coast-day.csv").decode())))
    scene = json.loads(read(base / "coast-day.json"))
    result = audit_intervals(rows, scene)
    assert result.get("frames") == len(rows), "Actual CSV frame count must be preserved and verified"
    tests = ["Actual CSV frame count and integer ns preserved and verified"]
    for label, mutate in (("nonsequential frame rejected", lambda r: r[0].update(frame="1")),
                          ("ns/ms mismatch rejected", lambda r: r[0].update(ns=str(int(r[0]["ns"]) + 1000000))),
                          ("nonfinite interval rejected", lambda r: r[0].update(ms="NaN"))):
        corrupt = [dict(r) for r in rows]; mutate(corrupt)
        try:
            audit_intervals(corrupt, scene)
        except ValueError:
            tests.append(label)
        else:
            raise AssertionError(label)
    observation = json.loads(read(ROOT / "observations" / (REQUEST + ".json")))
    field = read(ROOT / "observations" / (REQUEST + ".rgba32f"), 65536)
    assert audit_field(observation, field)["known_columns"] == 4096
    tests.append("actual full raw field and selected samples verified")
    for label, damaged in (("truncated raw field rejected", field[:-4]), ("modified raw field rejected", bytes([field[0] ^ 1]) + field[1:])):
        try:
            audit_field(observation, damaged)
        except ValueError:
            tests.append(label)
        else:
            raise AssertionError(label)
    return {"passed": True, "tests": tests}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write", action="store_true", help="Generate only adjacent smoke-audit.json")
    args = parser.parse_args()
    try:
        if args.self_test:
            print(json.dumps(self_test(), indent=2))
        else:
            result = audit(); result["cpu_tests"] = self_test()
            result["script_sha256"] = hashlib.sha256(read(Path(__file__))).hexdigest()
            output = ROOT / "smoke-audit.json"
            if output.exists():
                prior = json.loads(read(output))
                if "cpu_test_first_failure" in prior:
                    result["cpu_test_first_failure"] = prior["cpu_test_first_failure"]
            if args.write:
                output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            print(json.dumps({"smoke_evidence_pass": True, "scenes": len(result["captures"]), "total_frames": result["total_frames"],
                              "total_ns": result["total_ns"], "known_columns": result["observations"][0]["known_columns"],
                              "release_or_1440p_acceptance": False, "full_visual_goal_complete": False}, indent=2))
    except Exception as error:
        print(json.dumps({"smoke_evidence_pass": False, "error_class": type(error).__name__,
                          "reason": str(error) if isinstance(error, (ValueError, AssertionError)) else "bounded audit boundary failed"}))
        raise SystemExit(1)
