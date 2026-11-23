"""Verify the continuous snowy-village route, then preserve the measured save."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "2026-11-22-ceiling-return"
sys.path.insert(0, str(SOURCE))
from save_checkpoint import preserve, load_gz, Region, block_at
sys.path.insert(0, str(HERE.parent / "2026-11-23-torch-density"))
from playtime import extend

PACK = "e84240aba58a5905312c75b553a529f566dda0bf0a53f4769f731e50e634aa57"


def verify(step, label):
    fitting = step == "fit"
    folder = SOURCE / "village" / label
    old = HERE / "forage-playtime.json" if fitting else HERE.parent / "2026-11-23-torch-cell-shadow/playtime.json"
    ledger = json.loads(old.read_text())
    rows = ledger["chains"]
    extend(rows, folder, 20261139, PACK, "craft-and-fit-the-red-window" if fitting else "bring-a-poppy-home")
    world = Path(json.loads((folder / "identity.json").read_text())["world"])
    level = load_gz(world / "level.dat")["Data"]
    assert all(level["GameRules"][r] == "true" for r in ("doDaylightCycle", "doWeatherCycle"))
    player = load_gz(next((world / "playerdata").glob("*.dat")))
    items = {i["id"].removeprefix("minecraft:"): i["count"] for i in player["Inventory"]}
    assert items["spruce_planks"] == (11 if fitting else 15)
    if fitting:
        assert items["red_stained_glass"] == 2 and items["red_stained_glass_pane"] == 15
        assert all(i not in items for i in ("glass", "red_dye", "poppy"))
    else:
        assert items["glass"] == 8 and items["poppy"] == 1
    expected = {(-896,71,508): "air", (-901,71,576): "red_stained_glass_pane" if fitting else "air",
                (-903,71,577): "crafting_table" if fitting else "air", (-902,71,579): "spruce_planks",
                (-902,70,578): "soul_torch", (-902,73,578): "lantern",
                (-904,70,575): "lantern", (-900,70,575): "lantern"}
    preserve(folder, "Aqualumen-Red-Window" if fitting else "Aqualumen-Village-Poppy",
             {p: "minecraft:" + b for p, b in expected.items()})
    if fitting:
        x,y,z=-901,71,576
        region=Region(world/"region"/f"r.{x//512}.{z//512}.mca")
        pane=block_at(region.chunk(x//16,z//16),x,y,z)
        assert pane["Properties"]["east"]=="true" and pane["Properties"]["waterlogged"]=="false"
        window=dict(position=[x,y,z],block=pane,remainingPanes=items["red_stained_glass_pane"],
                    remainingGlassBlocks=items["red_stained_glass"],time=level["Time"],
                    inventoryAndSave=str((folder/"save.json").relative_to(HERE.parents[1])))
        (HERE/"window.json").write_text(json.dumps(window,indent=2)+"\n")
    ticks = sum(r["lastTick"] - r["firstTick"] for r in rows)
    out = HERE / ("playtime.json" if fitting else "forage-playtime.json")
    out.write_text(json.dumps(dict(chains=rows, ticks=ticks, seeds=ledger["seeds"], gameDays=ticks/24000,
                                   walkedMetres=round(sum(r["walkedMetres"] for r in rows), 2),
                                   basis=ledger["basis"]), indent=2) + "\n")
    print(out.name, ticks, rows[-1]["walkedMetres"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=("forage", "fit"))
    parser.add_argument("label")
    args = parser.parse_args()
    verify(args.step, args.label)
