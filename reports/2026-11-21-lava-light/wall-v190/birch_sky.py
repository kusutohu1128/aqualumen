"""Measure upper-hemisphere visibility from the same natural birch used for torch captures."""
import collections
import json
import math
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parents[1] / "2026-11-21-leaf-light/forest"))
from sitesearch import Scene, SNAP


def sky(scene, point, normal, polar, azimuth):
    totals = collections.Counter()
    for j in range(polar):
        y = (j + .5) / polar
        radius = math.sqrt(1 - y*y)
        for i in range(azimuth):
            phi = 2 * math.pi * ((i + .5 + (j % 2) * .5) / azimuth)
            direction = (radius*math.cos(phi), y, radius*math.sin(phi))
            weight = sum(a*b for a, b in zip(normal, direction))
            if weight <= 0:
                continue
            first = scene.trace(point, direction, 20)["kind"]
            totals["total"] += weight
            totals[first] += weight
            if first == "sky" or (first == "leaf" and scene.trace(point, direction, 20, stop_leaf=False)["kind"] == "sky"):
                totals["withoutLeaves"] += weight
    assert totals["unknown"] == 0
    return {k: round(totals[k] / totals["total"], 5) for k in ("sky", "withoutLeaves", "leaf", "log", "solid", "ground", "plant", "water")}


if __name__ == "__main__":
    scene = Scene((207, 359, 210, 361))
    assert scene.state((209, 65, 360))["Name"] == "minecraft:birch_log"
    assert scene.state((207, 63, 359))["Name"] == "minecraft:grass_block"
    samples = {
        "middleBirchBark": ((209.5, 65.5, 359.999), (0, 0, -1)),
        "grassAtTorch": ((207.5, 64.001, 359.5), (0, 1, 0)),
        "grassAtRoot": ((209.5, 64.001, 359.5), (0, 1, 0)),
    }
    answers = {}
    for name, (point, normal) in samples.items():
        coarse = sky(scene, point, normal, 32, 96)
        fine = sky(scene, point, normal, 64, 192)
        answers[name] = {"position": point, "normal": normal, "grid32x96": coarse, "grid64x192": fine}
    result = {"sourceSnapshot": SNAP["sourceDigest"], "seed": SNAP["seed"], "radiusBlocks": 20,
              "meaning": "Fraction of cosine-weighted incoming sky directions unobstructed within 20 blocks. Vanilla leaf texture alpha on first entries. Other plants modelled as solid; no multiple scattering, no Sun, no torch or radiometric calibration.",
              "samples": answers}
    with (here / "birch-release-comparison/sky-visibility.json").open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
