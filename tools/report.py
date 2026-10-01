"""Summarize a completed Minecraft capture and independently recompute its CSV metrics."""
import argparse
import csv
import json
import math
from pathlib import Path

BUDGET = 1000.0 / 60.0
FIXTURE_WORLD = "AqualumenNaturalV2"
FIXTURE_WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d"
OPAQUE_SCENARIOS = {f"opaque-{distance}-{variant}": (distance, not variant.startswith("open-"), variant.removeprefix("open-"))
                    for distance in ("near", "far")
                    for variant in ("magenta", "lime", "open-magenta", "open-lime")}
EYE_TOLERANCE_M = .05


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
    distance, wall_present, color = OPAQUE_SCENARIOS[scenario]
    z = -367 if distance == "near" else -239
    fixture = row.get("opaque_fixture")
    if not isinstance(fixture, dict) or row.get("workload") != "opaque-occlusion-test":
        raise ValueError(f"Missing opaque fixture metadata in {scenario}")
    if fixture.get("range") != distance or fixture.get("wall_present") is not wall_present or fixture.get("background_color") != color:
        raise ValueError(f"Wrong opaque fixture variant in {scenario}")
    for key, expected in (("wall_bounds", [444, 157, z, 452, 165, z]),
                          ("target_bounds", [445, 158, z + 6, 451, 164, z + 6])):
        bounds = fixture.get(key)
        if (not isinstance(bounds, list) or len(bounds) != 6 or
                any(type(part) is not int for part in bounds) or bounds != expected):
            raise ValueError(f"Wrong opaque fixture {key} in {scenario}")
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
    if (row.get("expected_camera_rotation") != [0, 0] or
            not isinstance(rotation, list) or len(rotation) != 2 or
            any(isinstance(part, bool) or not isinstance(part, (int, float)) or not math.isfinite(part) for part in rotation)):
        raise ValueError(f"Wrong opaque fixture orientation in {scenario}")


def load_run(directory):
    run = json.loads((directory / "run.json").read_text())
    complete = json.loads((directory / "complete.json").read_text())
    if (directory / "aborted.json").exists():
        raise ValueError("Run contains an abort record")
    if complete.get("run_id") != run["run_id"] or complete.get("status") != "complete":
        raise ValueError("Incomplete run or run identity mismatch")
    if run["world_generator"] != "minecraft:noise/overworld":
        raise ValueError("This is not a natural vanilla world")
    if not run["shader_active"] or run["shader_fallback"] or run["pack_sha256"] != run["expected_pack_sha256"]:
        raise ValueError("Shader identity/active validation failed")
    fixture_scenes = [scenario for scenario in run["scenarios"] if scenario in OPAQUE_SCENARIOS]
    if fixture_scenes:
        if (run.get("world_id") != FIXTURE_WORLD_ID or
                Path(run.get("world_directory", "")).name != FIXTURE_WORLD or
                run.get("fixture_world") != {"name": FIXTURE_WORLD, "world_id": FIXTURE_WORLD_ID}):
            raise ValueError("Opaque fixture run has the wrong exact disposable world marker")
        if complete.get("fixture_cleanup_complete") is not True:
            raise ValueError("Opaque fixture cleanup was not confirmed complete")
    rows = []
    for scenario in run["scenarios"]:
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
        if scenario in OPAQUE_SCENARIOS:
            if row.get("scenario") != scenario or row.get("run_id") != run["run_id"]:
                raise ValueError(f"Opaque fixture capture identity mismatch in {scenario}")
            validate_opaque_fixture(row, scenario)
        elif row.get("workload") == "opaque-occlusion-test" or "opaque_fixture" in row:
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
