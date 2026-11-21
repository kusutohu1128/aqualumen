"""CPU-only audit of the three explicitly authorized coast-atlas captures.

Default execution only prints results; --write writes only the two adjacent
audit JSON files. No game, GPU, network, control, config or world writes.
"""
import argparse
import collections
import copy
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d"
CAMERA = [-191.5, 65.71999988555908, 320.5]
PLAYER = [-191.5, 64.1, 320.5]
ROTATION = [0.0, 9.0]
SIZE = [1600, 900]
SURFACE = 62.88888931274414
CAPTURES = {
    "shore-atlas-optical-r1-20261002-1132": (
        "Aqualumen-ShoreProbe-optical-r1.zip",
        "cbf822dd488203e464703f3e2b5c1757d2a31d4139669550470f437e14c72af5"),
    "shore-atlas-geometry-r1-20261002-1137": (
        "Aqualumen-ShoreProbe-geometry-r1.zip",
        "4fc904e301afe799f18922fa6c4af539a375872125245ba566f6fab30054aaed"),
    "shore-atlas-transport-r2-20261002-1142": (
        "Aqualumen-ShoreProbe-transport-r2.zip",
        "6ef8effc0db4c546d11b7c7fbed6f4713991b0bbd41b1e9272aefc37a7e49ff0"),
}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


REPORT = module("shore_packet_report", REPO / "tools/report.py")
ANVIL = module("shore_packet_anvil", REPO / "tools/audit-fixture-air.py")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bounded(path, limit):
    require(not path.is_symlink(), "Evidence symlinks are forbidden")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, "Evidence exceeds bounded read")
    return raw


def read_json(path):
    return json.loads(bounded(path, 1024 * 1024))


def near_vector(actual, expected):
    return (isinstance(actual, list) and len(actual) == len(expected) and
            all(type(value) in (int, float) and math.isfinite(value) and
                abs(value - target) <= 1e-6 for value, target in zip(actual, expected)))


def validate_metadata(run_id, run, scene, complete):
    """Validate public capture observations, without exporting private fields."""
    require(run_id in CAPTURES, "Capture is outside the three-run authorization")
    pack, pack_sha = CAPTURES[run_id]
    for data in (run, scene):
        require(data.get("run_id") == run_id, "Run identity mismatch")
        require(data.get("world_id") == WORLD_ID, "Disposable world UUID mismatch")
        require(data.get("pack_name") == pack and data.get("pack_sha256") == pack_sha,
                "Pack identity mismatch")
        require(data.get("shader_active") is True and data.get("shader_fallback") is False,
                "Shader is inactive or fallback is recorded")
        require(data.get("resolution") == SIZE and data.get("framebuffer_resolution") == SIZE,
                "Actual window/framebuffer size mismatch")
        require(data.get("player_dimension") == "minecraft:overworld", "Dimension mismatch")
    require(run.get("expected_pack_sha256") == pack_sha and run.get("expected_resolution") == SIZE,
            "Expected capture identity mismatch")
    require(type(run.get("seed")) is int and run["seed"] == 308060 and
            run.get("world_generator") == "minecraft:noise/overworld" and
            Path(run.get("world_directory", "")).name == "AqualumenNaturalV2", "World marker mismatch")
    require(type(run.get("frame_limit")) is int and run["frame_limit"] == 120 and
            run.get("render_chunks") == 12 and run.get("simulation_chunks") == 6 and
            run.get("vsync") is False, "Recorded runtime options mismatch")
    require(run.get("scenarios") == ["coast-day"] and scene.get("scenario") == "coast-day" and
            scene.get("workload") == "warmed-view", "Scene/workload mismatch")
    require(complete.get("run_id") == run_id and complete.get("status") == "complete" and
            complete.get("scenarios") == ["coast-day"] and
            complete.get("fixture_cleanup_complete") is True, "Capture is incomplete")
    properties = {}
    for line in run.get("iris_configuration", "").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            properties[key] = value
    require(properties.get("shaderPack") == pack and properties.get("enableShaders") == "true",
            "Recorded Iris selection/enabling mismatch")
    require(near_vector(scene.get("actual_camera_position"), CAMERA) and
            near_vector(scene.get("actual_player_position"), PLAYER) and
            all(near_vector(scene.get(key), ROTATION) for key in
                ("actual_camera_rotation", "actual_player_rotation", "expected_camera_rotation")),
            "Recorded coast pose mismatch")
    require(scene.get("window_focused") is True and scene.get("camera_follows_local_player") is True and
            bool(scene.get("camera_lock")), "Capture focus/camera identity is missing")
    require(run.get("warmup_seconds") == 10 and scene.get("warmup_seconds") == 10 and
            run.get("sample_seconds") == 5 and scene.get("sample_seconds_requested") == 5 and
            type(scene.get("sample_seconds_actual")) in (int, float) and
            math.isfinite(scene["sample_seconds_actual"]) and scene["sample_seconds_actual"] >= 4.9,
            "Sample duration mismatch")
    return {"pose_validated": True, "selected_and_enabled": True, "no_fallback": True,
            "frame_limit_setting": 120, "resolution": SIZE, "camera_position": CAMERA,
            "player_position": PLAYER, "camera_rotation": ROTATION,
            "world_id": WORLD_ID, "seed": 308060, "pack": pack, "pack_sha256": pack_sha}


