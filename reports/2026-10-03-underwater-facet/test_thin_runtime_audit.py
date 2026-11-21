#!/usr/bin/env python3
"""CPU-only audit of the bounded 0.8.6 five-view TEST capture; no game access."""
import argparse
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest
from zipfile import ZipFile

sys.dont_write_bytecode = True
import report

PACK_NAME = "Aqualumen-0.8.6.zip"
PACK_SHA = "16a7da88b7a5ba11d6aadfd56c717875fc61153b81cc859b4503da620c56c9d0"
PREVIOUS_SHA = "ed515dca837333cd94e380af9a7f25e827ac2ba228aa5e380396d8a08dcccff8"
WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d"
SIZE = [1600, 900]
SCENES = ["coast-day", "river-day", "underwater-up-near", "underwater-up-deep", "underwater-up-tilt"]


def validate_run(run, complete):
    """Reject a capture outside the explicitly approved TEST identity/configuration."""
    if run.get("world_id") != WORLD_ID:
        raise ValueError("Wrong approved world UUID")
    if run.get("shader_active") is not True:
        raise ValueError("Shader is not active")
    if run.get("pack_sha256") != PACK_SHA:
        raise ValueError("Wrong candidate pack SHA")
    if complete.get("status") != "complete" or not run.get("run_id") or complete.get("run_id") != run["run_id"]:
        raise ValueError("Incomplete capture or run identity mismatch")
    exact = {"schema": 2, "pack_name": PACK_NAME, "expected_pack_sha256": PACK_SHA,
             "world_generator": "minecraft:noise/overworld", "seed": 308060,
             "resolution": SIZE, "framebuffer_resolution": SIZE, "expected_resolution": SIZE,
             "player_dimension": "minecraft:overworld", "render_chunks": 12,
             "simulation_chunks": 6, "frame_limit": 120, "warmup_seconds": 5.0,
             "sample_seconds": 5.0, "scenarios": SCENES, "terrain_fixture": "No terrain placement"}
    for key, expected in exact.items():
        if run.get(key) != expected or isinstance(run.get(key), bool):
            raise ValueError(f"Wrong runtime configuration: {key}")
    if any(type(run[key]) is not int for key in ("schema", "seed", "render_chunks", "simulation_chunks", "frame_limit")):
        raise ValueError("Runtime integer configuration is not recorded as integers")
    if (run.get("shader_fallback") is not False or run.get("vsync") is not False or
            Path(run.get("world_directory", "")).name != "AqualumenNaturalV2" or
            complete.get("scenarios") != SCENES or complete.get("fixture_cleanup_complete") is not True):
        raise ValueError("Fallback, world marker, completion or cleanup contract failed")
    mods = run.get("mods", {})
    for key, expected in {"aqualumen_benchmark": "0.3.9", "aqualumen_physics": "0.3.0",
                          "iris": "1.8.8+mc1.21.1", "sodium": "0.6.9+mc1.21.1",
                          "minecraft": "1.21.1", "java": "21"}.items():
        if mods.get(key) != expected:
            raise ValueError(f"Wrong installed mod version: {key}")
    if "NVIDIA" not in run.get("gl_renderer", "") or "3080 Ti" not in run["gl_renderer"]:
        raise ValueError("Recorded renderer is not the expected NVIDIA GPU")
    properties = {}
    for line in run.get("iris_configuration", "").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if key in properties:
                raise ValueError("Ambiguous recorded Iris configuration")
            properties[key] = value
    if properties.get("enableShaders") != "true" or properties.get("shaderPack") != PACK_NAME:
        raise ValueError("Recorded Iris selection does not match candidate")
    storage = run.get("iris_render_target_storage", {})
    queries = storage.get("queries", [])
    if (storage.get("available") is not True or storage.get("bindingRestored") is not True or
            not isinstance(queries, list) or len(queries) != 6 or
            {row.get("index") for row in queries} != {0, 4, 5, 6, 7, 8}):
        raise ValueError("Actual Iris storage observer is incomplete or unrestored")
    textures = set()
    for query in queries:
        index = query["index"]
        width, height = (1024, 512) if index in (6, 7) else SIZE
        fmt, name = (34836, "RGBA32F") if index in (0, 4) else (34842, "RGBA16F")
        if [query.get("declaredWidth"), query.get("declaredHeight"), query.get("declaredFormat")] != [width, height, name]:
            raise ValueError(f"Wrong declared Iris storage at C{index}")
        for side in ("main", "alt"):
            actual = query.get(side, {})
            texture = actual.get("textureId")
            if (type(texture) is not int or texture <= 0 or texture in textures or
                    [actual.get("width"), actual.get("height"), actual.get("actualFormat")] != [width, height, fmt]):
                raise ValueError(f"Wrong actual Iris storage at C{index}/{side}")
            textures.add(texture)


