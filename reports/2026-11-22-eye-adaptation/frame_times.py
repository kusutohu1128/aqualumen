"""Recompute the preview 8 qualification from private-client receipts and render intervals."""
from datetime import datetime
import json
from pathlib import Path
import re
import sys

REPORT = Path(__file__).resolve().parent
ANIMAL = REPORT.parent / "2026-11-21-animal-light"
ROOT = REPORT.parents[1]
sys.path.insert(0, str(ANIMAL / "timing"))
from measure import extract

STAGES = ("both-west", "day-white")
PACKS = {
    7: ("dist", "c6f3c4a6a002cc1c0635c1b14a5ed3f92bed0d8937613ef1a01d448685bc967c"),
    8: ("build/eye-adaptation", "2989e6b5582935417bc5aa80f0e9e1c4f12a595b520f1c87f76c8f17a7fafe72"),
}
WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d"
LIMITS = {"meanIntervalMs": 5, "p99Ms": 10}


def read(path):
    return json.loads(path.read_text())


def progress_time(label, event):
    lines = (ANIMAL / "progress.txt").read_text().splitlines()
    stamp, = [line.split()[0] for line in lines if f" {label}: {event}" in line]
    return datetime.fromisoformat(stamp)


def read_run(version, pair):
    label = f"eye-frames-p{version}-{pair}"
    if (ANIMAL / (label + "-retry")).exists():
        label += "-retry"
    run = ANIMAL / label
    r = read(run / "complete.json")
    pre = read(run / "preflight.json")
    historical = ANIMAL / "ceiling-isolated"
    observer = read(run / "observer.json")
    expected = read(historical / "complete.json")
    assert r["complete"] and r["failure"] is None and r["label"] == label
    assert r["backend"] == "vgl" and r["stages"] == list(STAGES)
    assert (r["periodTicks"], r["settleSeconds"]) == (680, 1)
    assert r["sourceDigest"] == expected["sourceDigest"] and r["originalWorldAndConfigUnchanged"]
    assert read(run / "geometry.json") == read(historical / "geometry.json")
    assert observer == read(historical / "observer.json") and observer["worldId"] == WORLD_ID
    assert r["compilerModSha256"] == expected["compilerModSha256"]
    assert pre["runnerExit"] == 0 and not pre["foreignGpuObservations"] and not pre["competingJobsBefore"]
    assert pre["monitorSamples"] > 0
    folder, digest = PACKS[version]
    pack = ROOT / folder / f"Aqualumen-1.9.0-preview.{version}.zip"
    assert r["pack"] == pack.name and r["sourcePackShaNow"] == r["packSha256"] == digest
    log = (run / "client.log").read_text()
    assert f"Using shaderpack: {pack.name}" in log and "reverting to default" not in log.lower()
    assert r["gl"]["renderer"] == expected["gl"]["renderer"]

    launched = progress_time(label, "起動 backend=")
    confirmed = progress_time(label, "描画開始を確認")
    # FrameSample prints the wall time of the batch end and every interval since its first return.
    first_batch = re.search(r"AQ_RENDER_INTERVALS_US (\d+) ([\d ]+)", log)
    assert first_batch
    end_ms, intervals = first_batch.groups()
    first_return = int(end_ms) / 1000 - sum(map(int, intervals.split())) / 1e6
    pipeline = log.index("Creating pipeline for dimension minecraft:overworld")
    workers = re.search(r"\[([\d:]+)\] \[Render thread/INFO\]: Started [1-9]\d* worker threads", log[pipeline:])
    assert workers
    world_batch = re.search(r"AQ_RENDER_INTERVALS_US (\d+) ([\d ]+)", log[pipeline + workers.end():])
    assert world_batch
    world_return = int(world_batch[1]) / 1000
    last_interval_us = int(world_batch[2].split()[-1])
    # Verify the preceding return predates even the start of the worker log's second.
    # The next observed return is thus identifiable despite one-second log timestamps.
    assert datetime.fromtimestamp(world_return, launched.tzinfo).strftime("%H:%M:%S") == workers[1]
    assert world_return - last_interval_us / 1e6 < int(world_return) - .002
    scenes = {}
    for stage in STAGES:
        row = extract(label, stage, version, pack_path=pack)
        window = log.split(f"[Server] AQLAVA_READY_{stage}_END", 1)[1].split(f"[Server] AQLAVA_STILL_{stage}_END", 1)[0]
        name, = re.findall(r"(\d{4}-\d\d-\d\d_[\d.]+(?:_\d+)?\.png)として保存しました", window)
        assert (run / "f2" / name).read_bytes() == (run / f"{stage}-ingame.png").read_bytes()
        row["f2"] = name
        us = row["intervalsUs"]
        row["meanIntervalMs"] = sum(us) / len(us) / 1000
        row["meanFps"] = len(us) * 1e6 / sum(us)
        scenes[stage] = row
    return {
        "run": label, "pack": str(pack.relative_to(ROOT)), "sha256": digest, "gl": r["gl"],
        "sourceDigest": r["sourceDigest"], "observer": observer, "compilerSha256": r["compilerModSha256"],
        "cacheBefore": pre["cacheBefore"], "cacheAfter": pre["cacheAfter"],
        "launchedAt": launched.isoformat(), "renderConfirmedAt": confirmed.isoformat(),
        "launchToFirstObserverReturnApproxSeconds": round(first_return - launched.timestamp(), 1),
        "launchToFirstLoggedOverworldRenderApproxSeconds": round(world_return - launched.timestamp(), 1),
        "overworldWorkerLogTime": workers[1], "firstOverworldBatchEndMs": int(world_batch[1]),
        "intervalEndingAtFirstOverworldReturnUs": last_interval_us,
        "launchToSceneConfirmedSeconds": int((confirmed - launched).total_seconds()),
        "scenes": scenes,
    }