def raw_metrics(records):
    """Keep nanoseconds as integers; milliseconds are an additional cross-check."""
    values = []
    for index, record in enumerate(records):
        require(record.get("frame") == str(index), "Raw frame sequence mismatch")
        text = record.get("ns", "")
        require(re.fullmatch(r"[0-9]+", text) is not None, "Nanoseconds must be lossless decimal integers")
        ns = int(text)
        require(0 < ns <= 2**63 - 1, "Invalid nanosecond interval")
        ms = float(record["ms"])
        require(math.isfinite(ms) and ms > 0 and abs(ms - ns / 1e6) <= 1e-10,
                "Raw ns/ms disagreement")
        values.append(ns)
    require(len(values) >= 10, "Too few raw intervals")
    ordered = sorted(values)
    count = max(1, math.ceil(len(values) * .01))
    total = sum(values)
    result = {"frames": len(values), "mean_fps": 1e9 * len(values) / total,
              "one_percent_low_fps": 1e9 * count / sum(ordered[-count:]),
              "p99_ms": ordered[math.ceil(len(values) * .99) - 1] / 1e6,
              "max_ms": ordered[-1] / 1e6, "min_instantaneous_fps": 1e9 / ordered[-1],
              "frames_over_16_667_ms": sum(ns * 60 > 1_000_000_000 for ns in values)}
    return result, total


def audit_three():
    results = []
    for run_id in CAPTURES:
        directory = HERE / "captures" / run_id
        require(not (directory / "aborted.json").exists(), "An abort record prevents acceptance")
        run, scene, complete = [read_json(directory / name) for name in
                                ("run.json", "coast-day.json", "complete.json")]
        gates = validate_metadata(run_id, run, scene, complete)
        csv_bytes = bounded(directory / "coast-day.csv", 4 * 1024 * 1024)
        records = list(csv.DictReader(io.StringIO(csv_bytes.decode("utf-8"))))
        calculated, total = raw_metrics(records)
        for key, value in calculated.items():
            require(type(scene.get(key)) in (int, float) and math.isfinite(scene[key]) and
                    abs(value - scene[key]) <= max(1e-9, abs(value) * 1e-12), "Raw metric mismatch: " + key)
        require(abs(total / 1e9 - scene["recorded_seconds"]) <= 1e-9, "Recorded duration mismatch")
        REPORT.check_png(directory / "coast-day.png", tuple(SIZE))
        files = {name: {"sha256": hashlib.sha256(bounded(directory / name, REPORT.PNG_MAX_BYTES)).hexdigest(),
                        "bytes": (directory / name).stat().st_size}
                 for name in ("run.json", "complete.json", "coast-day.json", "coast-day.csv", "coast-day.png")}
        results.append({"run_id": run_id, "passed": True, "metadata": gates,
                        "completed_utc": complete.get("utc"), "png_integrity_passed": True,
                        "metrics_recomputed_from_integer_ns": calculated, "total_ns": total,
                        "recorded_seconds": total / 1e9, "files": files})
    return {"passed": True, "capture_count": 3, "captures": results,
            "ignored_additional_capture_directories": True,
            "existing_1440p_load_run_validator_modified": False,
            "limits": ["Atlas-debug captures are not normal-pack quality or FPS acceptance.",
                       "Recorded frame-limit120 is a setting, not an independently tested pacing guarantee.",
                       "Focus and actual-camera pose are capture-boundary observations.",
                       "PNG integrity and metadata do not prove optical correctness or causal source attribution.",
                       "No additional runtime, GPU, control, accounts or process-argv inspection."]}