def read_intervals(path):
    """Read public frame CSV, preserving integer nanoseconds as the authority."""
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("Frame CSV exceeds bounded audit size")
    ns_values = []
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["frame", "ns", "ms"]:
            raise ValueError("Wrong raw frame CSV columns")
        for frame, row in enumerate(reader):
            if (set(row) != {"frame", "ns", "ms"} or frame >= 100000 or row.get("frame") != str(frame) or
                    not row.get("ns", "").isascii() or not row["ns"].isdigit()):
                raise ValueError("Invalid sequential frame index or integer nanoseconds")
            ns = int(row["ns"])
            try:
                ms = Decimal(row["ms"])
            except (InvalidOperation, TypeError) as error:
                raise ValueError("Invalid CSV milliseconds") from error
            # Recorder.java emits Double.toString(longNs * 1e-6), not exact
            # decimal division. Integer ns remains authoritative and lossless.
            if not 0 < ns < 2**63 or not ms.is_finite() or float(ms) != ns * 1e-6:
                raise ValueError("CSV milliseconds differ from raw integer nanoseconds")
            ns_values.append(ns)
    if len(ns_values) < 10:
        raise ValueError("Insufficient raw frame intervals")
    return ns_values, [ns * 1e-6 for ns in ns_values]


def compare_shader_archives(previous, candidate):
    """Compare provided immutable ZIP contents, without extraction or writes."""
    contents = []
    for path in (previous, candidate):
        with ZipFile(path) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(names) != len(set(names)) or len(names) > 1024 or sum(entry.file_size for entry in entries) > 64 * 1024 * 1024:
                raise ValueError("Duplicate or oversized shader ZIP contents")
            contents.append({name: archive.read(name) for name in names})
    old, new = contents
    if old.keys() != new.keys():
        raise ValueError("Candidate ZIP file inventory changed")
    changed = [name for name in sorted(old) if old[name] != new[name]]
    if changed != ["shaders/gbuffers_water.vsh"]:
        raise ValueError("Candidate must change ONLY gbuffers_water.vsh")
    return {"changed_entries": changed, "unchanged_entries": len(old) - 1,
            "previous_water_vs_sha256": hashlib.sha256(old[changed[0]]).hexdigest(),
            "candidate_water_vs_sha256": hashlib.sha256(new[changed[0]]).hexdigest(),
            "water_fs_sha256": hashlib.sha256(new["shaders/gbuffers_water.fsh"]).hexdigest()}


