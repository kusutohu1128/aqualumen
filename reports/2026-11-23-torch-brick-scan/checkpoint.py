"""Verify the new trail marker, both birch torches and the original lamp in the niche."""
import json
from pathlib import Path
import sys
from make_rows import HERE, PREVIOUS

sys.path.insert(0, str(HERE.parent / "2026-11-22-ceiling-return"))
from save_checkpoint import preserve, load_gz
sys.path.insert(0, str(HERE.parent / "2026-11-23-torch-density"))
from playtime import extend

def load(path):
    return json.loads(path.read_text())

if __name__ == "__main__":
    run = HERE.parent / "2026-11-21-animal-light/woodland/row-scan-camp-walk"
    record = load(run / "complete.json")
    assert record["labFilesUnchanged"] and record["modsUnchanged"] and "RTX 3080 Ti" in record["renderer"]
    assert record["revisit"]["sourceRun"] == "raised-soul-torch" and not (run / "frozen-sky.json").exists()
    assert record["results"]["entranceTorch"] == [593,71,426] and record["results"]["nicheTorch"] == [599,72,425]
    world = Path(load(run / "identity.json")["world"])
    rules = load_gz(world / "level.dat")["Data"]["GameRules"]
    assert all(rules[k] == "true" for k in ("doDaylightCycle","doWeatherCycle"))
    ledger = load(PREVIOUS / "playtime.json")
    previous = load(run.parent / "raised-soul-torch/save.json")
    extend(ledger["chains"], run, 308060, "2a69fd3773f3af3548bb0247db5903c3e1d1bf199d84e24cb72a4493636381c1",
           "mark-the-return-path-to-the-stone-niche")
    expected = {tuple(map(int,k.split(","))): v for k,v in previous["verifiedBlocks"].items()}
    expected[(593,71,426)] = "minecraft:torch"
    preserve(run, "Aqualumen-Birch-Camp-Path", expected)
    saved = load(run / "save.json")
    assert previous["inventory"]["1"][1] - saved["inventory"]["1"][1] == 1
    assert saved["inventory"]["2"] == previous["inventory"]["2"]
    ticks = sum(r["lastTick"] - r["firstTick"] for r in ledger["chains"])
    ledger.update(ticks=ticks,gameDays=ticks/24000.,walkedMetres=round(sum(r["walkedMetres"] for r in ledger["chains"]),2))
    ledger["newSession"] = dict(elapsedWorldTicks=record["savedLevel"]["Time"]-record["revisit"]["sourceSavedTime"],
        afterJoinPipelineSeconds=record["pipelineSecondsAfterJoin"],controlWindowSeconds=record["seconds"],
        walkedMetres=record["walkedAfterReloadMetres"],displayedFps=record["displayedFps"])
    (HERE / "playtime.json").write_text(json.dumps(ledger,indent=2)+"\n")