def saved_shore_profile():
    """Read only the fixed V2 save; no world/region/plot override is accepted."""
    world = ANVIL.WORLD
    require(world.resolve() == world.absolute(), "World symlink redirection is forbidden")
    marker = dict(line.split("=", 1) for line in (world / "aqualumen-world.properties").read_text().splitlines()
                  if line and not line.startswith("#"))
    ANVIL.validate_marker(world.name, marker)
    region = world / "region/r.-1.0.mca"
    before = region.stat()
    require(8192 <= before.st_size <= ANVIL.LIMIT, "Region size exceeds bounded plan")
    raw = bounded(region, ANVIL.LIMIT)
    require(len(raw) == before.st_size, "Region changed during initial read")
    xs, zs = range(-216, -167), range(320, 385)
    chunks = {}
    for cx, cz in sorted({(x // 16, z // 16) for x in xs for z in zs}):
        require((cx // 32, cz // 32) == (-1, 0), "Chunk outside approved shore region")
        chunks[cx, cz] = ANVIL.decode_chunk(raw, region, cx, cz)[0]

    def cell(x, y, z):
        return ANVIL.block_state(chunks[x // 16, z // 16], x, y, z)

    fluid = {"minecraft:water", "minecraft:seagrass", "minecraft:tall_seagrass",
             "minecraft:kelp", "minecraft:kelp_plant"}
    air = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
    full_bed = {"minecraft:" + name for name in ("sand", "gravel", "dirt", "stone", "clay", "sandstone",
                "granite", "diorite", "andesite", "deepslate", "coal_ore", "copper_ore", "moss_block")}
    rows, excluded = {}, collections.Counter()
    for x in xs:
        for z in zs:
            top = cell(x, 62, z)
            if top["Name"] not in fluid:
                excluded["not_water_at_Y62"] += 1
                continue
            if top["Name"] == "minecraft:water" and top.get("Properties", {}).get("level") != "0":
                excluded["non_source_top"] += 1
                continue
            if cell(x, 63, z)["Name"] not in air:
                excluded["not_exposed_air_above"] += 1
                continue
            for y in range(61, -1, -1):
                state = cell(x, y, z)
                if state["Name"] in fluid:
                    continue
                if state["Name"] not in full_bed or state.get("Properties", {}).get("waterlogged") == "true":
                    excluded["unknown_or_non_full_first_support"] += 1
                    break
                rows[x, z] = {"bed_block_y": y, "bed_surface_y": y + 1, "bed_material": state["Name"],
                              "nominal_depth_m": SURFACE - (y + 1)}
                break
            else:
                excluded["no_bed_to_Y0"] += 1
    centre = []
    for z in zs:
        row = rows.get((-192, z))
        require(row is not None, "Centre profile is not a qualified exposed sea column")
        if centre and all(centre[-1][key] == value for key, value in row.items()):
            centre[-1]["z_last"] = z
        else:
            centre.append({"z_first": z, "z_last": z, **row})
    after = region.stat()
    stable = (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    require(stable, "Saved region changed during audit; reject profile")
    require(len(rows) == 3040 and len(xs) * len(zs) == 3185, "Saved-shore counts differ from observed checkpoint")
    return {"schema": 1, "audit": "bounded read-only saved-shore shape; not a camera-ray join",
            "observed_utc": datetime.now(timezone.utc).isoformat(), "passed": True,
            "marker_verified": {"world_name": world.name, "world_id": marker["world_id"], "seed": int(marker["seed"]),
                                "generator": marker["generator"], "schema": marker["schema"]},
            "region": {"name": region.name, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw),
                       "mtime_ns_before": before.st_mtime_ns, "mtime_ns_after": after.st_mtime_ns,
                       "stable_size_and_mtime_during_read": stable, "decoded_chunk_count": len(chunks),
                       "data_version": 3955},
            "shape_bounds": {"x_inclusive": [-216, -168], "z_inclusive": [320, 384], "y_scanned_inclusive": [0, 63],
                             "columns_total": 3185, "exposed_contiguous_wet_columns": len(rows), "excluded": dict(excluded),
                             "bed_surface_y_range": [min(v["bed_surface_y"] for v in rows.values()), max(v["bed_surface_y"] for v in rows.values())],
                             "nominal_depth_range_m": [min(v["nominal_depth_m"] for v in rows.values()), max(v["nominal_depth_m"] for v in rows.values())]},
            "surface_basis": {"reference_y": SURFACE, "source": "coast capture fluid surface; exposed Y62 source-water columns",
                              "depth_is_surface_minus_saved_full_block_top": True},
            "capture_pose": {"camera_position": CAMERA, "yaw_pitch": ROTATION, "forward_horizontal_axis": "+Z"},
            "centre_x": -192, "centre_profile": centre,
            "transverse_bed_top_grid": {"x_columns": [-208, -200, -192, -184, -176],
                "rows": [{"z": z, "bed_surface_y": [rows.get((x, z), {}).get("bed_surface_y") for x in [-208, -200, -192, -184, -176]]}
                         for z in [320, 324, 328, 332, 336, 340, 344, 348, 352, 360, 368, 376, 384]]},
            "limits": {"camera_ray_join_proven": False, "same_frame_live_geometry_join_proven": False,
                       "atlas_path_correctness_proven": False, "ordinary_world_read": False, "world_writes": False,
                       "private_world_full_paths_exported": False,
                       "interpretation": "Saved sea floor deepens from0.889m to4.889–8.889m ahead;4–9m atlas thickness is not ruled out by the1-block site label. Pixel-to-interface-to-receiver join, waves and occlusion remain unproven."}}


def self_test():
    result = audit_three()
    assert result["passed"] is True, "completed three-coast captures must satisfy packet contract"
    tests = ["actual three completed captures accepted"]
    run_id = next(iter(CAPTURES))
    directory = HERE / "captures" / run_id
    base = [read_json(directory / name) for name in ("run.json", "coast-day.json", "complete.json")]
    mutations = [
        ("reject UUID drift", 0, "world_id", "wrong"),
        ("reject selected-pack drift", 0, "iris_configuration", "enableShaders=true\nshaderPack=wrong.zip\n"),
        ("reject framebuffer drift", 1, "framebuffer_resolution", [2560, 1440]),
        ("reject cap drift", 0, "frame_limit", 260),
        ("reject camera-pose drift", 1, "actual_camera_position", [-191.5, 65.8, 320.5]),
        ("reject fallback", 1, "shader_fallback", True),
        ("reject missing completion cleanup", 2, "fixture_cleanup_complete", False),
    ]
    for name, index, key, value in mutations:
        data = copy.deepcopy(base)
        data[index][key] = value
        try:
            validate_metadata(run_id, *data)
        except ValueError:
            tests.append(name)
        else:
            raise AssertionError(name)
    raw = bounded(directory / "coast-day.png", REPORT.PNG_MAX_BYTES)
    try:
        REPORT.check_png_bytes(raw[:-1], tuple(SIZE))
    except ValueError:
        tests.append("reject truncated real PNG")
    else:
        raise AssertionError("truncated PNG accepted")
    records = list(csv.DictReader(io.StringIO(bounded(directory / "coast-day.csv", 4 * 1024 * 1024).decode())))
    records[0]["ns"] = "1.5"
    try:
        raw_metrics(records)
    except ValueError:
        tests.append("reject noninteger raw nanoseconds")
    else:
        raise AssertionError("noninteger ns accepted")
    return {"passed": True, "count": len(tests), "behaviors": tests}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="Test public acceptance/rejection behavior; no writes")
    parser.add_argument("--write", action="store_true", help="Generate only the adjacent smoke/profile JSON evidence")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2))
        return
    smoke = audit_three()
    smoke["schema"] = 1
    smoke["observed_utc"] = datetime.now(timezone.utc).isoformat()
    smoke["cpu_behavior_tests"] = self_test()
    prior = read_json(HERE / "smoke-audit.json") if (HERE / "smoke-audit.json").exists() else {}
    if "tdd" in prior:
        smoke["tdd"] = prior["tdd"]
        smoke["tdd"]["interpretation"] = "Software-auditor scaffolding only; not shader RED, capture failure or a rendering fix."
    profile = saved_shore_profile()
    smoke["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    smoke["report_helper_sha256"] = hashlib.sha256((REPO / "tools/report.py").read_bytes()).hexdigest()
    smoke["anvil_helper_sha256"] = hashlib.sha256((REPO / "tools/audit-fixture-air.py").read_bytes()).hexdigest()
    smoke["saved_profile_passed"] = profile["passed"]
    if args.write:
        for name, value in (("smoke-audit.json", smoke), ("saved-shore-profile.json", profile)):
            (HERE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps({"passed": True, "captures": 3, "behavior_tests": smoke["cpu_behavior_tests"]["count"],
                          "wet_columns": profile["shape_bounds"]["exposed_contiguous_wet_columns"],
                          "written": ["smoke-audit.json", "saved-shore-profile.json"]}))
    else:
        print(json.dumps({"smoke": smoke, "saved_profile": profile}, indent=2, allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Keep missing-file/OS errors from exposing private save paths. All
        # planned validation failures are already concise non-private messages.
        print(json.dumps({"passed": False, "error_class": type(error).__name__,
                          "reason": str(error) if isinstance(error, ValueError) else "bounded audit boundary failed"}))
        raise SystemExit(1)