def audit_scene(run, row, scenario, ns_values, values):
    """Validate one measured pose and independently recompute its timing evidence."""
    if row.get("window_focused") is not True:
        raise ValueError(f"Unfocused scene: {scenario}")
    exact = {"scenario": scenario, "run_id": run["run_id"], "world_id": WORLD_ID,
             "pack_name": PACK_NAME, "pack_sha256": PACK_SHA, "resolution": SIZE,
             "framebuffer_resolution": SIZE, "player_dimension": "minecraft:overworld",
             "workload": "warmed-view", "warmup_seconds": 5.0, "sample_seconds_requested": 5.0,
             "contact_driver": "none"}
    if any(row.get(key) != expected for key, expected in exact.items()):
        raise ValueError(f"Scene identity/configuration changed: {scenario}")
    for key in ("shader_active", "camera_follows_local_player", "physics_active_seen"):
        if row.get(key) is not True:
            raise ValueError(f"Scene guard missing: {scenario}/{key}")
    if row.get("shader_fallback") is not False or not row.get("camera_lock"):
        raise ValueError(f"Fallback or missing camera lock: {scenario}")
    computed = report.metrics(values)
    ordered = sorted(ns_values)
    slow = max(1, math.ceil(len(ns_values) * .01))
    integer_metrics = {"frames": len(ns_values), "mean_fps": 1e9 * len(ns_values) / sum(ns_values),
                       "one_percent_low_fps": 1e9 * slow / sum(ordered[-slow:]),
                       "p99_ms": ordered[math.ceil(len(ns_values) * .99) - 1] / 1e6,
                       "max_ms": max(ns_values) / 1e6, "min_instantaneous_fps": 1e9 / max(ns_values),
                       "frames_over_16_667_ms": sum(ns * 60 > 1000000000 for ns in ns_values)}
    for key, value in computed.items():
        saved = row.get(key)
        if (isinstance(saved, bool) or not isinstance(saved, (float, int)) or not math.isfinite(saved) or
                abs(saved - value) > max(.001, abs(value) * .00001) or
                abs(integer_metrics[key] - value) > max(1e-9, abs(value) * 1e-12)):
            raise ValueError(f"Frame metric mismatch: {scenario}/{key}")
    for key in ("frames", "frames_over_16_667_ms"):
        if type(row[key]) is not int or row[key] != integer_metrics[key]:
            raise ValueError(f"Raw integer frame count mismatch: {scenario}/{key}")
    recorded = sum(ns_values) / 1e9
    actual = row.get("sample_seconds_actual")
    if (isinstance(actual, bool) or not isinstance(actual, (int, float)) or not math.isfinite(actual) or
            actual < 4.9 or recorded < 4.9 or recorded > actual + 1e-8 or
            not math.isclose(row.get("recorded_seconds", -1), recorded, rel_tol=0, abs_tol=1e-8)):
        raise ValueError(f"Truncated or inconsistent raw timing duration: {scenario}")
    if scenario in report.UNDERWATER_UP_SCENARIOS:
        report.validate_underwater_up(row, scenario)
    else:
        player, rotation = (([-191.5, 64.1, 320.5], [0, 9]) if scenario == "coast-day"
                            else ([-63.5, 64.1, -63.5], [-45, 9]))
        camera = [player[0], player[1] + 1.62, player[2]]
        if (math.dist(report.vector(row.get("actual_player_position"), scenario, "player"), player) > .05 or
                math.dist(report.vector(row.get("actual_camera_position"), scenario, "camera"), camera) > .05 or
                row.get("expected_camera_rotation") != rotation):
            raise ValueError(f"Wrong fixed coast/river pose: {scenario}")
        for key in ("actual_camera_rotation", "actual_player_rotation"):
            observed = row.get(key)
            if (not isinstance(observed, list) or len(observed) != 2 or
                    any(isinstance(part, bool) or not isinstance(part, (int, float)) or not math.isfinite(part) or
                        abs(part - expected) > .05 for part, expected in zip(observed, rotation))):
                raise ValueError(f"Wrong fixed orientation: {scenario}/{key}")
    physics = json.loads(row.get("physics_status_json", "{}"))
    bathymetry = physics.get("bathymetry", {})
    if (physics.get("version") != "0.3.0-candidate" or physics.get("active") != 1 or physics.get("dimension") != 0 or
            bathymetry.get("ready") != 1 or bathymetry.get("failed") is not False or
            type(bathymetry.get("known_columns")) is not int or not 1 <= bathymetry["known_columns"] <= 4096):
        raise ValueError(f"Physics/bathymetry status not ready: {scenario}")
    result = {"scenario": scenario, "raw_ns_count": len(ns_values), "raw_ns_sum": sum(ns_values),
              "recorded_seconds": recorded, "metrics": integer_metrics, "focused": True,
              "actual_player_position": row["actual_player_position"], "actual_camera_position": row["actual_camera_position"],
              "actual_camera_rotation": row["actual_camera_rotation"], "physics_active": True,
              "known_columns_at_capture": bathymetry["known_columns"]}
    if scenario in report.UNDERWATER_UP_SCENARIOS:
        measured = row["underwater_up"]
        result["underwater_head"] = {key: measured[key] for key in
                                     ("camera_submersion_type", "actual_eye_depth", "measured_surface_y",
                                      "camera_first_person", "camera_eye_match", "actual_world_time", "actual_server_world_time")}
    return result


def audit_runtime(directory, candidate_zip, previous_zip):
    """Return a read-only CPU audit; no report, capture, config or game writes."""
    if (directory / "aborted.json").exists():
        raise ValueError("Run contains an abort record")
    run = json.loads((directory / "run.json").read_text())
    complete = json.loads((directory / "complete.json").read_text())
    validate_run(run, complete)
    for path, expected in ((candidate_zip, PACK_SHA), (previous_zip, PREVIOUS_SHA)):
        if path.stat().st_size > 64 * 1024 * 1024 or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Immutable ZIP identity mismatch: {path.name}")
    zip_comparison = compare_shader_archives(previous_zip, candidate_zip)
    scenes = []
    for scenario in SCENES:
        png = directory / f"{scenario}.png"
        report.check_png(png, SIZE)
        row = json.loads((directory / f"{scenario}.json").read_text())
        ns_values, values = read_intervals(directory / f"{scenario}.csv")
        observed = audit_scene(run, row, scenario, ns_values, values)
        observed["artifacts_sha256"] = {f"{scenario}.{suffix}": hashlib.sha256((directory / f"{scenario}.{suffix}").read_bytes()).hexdigest()
                                        for suffix in ("png", "json", "csv")}
        observed["png_full_crc_and_decode"] = True
        scenes.append(observed)
    return {"available": True, "audit": "read-only CPU 0.8.6 five warmed-view capture audit",
            "run_id": run["run_id"], "world_id": WORLD_ID, "seed": 308060,
            "pack_name": PACK_NAME, "pack_sha256": PACK_SHA, "previous_pack_sha256": PREVIOUS_SHA,
            "mods": {key: run["mods"][key] for key in ("aqualumen_benchmark", "aqualumen_physics", "iris", "sodium")},
            "resolution": SIZE, "frame_limit": 120, "vsync": False, "render_chunks": 12, "simulation_chunks": 6,
            "warmup_seconds": 5, "sample_seconds": 5, "scene_count": len(scenes),
            "completed_utc": complete.get("utc"), "fixture_cleanup_complete_reported": True,
            "iris_actual_storage_complete_and_binding_restored": True, "zip_source_comparison": zip_comparison,
            "scenes": scenes,
            "claims": {"completed_focused_warmed_900p_views": True, "natural_visual_acceptance": False,
                       "live_thin_sheet_topology_reproduced": False, "same_frame_shader_fetch_proof": False,
                       "persisted_world_cleanup_independently_audited": False, "motion_acceptance": False,
                       "1440p_acceptance": False, "sixty_fps_floor_guaranteed": False, "release_acceptance": False,
                       "full_goal_complete": False},
            "limits": ["PNG integrity and head/pose metadata do not judge natural appearance.",
                       "Only five short warmed views; frame limit120, not uncapped throughput.",
                       "Storage observer proves recorded allocation, not per-fragment consumption or freshness.",
                       "No live thin-water terrain fixture; integrated-server safety remains the recorder's runtime guard."]}


