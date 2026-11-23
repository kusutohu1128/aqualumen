"""Publish the continued survival save after verifying the two new permanent lights and the previous shore."""

import json
from pathlib import Path
import sys

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent / "2026-11-22-ceiling-return"))
from save_checkpoint import preserve

sys.path.insert(0, str(here.parent / "2026-11-23-torch-density"))
from playtime import extend

source = here.parent / "2026-11-21-animal-light/woodland/lakeside-to-meadow"
receipt = json.loads((source / "complete.json").read_text())
assert receipt["labFilesUnchanged"] and receipt["modsUnchanged"] and not receipt["results"].get("failed")
assert (
    receipt["revisit"]["sourceRun"] == "lakeside-lanterns"
    and receipt["savedLevel"]["DayTime"] == receipt["savedLevel"]["Time"]
)
assert receipt["results"]["completed"] == ["mark-the-pasture-route", "watch-cattle-in-the-meadow"]
data = json.loads((here.parent / "2026-11-23-leaf-tiles/playtime.json").read_text())
extend(
    data["chains"],
    source,
    308060,
    "fb3026acb3535855bad31671c4fc3f1bccf50d75004960a085b6db4f1905b583",
    "mark-the-pasture-route",
)
preserve(
    source,
    "Aqualumen-Meadow-Trail",
    {
        p: "minecraft:" + m
        for p, m in {
            (560, 64, 385): "lantern",
            (587, 64, 362): "soul_lantern",
            (541, 62, 394): "water",
            (541, 63, 395): "soul_lantern",
            (556, 63, 420): "lantern",
            (571, 65, 420): "lantern",
        }.items()
    },
)
data.update(
    ticks=sum(row["lastTick"] - row["firstTick"] for row in data["chains"]),
    walkedMetres=round(sum(row["walkedMetres"] for row in data["chains"]), 2),
)
data["gameDays"] = data["ticks"] / 24000.0
(here / "playtime.json").write_text(json.dumps(data, indent=2) + "\n")
print(data["ticks"], data["gameDays"], data["walkedMetres"])
