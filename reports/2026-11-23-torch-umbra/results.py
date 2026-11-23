"""Pair private Minecraft captures, timestamps and displayed birch pixels."""

from hashlib import sha256
import json
import sys

import numpy as np
from PIL import Image
from candidate import HERE, ROOT, BASE, build

DENSITY = HERE.parent / "2026-11-23-torch-density"
sys.path.insert(0, str(DENSITY))
from birch_pixels import REGIONS


def read(path):
    return json.loads(path.read_text())


def record(arm, pack, timestamps):
    folder = DENSITY / ("gp-density-umbra-" + arm)
    receipt = read(folder / "complete.json")
    pre = read(folder / "preflight.json")
    summary = read(folder / "summary.json")
    assert receipt["complete"] and receipt["originalWorldAndConfigUnchanged"] and not receipt["failure"]
    assert receipt["stages"] == ["birch-4"] and receipt["size"] == [2560, 1440]
    assert pre["labBefore"] == pre["labAfter"] and not pre["foreignObservations"]
    assert summary["packSha"] == receipt["packSha256"] == sha256(pack.read_bytes()).hexdigest()
    assert "RTX 3080 Ti" in summary["renderer"]["renderer"]
    w = summary["scenes"]["birch-4"]
    assert ("gpu" in w) == timestamps
    source = folder / "birch-4-ingame.png"
    assert sha256(source.read_bytes()).hexdigest() == w["capture"]
    with Image.open(source) as frame:
        assert frame.size == tuple(receipt["size"])
        crops = {k: np.asarray(frame.crop(box).convert("RGB"), dtype=int) for k, box in REGIONS.items()}
    stats = dict(
        source=str(folder.relative_to(ROOT)),
        pack=summary["packSha"],
        capture=w["capture"],
        frames=w["frames"],
        renderer=summary["renderer"]["renderer"],
        frameIntervalMeanMs=w["cpuMeanMs"],
        frameIntervalP99Ms=w["cpuP99Ms"],
    )
    if timestamps:
        stats["gpuFrameP95Ms"] = w["gpu"]["ranges"]["frame"]["p95Ms"]
        stats["gpuMeanMs"] = {
            k: w["meanMs"][k] for k in ("frame", "terrain/cutout", "terrain/solid", "main/entities")
        }
    return stats, crops


def pair(order, timestamps):
    runs, photos = {}, {}
    packs = {"pilot": build(), "reference": BASE}
    for label in order:
        arm = label if timestamps else label + "-intervals"
        runs[label], photos[label] = record(arm, packs[label], timestamps)
    for file in ("birch-world.json", "geometry.json", "observer.json"):
        assert read(ROOT / runs["reference"]["source"] / file) == read(ROOT / runs["pilot"]["source"] / file)
    display = {}
    for region, rect in REGIONS.items():
        change = abs(photos["pilot"][region] - photos["reference"][region]).max(axis=2)
        display[region] = dict(
            rect=rect, pixels=int(change.size), exact=int((change == 0).sum()),
            maxRGBChange=int(change.max()), p99RGBChange=float(np.quantile(change, 0.99)),
        )
    return dict(order=order, gpuTimestamps=timestamps, runs=runs, registeredDisplay=display)


def main():
    result = dict(scene="birch-4", size=[2560, 1440], chunks=12, **pair(["pilot", "reference"], True))
    result["withoutTimestamps"] = pair(["reference", "pilot"], False)
    (HERE / "timings.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
