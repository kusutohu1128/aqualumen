"""Verify the newly placed soil in a survival save and extend its predecessor once."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-11-22-ceiling-return"))
from save_checkpoint import preserve, load_gz
sys.path.insert(0, str(HERE.parent / "2026-11-23-torch-density"))
from playtime import extend


def record_save(record):
    previous = HERE.parent / "2026-11-23-placed-penumbra/playtime.json"
    ledger = json.loads(previous.read_text())
    run = json.loads((record / "complete.json").read_text())
    assert run["labFilesUnchanged"] and run["modsUnchanged"] and "RTX 3080 Ti" in str(run["renderer"])
    assert run["revisit"]["sourceRun"] == "torch-birch-walk" and not (record / "frozen-sky.json").exists()
    assert run["results"]["placedSoil"] == [583, 64, 423] and run["results"]["torchStillPresent"] == [584, 64, 424]
    world = Path(json.loads((record / "identity.json").read_text())["world"])
    rules = load_gz(world / "level.dat")["Data"]["GameRules"]
    assert all(rules[name] == "true" for name in ("doDaylightCycle", "doWeatherCycle"))
    rows = ledger["chains"]
    extend(rows, record, 308060, "9d2d40e8ea3e70dcc5709b21288bfe0e35c313cf112f755356c3c433452144e1",
           "soil-step-at-the-lit-birch")
    preserve(record, "Aqualumen-Birch-Soil-Step", {
        (583, 64, 423): "minecraft:dirt", (583, 64, 424): "minecraft:birch_log",
        (584, 64, 424): "minecraft:torch", (599, 72, 425): "minecraft:wall_torch",
        (600, 71, 427): "minecraft:soul_lantern"})
    ticks = sum(row["lastTick"] - row["firstTick"] for row in rows)
    ledger.update(ticks=ticks, gameDays=ticks / 24000, walkedMetres=round(sum(row["walkedMetres"] for row in rows), 2))
    (HERE / "playtime.json").write_text(json.dumps(ledger, indent=2) + "\n")
    print(ticks, ledger["gameDays"], ledger["walkedMetres"])


if __name__ == "__main__":
    record_save(HERE.parent / "2026-11-21-animal-light/woodland" / sys.argv[1])
