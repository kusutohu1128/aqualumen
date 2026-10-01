"""Summarize a completed Minecraft capture and independently recompute its CSV metrics."""
import argparse
import csv
import json
import math
from pathlib import Path
import struct
import zlib

BUDGET = 1000.0 / 60.0
FIXTURE_WORLD = "AqualumenNaturalV2"
FIXTURE_WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d"
OPAQUE_SCENARIOS = {f"opaque-{distance}-{variant}": (distance, not variant.startswith("open-"), variant.removeprefix("open-"))
                    for distance in ("near", "far")
                    for variant in ("magenta", "lime", "open-magenta", "open-lime")}
AIR_SHADOW_SCENARIOS = {"air-shadow-backlit": (True,11000), "air-sunlit-front": (True,1000), "air-backlit-open": (False,11000)}
FIXTURE_SCENARIOS = set(OPAQUE_SCENARIOS) | set(AIR_SHADOW_SCENARIOS)
EYE_TOLERANCE_M = .05
PNG_MAX_BYTES = 16 * 1024 * 1024
PNG_MAX_SIZE = (2560, 1440)


def check_png_bytes(raw, expected_size):
    """Validate bounded Minecraft RGB/RGBA screenshot bytes without modifying them."""
    if (not isinstance(expected_size, (tuple, list)) or len(expected_size) != 2 or
            any(type(value) is not int or not 1 <= value <= bound
                for value, bound in zip(expected_size, PNG_MAX_SIZE))):
        raise ValueError("Invalid bounded PNG dimensions")
    if len(raw) > PNG_MAX_BYTES or raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid PNG signature or encoded size")
    offset, chunks, ended_idat, seen_iend, seen_palette = 8, 0, False, False, False
    image_data = []
    while offset < len(raw):
        if len(raw) - offset < 12:
            raise ValueError("Truncated PNG chunk")
        length = struct.unpack_from(">I", raw, offset)[0]
        kind = raw[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(raw):
            raise ValueError("Truncated PNG chunk payload")
        data = raw[offset + 8:offset + 8 + length]
        crc = struct.unpack_from(">I", raw, offset + 8 + length)[0]
        if (any(not (65 <= letter <= 90 or 97 <= letter <= 122) for letter in kind) or
                not 65 <= kind[2] <= 90 or zlib.crc32(kind + data) != crc):
            raise ValueError("Invalid PNG chunk type or CRC")
        if chunks == 0:
            if kind != b"IHDR" or length != 13:
                raise ValueError("PNG must start with one 13-byte IHDR")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", data)
            if ((width, height) != tuple(expected_size) or depth != 8 or color not in (2, 6) or
                    compression != 0 or filtering != 0 or interlace != 0):
                raise ValueError("Unsupported PNG dimensions or pixel format")
        elif kind == b"IHDR":
            raise ValueError("Duplicate PNG IHDR")
        elif kind == b"IDAT":
            if ended_idat:
                raise ValueError("PNG IDAT chunks must be consecutive")
            image_data.append(data)
        elif kind == b"IEND":
            if length != 0 or not image_data or end != len(raw):
                raise ValueError("Invalid PNG IEND, missing IDAT or trailing bytes")
            seen_iend = True
        else:
            if image_data:
                ended_idat = True
            if kind == b"PLTE":
                if image_data or seen_palette or not 0 < length <= 768 or length % 3:
                    raise ValueError("Invalid PNG palette order or size")
                seen_palette = True
            elif not kind[0] & 32:
                raise ValueError("Unsupported critical PNG chunk")
        offset, chunks = end, chunks + 1
    if not seen_iend:
        raise ValueError("Incomplete PNG: missing IEND")
    stride = 1 + width * (3 if color == 2 else 4)
    expected_bytes = height * stride
    decoder = zlib.decompressobj()
    try:
        scanlines = decoder.decompress(b"".join(image_data), expected_bytes + 1)
    except zlib.error as error:
        raise ValueError("Corrupt PNG zlib stream") from error
    if (len(scanlines) != expected_bytes or not decoder.eof or decoder.unused_data or
            decoder.unconsumed_tail):
        raise ValueError("PNG zlib stream is incomplete, oversized or has trailing data")
    if any(scanlines[offset] > 4 for offset in range(0, expected_bytes, stride)):
        raise ValueError("Invalid PNG scanline filter")


def check_png(path, expected_size):
    """Read at most 16 MiB + 1 and reject incomplete visual-review evidence."""
    try:
        with path.open("rb") as stream:
            raw = stream.read(PNG_MAX_BYTES + 1)
        check_png_bytes(raw, expected_size)
    except (OSError, ValueError) as error:
        raise ValueError(f"Invalid screenshot {path.name}: {error}") from error


def metrics(values):
    ordered = sorted(values)
    slow_count = max(1, math.ceil(len(values) * .01))
    return {"frames": len(values), "mean_fps": 1000 * len(values) / sum(values),
            "one_percent_low_fps": 1000 * slow_count / sum(ordered[-slow_count:]),
            "p99_ms": ordered[math.ceil(len(values) * .99) - 1], "max_ms": max(values),
            "min_instantaneous_fps": 1000 / max(values),
            "frames_over_16_667_ms": sum(value > BUDGET for value in values)}


def vector(value, scenario, label):
    if (not isinstance(value, list) or len(value) != 3 or
            any(isinstance(part, bool) or not isinstance(part, (int, float)) or not math.isfinite(part) for part in value)):
        raise ValueError(f"Invalid {label} in {scenario}")
    return value


def validate_opaque_fixture(row, scenario):
    air_shadow = scenario in AIR_SHADOW_SCENARIOS
    if air_shadow:
        wall_present, requested_time = AIR_SHADOW_SCENARIOS[scenario]
        distance, color, rotation_expected = "west-air", "magenta", [90,0]
        bounds_expected = (("wall_bounds", [432,157,-387,432,165,-379]), ("target_bounds", [426,158,-386,426,164,-380]))
    else:
        distance, wall_present, color = OPAQUE_SCENARIOS[scenario]
        z = -367 if distance == "near" else -239
        rotation_expected = [0,0]
        bounds_expected = (("wall_bounds", [444,157,z,452,165,z]), ("target_bounds", [445,158,z+6,451,164,z+6]))
    fixture = row.get("opaque_fixture")
    if not isinstance(fixture, dict) or row.get("workload") != ("air-sun-shadow-test" if air_shadow else "opaque-occlusion-test"):
        raise ValueError(f"Missing opaque fixture metadata in {scenario}")
    if fixture.get("range") != distance or fixture.get("wall_present") is not wall_present or fixture.get("background_color") != color:
        raise ValueError(f"Wrong opaque fixture variant in {scenario}")
    for key, expected in bounds_expected:
        bounds = fixture.get(key)
        if (not isinstance(bounds, list) or len(bounds) != 6 or
                any(type(part) is not int for part in bounds) or bounds != expected):
            raise ValueError(f"Wrong opaque fixture {key} in {scenario}")
    if air_shadow:
        required = {"wall_plane_axis": "x", "wall_material": "minecraft:white_concrete", "target_material": "minecraft:magenta_concrete",
                    "fixed_lights": [[426,164,-386],[426,164,-380]], "reserved_air_cells": 130,
                    "placed_cells": 130 if wall_present else 49, "requested_player_position": [448.5,160,-383.5],
                    "requested_camera_rotation": rotation_expected}
        for key, expected in required.items():
            if fixture.get(key) != expected:
                raise ValueError(f"Wrong air-shadow fixture {key} in {scenario}")
        for key in ("requested_world_time", "actual_world_time", "actual_server_world_time"):
            if type(fixture.get(key)) is not int or fixture[key] != requested_time:
                raise ValueError(f"Wrong air-shadow sun/time control in {scenario}: {key}")
    if fixture.get("camera_eye_match") is not True or fixture.get("camera_first_person") is not True:
        raise ValueError(f"Missing first-person eye validation in {scenario}")
    tolerance = fixture.get("eye_tolerance_m")
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or tolerance != EYE_TOLERANCE_M:
        raise ValueError(f"Wrong camera eye tolerance in {scenario}")
    eye = vector(fixture.get("actual_eye_position"), scenario, "fixture eye position")
    camera = vector(fixture.get("actual_camera_position"), scenario, "fixture camera position")
    top_eye = vector(row.get("actual_eye_position"), scenario, "measured eye position")
    top_camera = vector(row.get("actual_camera_position"), scenario, "measured camera position")
    player = vector(row.get("actual_player_position"), scenario, "measured player position")
    if eye != top_eye or camera != top_camera or math.dist(eye, camera) > EYE_TOLERANCE_M:
        raise ValueError(f"Rendered camera is not at the measured player eye in {scenario}")
    if (math.dist(player, [448.5, 160, -383.5]) > EYE_TOLERANCE_M or
            math.hypot(eye[0] - player[0], eye[2] - player[2]) > EYE_TOLERANCE_M or
            not 0 < eye[1] - player[1] <= 3):
        raise ValueError(f"Wrong opaque fixture player/eye position in {scenario}")
    rotation = row.get("actual_camera_rotation")
    if (row.get("expected_camera_rotation") != rotation_expected or
            not isinstance(rotation, list) or len(rotation) != 2 or
            any(isinstance(part, bool) or not isinstance(part, (int, float)) or not math.isfinite(part) for part in rotation)):
        raise ValueError(f"Wrong opaque fixture orientation in {scenario}")
    if any(abs(actual - expected) > .05 for actual,expected in zip(rotation,rotation_expected)):
        raise ValueError(f"Rendered fixture orientation is incorrect in {scenario}")


def load_run(directory):
    run = json.loads((directory / "run.json").read_text())
    complete = json.loads((directory / "complete.json").read_text())
    if run.get("expected_resolution") != list(PNG_MAX_SIZE):
        raise ValueError("Expected screenshot resolution must be exactly 2560x1440")
    if (directory / "aborted.json").exists():
        raise ValueError("Run contains an abort record")
    if complete.get("run_id") != run["run_id"] or complete.get("status") != "complete":
        raise ValueError("Incomplete run or run identity mismatch")
    if run["world_generator"] != "minecraft:noise/overworld":
        raise ValueError("This is not a natural vanilla world")
    if not run["shader_active"] or run["shader_fallback"] or run["pack_sha256"] != run["expected_pack_sha256"]:
        raise ValueError("Shader identity/active validation failed")
    fixture_scenes = [scenario for scenario in run["scenarios"] if scenario in FIXTURE_SCENARIOS]
    if fixture_scenes:
        if (run.get("world_id") != FIXTURE_WORLD_ID or
                Path(run.get("world_directory", "")).name != FIXTURE_WORLD or
                run.get("fixture_world") != {"name": FIXTURE_WORLD, "world_id": FIXTURE_WORLD_ID}):
            raise ValueError("Opaque fixture run has the wrong exact disposable world marker")
        if complete.get("fixture_cleanup_complete") is not True:
            raise ValueError("Opaque fixture cleanup was not confirmed complete")
    rows = []
    for scenario in run["scenarios"]:
        check_png(directory / f"{scenario}.png", run["expected_resolution"])
        row = json.loads((directory / f"{scenario}.json").read_text())
        with (directory / f"{scenario}.csv").open(newline="") as stream:
            values = [float(record["ms"]) for record in csv.DictReader(stream)]
        if len(values) < 10 or any(not math.isfinite(value) or value <= 0 for value in values):
            raise ValueError(f"Invalid frame intervals in {scenario}")
        computed = metrics(values)
        for key, value in computed.items():
            if abs(row[key] - value) > max(0.001, abs(value) * .00001):
                raise ValueError(f"Metric mismatch in {scenario}: {key}")
        if row["resolution"] != run["expected_resolution"] or row["framebuffer_resolution"] != run["expected_resolution"]:
            raise ValueError(f"Resolution mismatch in {scenario}")
        if row["pack_sha256"] != run["pack_sha256"] or row["world_id"] != run["world_id"] or not row["shader_active"] or row["shader_fallback"]:
            raise ValueError(f"Shader or world changed in {scenario}")
        if row["sample_seconds_actual"] < run["sample_seconds"] - .1:
            raise ValueError(f"Truncated sample in {scenario}")
        expected_dimension = "minecraft:the_nether" if scenario == "nether-view" else "minecraft:the_end" if scenario == "end-view" else "minecraft:overworld"
        if row["player_dimension"] != expected_dimension:
            raise ValueError(f"Wrong dimension in {scenario}")
        if not row.get("camera_lock") or not row.get("camera_follows_local_player"):
            raise ValueError(f"Missing rendered-camera validation in {scenario}")
        rendered, expected = row["actual_camera_rotation"], row["expected_camera_rotation"]
        if abs(rendered[1] - expected[1]) > .05 or (scenario != "moving-view" and abs(rendered[0] - expected[0]) > .05):
            raise ValueError(f"Camera did not render the requested scene in {scenario}")
        if scenario == "boat-contact" and (not row["physics_active_seen"] or row["maximum_contacts"] < 1 or row["maximum_force"] <= 0):
            raise ValueError("No measured moving boat disturbance reached the physics bridge")
        if scenario in FIXTURE_SCENARIOS:
            if row.get("scenario") != scenario or row.get("run_id") != run["run_id"]:
                raise ValueError(f"Opaque fixture capture identity mismatch in {scenario}")
            validate_opaque_fixture(row, scenario)
        elif row.get("workload") in ("opaque-occlusion-test", "air-sun-shadow-test") or "opaque_fixture" in row:
            raise ValueError(f"Unexpected opaque fixture metadata in {scenario}")
        rows.append(row)
    return run, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="Run directory containing run.json, complete.json and raw CSVs")
    parser.add_argument("--output", type=Path, help="Optional report destination; defaults to run/RESULTS.md")
    args = parser.parse_args()
    run, rows = load_run(args.run)
    limit = str(run["frame_limit"])
    text = ["# Minecraft natural-world image validation and frame measurements", "",
            f"Renderer: {run['gl_renderer']}; driver/GL: {run['gl_version']}.",
            f"Minecraft {run['minecraft']}; Java {run['java']}; installed mods: " + ", ".join(f"{key} {value}" for key, value in run['mods'].items()) + ".",
            "Garbage collectors: " + ", ".join(run.get("garbage_collectors", ["not recorded"])) + (f"; initial heap {run['jvm_heap_initial_bytes'] / 1048576:.0f} MiB; maximum heap {run['jvm_heap_max_bytes'] / 1048576:.0f} MiB." if "jvm_heap_max_bytes" in run else "."),
            f"Runtime cloud settings: Iris pipeline {run.get('iris_pipeline_cloud_setting', 'not recorded')}; effective Minecraft mode {run.get('minecraft_effective_cloud_mode', 'not recorded')}.",
            f"Window and framebuffer: {run['expected_resolution'][0]}×{run['expected_resolution'][1]}; render distance {run['render_chunks']}; simulation distance {run['simulation_chunks']}; VSync {run['vsync']}; frame-limit setting {limit}.",
            f"Pack: `{run['pack_name']}`; SHA-256 `{run['pack_sha256']}`; active without Iris fallback.",
            f"Natural vanilla noise world; seed {run['seed']}; UUID `{run['world_id']}`; local integrated server with one identified player and no LAN publication.",
            f"Requested per scene: {run['warmup_seconds']} seconds warmup + {run['sample_seconds']} seconds measurement. Render-loop wall-clock intervals include CPU work, rendering, frame pacing and any chunk work. Screenshots and file serialization occur outside the timed interval.", "",
            "Camera orientation is locked after input before world rendering; the actual rendered Camera angles and local-player identity are validated for every capture. Fixed-scene player coordinates are also checked.",
            "The accompanying scene PNGs are the visual-review evidence. Frame timings do not score appearance or physical correctness; 16.667 ms is a reference budget, not a quality acceptance threshold.", "",
            "| Scene | Workload | Frames | Mean FPS | 1% low FPS | P99 ms | Worst ms | Frames >16.67 ms |",
            "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in rows:
        text.append(f"| {row['scenario']} | {row['workload']} | {row['frames']} | {row['mean_fps']:.1f} | {row['one_percent_low_fps']:.1f} | {row['p99_ms']:.2f} | {row['max_ms']:.2f} | {row['frames_over_16_667_ms']} |")
    warmed = [row for row in rows if row["workload"] == "warmed-view"]
    boats = [row for row in rows if row["workload"] == "scripted-boat-contact"]
    traversal = [row for row in rows if row["workload"] == "chunk-traversal"]
    opaque = [row for row in rows if row["workload"] == "opaque-occlusion-test"]
    air_shadow = [row for row in rows if row["workload"] == "air-sun-shadow-test"]
    text += ["", "The 1% low is 1000 divided by the mean of the slowest 1% of intervals; it is not an absolute FPS minimum.",
             "An observed 60 FPS floor requires every measured interval to fit the 16.667 ms budget. A P99 pass allows up to 1% slower frames.", ""]
    if warmed:
        text.append(f"Warmed render views ({len(warmed)} scenes): P99 ≤16.667 ms in every scene: {all(row['p99_ms'] <= BUDGET for row in warmed)}; every measured frame ≤16.667 ms: {all(row['max_ms'] <= BUDGET for row in warmed)}.")
    else:
        text.append("Warmed render views: not measured in this run.")
    if opaque:
        text.append(f"Opaque-occlusion fixtures ({len(opaque)} scenes): exact disposable world, fixture geometry and measured first-person camera eye validated; cleanup confirmed. P99 ≤16.667 ms in every scene: {all(row['p99_ms'] <= BUDGET for row in opaque)}; every measured frame ≤16.667 ms: {all(row['max_ms'] <= BUDGET for row in opaque)}.")
        text.append("These temporary walls and colored targets are artificial test fixtures, not natural-world scenery. The open variants are positive visibility controls; closed variants share white-wall geometry and lighting while changing the hidden background color.")
        if run.get("visual_validation_limits"):
            text.append("Recorded visual-validation limits: " + str(run["visual_validation_limits"]))
        text.append("Sequential captures include changing cloud animation and exposure; color pairs are not pixel-exact proof of a depth/leak fix. Review open controls for visible targets and closed walls for occlusion; the separate opaque-pixel/cloud-radiance rendering regression is the causal test.")
    if air_shadow:
        text.append(f"West-facing air-shadow fixtures ({len(air_shadow)} scenes): exact approved receiver/target planes, first-person eye and frozen client/server sun times validated; cleanup confirmed.")
        text.append("These artificial WHITE concrete receivers occupy X432/Y157..165/Z-387..-379; magenta targets occupy X426/Y158..164/Z-386..-380, with identical sea-lantern upper corners. Camera/player is (448.5,160,-383.5), yaw90/pitch0. The 11000 backlit and 1000 front-lit sun angles are approximately opposed controls, not an exact matched-exposure radiometric experiment.")
        for row in air_shadow:
            fixture = row["opaque_fixture"]
            text.append(f"{row['scenario']}: white receiver present={fixture['wall_present']}; requested/client/server time={fixture['requested_world_time']}/{fixture['actual_world_time']}/{fixture['actual_server_world_time']}; {fixture['placed_cells']} placed cells in {fixture['reserved_air_cells']} prechecked AIR cells.")
        text.append("Review directional illumination and shadowing, with the open variant confirming the target is visible. A receiver may be partially sunlit; indirect sky illumination and atmospheric fog remain valid on shaded faces. Do not require the entire image, fog or shadow to be black. Animated clouds and exposure evolution also forbid a pixel-exact sequential-difference causal claim.")
        if run.get("visual_validation_limits"):
            text.append("Recorded visual-validation limits: " + str(run["visual_validation_limits"]))
    if boats:
        text.append(f"Scripted boat contact ({len(boats)} scene): P99 ≤16.667 ms: {all(row['p99_ms'] <= BUDGET for row in boats)}; every measured frame ≤16.667 ms: {all(row['max_ms'] <= BUDGET for row in boats)}; total over-budget frames: {sum(row['frames_over_16_667_ms'] for row in boats)}.")
    if traversal:
        text.append(f"Chunk traversal ({len(traversal)} scene): P99 ≤16.667 ms in every scene: {all(row['p99_ms'] <= BUDGET for row in traversal)}; every measured frame ≤16.667 ms: {all(row['max_ms'] <= BUDGET for row in traversal)}.")
        text.append("Traversal uses spectator teleports at 32 m/s and 20 Hz, so the measured workload includes scripted command/network correction overhead as well as chunk work; it is not a manual walking/flight benchmark.")
    for row in rows:
        if row["scenario"] == "boat-contact":
            text.append(f"Boat-contact bridge was active during measurement: {row['physics_active_seen']}; maximum simultaneous contacts {row['maximum_contacts']}; maximum force {row['maximum_force']:.3f}. The boat follows a scripted 6 m/s path; this validates contact input rather than player-controlled vanilla rowing.")
    text += ["", "These are observed results for the recorded configuration, seed, coordinates and durations. They do not guarantee a 60 FPS floor across arbitrary worlds, new chunk generation, mods or background loads. Traversal deliberately visits terrain outside the warmed camera position; it is reported separately from warmed views.", ""]
    output = args.output or args.run / "RESULTS.md"
    output.write_text("\n".join(text), encoding="utf-8")
    print("\n".join(text))


if __name__ == "__main__":
    main()
