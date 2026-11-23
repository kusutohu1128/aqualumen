"""Extend the accepted survival timelines without counting retries from the same save."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREVIOUS = HERE.parent / "2026-11-22-ceiling-return/playtime.json"
VILLAGE = HERE.parent / "2026-11-22-ceiling-return/village"
OAK = HERE.parent / "2026-11-21-animal-light/woodland"
CAVE = HERE.parent / "2026-11-22-forest-cave"
P7 = "c6f3c4a6a002cc1c0635c1b14a5ed3f92bed0d8937613ef1a01d448685bc967c"
P8 = "2989e6b5582935417bc5aa80f0e9e1c4f12a595b520f1c87f76c8f17a7fafe72"


def extend(rows, directory, seed, sha, activity):
    record = json.loads((directory / "complete.json").read_text())
    ident = json.loads((directory / "identity.json").read_text())
    assert ident["seed"] == seed and record["packSha256"] == sha
    assert record["cleanExit"] and record["previousSaveUnchanged"] and record["worldZipUnchanged"]
    assert not record["logErrors"] and not record["benchmarkSentinelPresent"]
    assert activity in record["results"]["completed"] and not record["results"].get("failed")
    assert record["savedLevel"]["GameType"] == record["savedLevel"]["allowCommands"] == 0
    start, end = record["revisit"]["sourceSavedTime"], record["savedLevel"]["Time"]
    previous = [row for row in rows if row["seed"] == seed]
    assert start == (previous[-1]["lastTick"] if previous else 3800) and end > start
    rows.append(dict(seed=seed, firstTick=start, lastTick=end, walkedMetres=record["walkedAfterReloadMetres"],
                     receipt=str((directory / "complete.json").relative_to(ROOT))))


def main():
    previous = json.loads(PREVIOUS.read_text())
    rows = [dict(row, receipt=str((PREVIOUS.parent / row["receipt"]).resolve().relative_to(ROOT))) for row in previous["chains"]]
    extend(rows, VILLAGE / "lamp-road", 20261139, P7, "porch-to-road-and-back")
    extend(rows, OAK / "after-dusk-oak", 308060, P8, "return-to-saved-oak")
    extend(rows, OAK / "two-flames-oak-r2", 308060, P8, "separate-placed-and-held-light")
    extend(rows, CAVE / "evening-alcove", 20261123, P8, "natural-cave")
    extend(rows, OAK / "oak-night-trail", 308060, "a5f2507b0c6cc6dd05630b4c01f9dbf3fc5a1f52ba58aa7213aed17085ab5bc9", "oak-to-raised-path")
    ticks = sum(row["lastTick"] - row["firstTick"] for row in rows)
    data = dict(chains=rows, ticks=ticks, seeds=sorted({r["seed"] for r in rows}), gameDays=ticks/24000,
                walkedMetres=round(sum(row["walkedMetres"] for row in rows), 2),
                basis="Elapsed survival save time on these continuous routes, including observation and startup. "
                      "The cave starter begins at tick 3800. Fixed-camera, failed and duplicate branches are excluded.")
    (HERE / "playtime.json").write_text(json.dumps(data, indent=2)+"\n")
    print(ticks, data["gameDays"], data["walkedMetres"])


if __name__ == "__main__":
    main()