def compare(p7, p8):
    deltas = {}
    for stage in STAGES:
        before, after = p7["scenes"][stage], p8["scenes"][stage]
        values = {}
        for key in ("meanFps", *LIMITS):
            diff = after[key] - before[key]
            values[key] = {"delta": diff, "percent": 100 * diff / before[key]}
        values["crossed"] = [key for key, limit in LIMITS.items()
                             if after[key] * 100 > before[key] * (100 + limit)]
        deltas[stage] = values
    return deltas


def run_summary():
    order = [(7, "a"), (8, "a"), (8, "b"), (7, "b")]
    runs = {key: read_run(*key) for key in order}
    pairs = {p: compare(runs[7, p], runs[8, p]) for p in ("a", "b")}
    triggers = {s: sorted(set(pairs["a"][s]["crossed"]) ^ set(pairs["b"][s]["crossed"]))
                for s in STAGES}
    if any(triggers.values()):
        for v in (7, 8):
            runs[v, "c"] = read_run(v, "c")
        pairs["c"] = compare(runs[7, "c"], runs[8, "c"])
    launches = [run["launchedAt"] for run in runs.values()]
    assert launches == sorted(launches)
    return {
        "settings": {"world": "AqualumenNaturalV2", "worldId": WORLD_ID, "seed": 308060,
                     "size": [2560, 1440], "renderChunks": 12, "vsync": False, "fpsCap": 120,
                     "periodTicks": 680, "settleSeconds": 1,
                     "cache": "build/eye-adaptation/timing-glcache"},
        "measurement": "MinecraftClient.render return intervals after F2; discard 3 batches, keep the next 10 s; nearest-rank p99.",
        "startup": "Launch marker has 1 s resolution. The first observer return may be a loading frame. Overworld render uses the first render-return batch end logged after overworld pipeline creation and terrain worker startup. Scene confirmation is the runner's later stage-start marker.",
        "thresholdPercent": LIMITS, "repeatPairTriggers": triggers,
        "runs": list(runs.values()), "pairedPreview8Minus7": pairs,
    }


if __name__ == "__main__":
    data = run_summary()
    (REPORT / "frame-times.json").write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(data["pairedPreview8Minus7"], indent=2))
