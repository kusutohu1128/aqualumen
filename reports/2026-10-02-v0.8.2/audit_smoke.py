"""Read-only audit of the pinned three-scene 0.8.2 Minecraft checkpoint."""
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from tools.report import check_png_bytes, metrics

RUN = "v082-cloud-local-smoke-20261002-1503"
PACK = "6f555c5b8fbb30531d2638cd69997f2969ed18bff1695165e3fc6622007199e5"
WORLD = "b22dbccb-2970-41e6-847f-f183b1ec923d"
SCENES = ["coast-day", "river-day", "ocean-day"]

def require(condition, message):
    if not condition:
        raise ValueError(message)

def read(path):
    require(path.is_file() and not path.is_symlink(), "Missing/redirected evidence")
    before = path.stat()
    with path.open("rb") as stream:
        raw = stream.read(16 * 1024 * 1024 + 1)
    after = path.stat()
    require(len(raw) <= 16 * 1024 * 1024 and
            (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
            "Evidence changed or exceeded bound")
    return raw

def identity(row):
    require(row["run_id"] == RUN and row["world_id"] == WORLD and
            row["pack_name"] == "Aqualumen-0.8.2.zip" and row["pack_sha256"] == PACK,
            "Run/world/pack mismatch")
    require(row["shader_active"] is True and row["shader_fallback"] is False and
            row["resolution"] == row["framebuffer_resolution"] == [1600, 900] and
            row["player_dimension"] == "minecraft:overworld", "Runtime identity mismatch")

def audit():
    directory = ROOT / "captures" / RUN
    run = json.loads(read(directory / "run.json"))
    identity(run)
    complete = json.loads(read(directory / "complete.json"))
    require(complete["run_id"] == RUN and complete["status"] == "complete" and
            complete["scenarios"] == run["scenarios"] == SCENES and
            complete["fixture_cleanup_complete"] is True, "Incomplete run")
    require(run["seed"] == 308060 and run["gl_renderer"].startswith("NVIDIA GeForce RTX 3080 Ti") and
            run["mods"]["aqualumen_physics"] == "0.3.0" and
            run["mods"]["aqualumen_benchmark"] == "0.3.7" and
            run["frame_limit"] == 120 and run["warmup_seconds"] == 20 and
            run["sample_seconds"] == 5 and run["vsync"] is False, "Workload/mod identity mismatch")
    storage = run["iris_render_target_storage"]
    require(storage["available"] is True and storage["bindingRestored"] is True,
            "Iris storage observation unavailable")
    for index in (6, 7):
        matches = [q for q in storage["queries"] if q["index"] == index]
        require(len(matches) == 1, "Missing/duplicate LUT allocation")
        q = matches[0]
        require(q["declaredFormat"] == "RGBA16F", "Unexpected LUT format")
        for side in ("main", "alt"):
            require(q[side]["actualFormat"] == 34842 and q[side]["width"] == 1024 and
                    q[side]["height"] == 512, "Actual LUT allocation mismatch")
    captures = []
    for name in SCENES:
        row = json.loads(read(directory / (name + ".json")))
        identity(row)
        require(row["scenario"] == name and row["window_focused"] is True and
                row["camera_follows_local_player"] is True and
                row["actual_camera_rotation"] == row["expected_camera_rotation"] and
                row["physics_active_seen"] is True and row["warmup_seconds"] == 20 and
                row["sample_seconds_requested"] == 5, "Capture/focus/camera mismatch")
        png = read(directory / (name + ".png"))
        check_png_bytes(png, [1600, 900])
        raw_csv = read(directory / (name + ".csv"))
        rows = list(csv.DictReader(raw_csv.decode().splitlines()))
        require(len(rows) == row["frames"] and len(rows) > 10, "Frame count mismatch")
        ns = []
        for i, frame in enumerate(rows):
            require(set(frame) == {"frame", "ms", "ns"} and frame["frame"] == str(i) and
                    frame["ns"].isdigit() and int(frame["ns"]) > 0, "Invalid raw integer interval")
            n = int(frame["ns"])
            require(math.isclose(float(frame["ms"]), n * 1e-6, rel_tol=0, abs_tol=1e-9), "ns/ms mismatch")
            ns.append(n)
        recalculated = metrics([n * 1e-6 for n in ns])
        for key, value in recalculated.items():
            require(type(row[key]) in (int, float) and math.isfinite(row[key]) and
                    math.isclose(row[key], value, rel_tol=1e-9, abs_tol=1e-9), "Metric mismatch: " + key)
        require(math.isclose(sum(ns) * 1e-9, row["recorded_seconds"], rel_tol=0, abs_tol=1e-10),
                "Recorded duration mismatch")
        captures.append({"scene": name, **recalculated, "total_ns": sum(ns),
                         "png_sha256": hashlib.sha256(png).hexdigest(),
                         "csv_sha256": hashlib.sha256(raw_csv).hexdigest()})
    return {"schema": 1, "smoke_evidence_pass": True, "run": RUN, "pack_sha256": PACK,
            "captures": captures, "total_intervals": sum(c["frames"] for c in captures),
            "total_ns": sum(c["total_ns"] for c in captures),
            "C6_C7_actual_allocations_match": True,
            "named_C7_sampler_binding_or_cache_pixel_readback_proven": False,
            "acceptance": "Three short warmed1600x900 views only; not1440p, FPS floor, fixed-phase A/B, motion or natural-appearance acceptance"}

if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, ensure_ascii=False))