class RuntimeContractTests(unittest.TestCase):
    def test_wrong_world_cannot_be_accepted_as_the_approved_test_capture(self):
        run = {"world_id": "not-the-approved-world"}
        with self.assertRaises(ValueError):
            validate_run(run, {})

    def test_disabled_shader_is_not_an_active_candidate_capture(self):
        with self.assertRaises(ValueError):
            validate_run({"world_id": WORLD_ID, "shader_active": False}, {})

    def test_active_old_pack_does_not_substitute_for_this_candidate(self):
        with self.assertRaises(ValueError):
            validate_run({"world_id": WORLD_ID, "shader_active": True, "pack_sha256": PREVIOUS_SHA}, {})

    def test_an_active_pack_alone_does_not_accept_incomplete_runtime_evidence(self):
        with self.assertRaises(ValueError):
            validate_run({"world_id": WORLD_ID, "shader_active": True, "pack_sha256": PACK_SHA}, {})

    def test_csv_cannot_silently_replace_raw_nanoseconds_with_inconsistent_ms(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix="aqualumen-csv-contract-") as temporary:
            path = Path(temporary) / "intervals.csv"
            path.write_text("frame,ns,ms\n" + "".join(f"{frame},500000000,1.0\n" for frame in range(10)))
            with self.assertRaises(ValueError):
                read_intervals(path)

    def test_real_recorder_binary64_ms_rounding_retains_exact_raw_nanoseconds(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix="aqualumen-csv-rounding-") as temporary:
            path = Path(temporary) / "intervals.csv"
            # Actual Recorder.java emission: long nanoseconds * binary64 1e-6.
            path.write_text("frame,ns,ms\n" + "".join(f"{frame},8444413,8.444412999999999\n" for frame in range(10)))
            ns_values, values = read_intervals(path)
            self.assertEqual(ns_values, [8444413] * 10)
            self.assertEqual(values, [8444413 * 1e-6] * 10)

    def test_a_changed_fragment_shader_is_not_the_vs_only_topology_candidate(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix="aqualumen-zip-contract-") as temporary:
            previous, candidate = (Path(temporary) / name for name in ("previous.zip", "candidate.zip"))
            for path, fragment in ((previous, "old"), (candidate, "changed")):
                with ZipFile(path, "w") as archive:
                    archive.writestr("shaders/gbuffers_water.vsh", path.name)
                    archive.writestr("shaders/gbuffers_water.fsh", fragment)
            with self.assertRaises(ValueError):
                compare_shader_archives(previous, candidate)

    def test_unfocused_scene_is_not_accepted_as_a_focused_measurement(self):
        with self.assertRaises(ValueError):
            audit_scene({}, {"window_focused": False}, "coast-day", [1000000] * 10, [1.0] * 10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("run", nargs="?", type=Path, help="Completed shipping-smoke directory")
    repository = Path(__file__).resolve().parents[1]
    parser.add_argument("--pack", type=Path, default=repository / "dist" / PACK_NAME)
    parser.add_argument("--previous-pack", type=Path, default=repository / "dist" / "Aqualumen-0.8.5.zip")
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeContractTests))
        return 0 if result.wasSuccessful() else 1
    if args.run is None:
        parser.error("A completed shipping-smoke directory is required")
    print(json.dumps(audit_runtime(args.run, args.pack, args.previous_pack), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
