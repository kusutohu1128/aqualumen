"""Summarize a completed Minecraft capture and independently recompute its CSV metrics."""
import argparse
import csv
import json
import math
from pathlib import Path

BUDGET = 1000.0 / 60.0


def metrics(values):
    ordered = sorted(values)
    slow_count = max(1, math.ceil(len(values) * .01))
    return {"frames": len(values), "mean_fps": 1000 * len(values) / sum(values),
            "one_percent_low_fps": 1000 * slow_count / sum(ordered[-slow_count:]),
            "p99_ms": ordered[math.ceil(len(values) * .99) - 1], "max_ms": max(values),
            "min_instantaneous_fps": 1000 / max(values),
            "frames_over_16_667_ms": sum(value > BUDGET for value in values)}


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
        rows.append(row)
    return run, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="Run directory containing run.json, complete.json and raw CSVs")
    parser.add_argument("--output", type=Path, help="Optional report destination; defaults to run/RESULTS.md")
    args = parser.parse_args()
    run, rows = load_run(args.run)
    limit = str(run["frame_limit"]) + (" (Minecraft's unlimited selector)" if isinstance(run["frame_limit"], int) and run["frame_limit"] >= 260 else "")
    text = ["# Minecraft natural-world frame measurements", "",
            f"Renderer: {run['gl_renderer']}; driver/GL: {run['gl_version']}.",
            f"Minecraft {run['minecraft']}; Java {run['java']}; installed mods: " + ", ".join(f"{key} {value}" for key, value in run['mods'].items()) + ".",
            "Garbage collectors: " + ", ".join(run.get("garbage_collectors", ["not recorded"])) + (f"; initial heap {run['jvm_heap_initial_bytes'] / 1048576:.0f} MiB; maximum heap {run['jvm_heap_max_bytes'] / 1048576:.0f} MiB." if "jvm_heap_max_bytes" in run else "."),
            f"Runtime cloud settings: Iris pipeline {run.get('iris_pipeline_cloud_setting', 'not recorded')}; effective Minecraft mode {run.get('minecraft_effective_cloud_mode', 'not recorded')}.",
            f"Window and framebuffer: {run['expected_resolution'][0]}×{run['expected_resolution'][1]}; render distance {run['render_chunks']}; simulation distance {run['simulation_chunks']}; VSync {run['vsync']}; frame-limit setting {limit}.",
            f"Pack: `{run['pack_name']}`; SHA-256 `{run['pack_sha256']}`; active without Iris fallback.",
            f"Natural vanilla noise world; seed {run['seed']}; UUID `{run['world_id']}`; local integrated server with one identified player and no LAN publication.",
            f"Requested per scene: {run['warmup_seconds']} seconds warmup + {run['sample_seconds']} seconds measurement. Render-loop wall-clock intervals include CPU work, rendering, frame pacing and any chunk work. Screenshots and file serialization occur outside the timed interval.", "",
            "Camera orientation is locked after input before world rendering; the actual rendered Camera angles and local-player identity are validated for every capture. Fixed-scene player coordinates are also checked.", "",
            "| Scene | Workload | Frames | Mean FPS | 1% low FPS | P99 ms | Worst ms | Frames >16.67 ms |",
            "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in rows:
        text.append(f"| {row['scenario']} | {row['workload']} | {row['frames']} | {row['mean_fps']:.1f} | {row['one_percent_low_fps']:.1f} | {row['p99_ms']:.2f} | {row['max_ms']:.2f} | {row['frames_over_16_667_ms']} |")
    warmed = [row for row in rows if row["workload"] == "warmed-view"]
    boats = [row for row in rows if row["workload"] == "scripted-boat-contact"]
    traversal = [row for row in rows if row["workload"] == "chunk-traversal"]
    text += ["", "The 1% low is 1000 divided by the mean of the slowest 1% of intervals; it is not an absolute FPS minimum.",
             "An observed 60 FPS floor requires every measured interval to fit the 16.667 ms budget. A P99 pass allows up to 1% slower frames.", "",
             f"Warmed render views ({len(warmed)} scenes): P99 ≤16.667 ms in every scene: {all(row['p99_ms'] <= BUDGET for row in warmed)}; every measured frame ≤16.667 ms: {all(row['max_ms'] <= BUDGET for row in warmed)}."]
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
