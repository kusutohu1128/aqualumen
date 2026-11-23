"""Read the two standing torches from the final physical save and extend its timeline once."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-22-ceiling-return"))
from save_checkpoint import preserve,load_gz
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
from playtime import extend

if __name__=="__main__":
    run=HERE.parent/"2026-11-21-animal-light/woodland"/sys.argv[1]
    record=json.loads((run/"complete.json").read_text())
    assert record["labFilesUnchanged"] and record["modsUnchanged"] and "RTX 3080 Ti" in record["renderer"]
    assert record["revisit"]["sourceRun"]=="soil-step-and-torch" and not (run/"frozen-sky.json").exists()
    assert record["results"]["raisedSoulTorch"]==[583,65,423] and record["results"]["warmTorch"]==[584,64,424]
    world=Path(json.loads((run/"identity.json").read_text())["world"])
    rules=load_gz(world/"level.dat")["Data"]["GameRules"]
    assert all(rules[k]=="true" for k in ("doDaylightCycle","doWeatherCycle"))
    ledger=json.loads((HERE.parent/"2026-11-23-mixed-occluders/playtime.json").read_text())
    previous=json.loads((run.parent/"soil-step-and-torch/save.json").read_text())
    extend(ledger["chains"],run,308060,"0ba3e7673ceef7d0f60529457e550e259006fe293b15390bcd3d38eebf500b2a","soul-torch-on-the-soil-step")
    assert previous["verifiedBlocks"]["583,64,423"]=="minecraft:dirt"
    preserve(run,"Aqualumen-Birch-Two-Lights",{(583,64,423):"minecraft:grass_block",(583,65,423):"minecraft:soul_torch",
             (584,64,424):"minecraft:torch",(583,64,424):"minecraft:birch_log",(599,72,425):"minecraft:wall_torch",
             (600,71,427):"minecraft:soul_lantern"})
    now=json.loads((run/"save.json").read_text())
    assert previous["inventory"]["2"][1]-now["inventory"]["2"][1]==1
    ticks=sum(r["lastTick"]-r["firstTick"] for r in ledger["chains"])
    ledger.update(ticks=ticks,gameDays=ticks/24000.,walkedMetres=round(sum(r["walkedMetres"] for r in ledger["chains"]),2))
    ledger["newSession"]=dict(elapsedWorldTicks=record["savedLevel"]["Time"]-record["revisit"]["sourceSavedTime"],
        afterJoinPipelineSeconds=record["pipelineSecondsAfterJoin"],controlWindowSeconds=record["seconds"],
        walkedMetres=record["walkedAfterReloadMetres"],groundBefore=previous["verifiedBlocks"]["583,64,423"],
        groundAfter=now["verifiedBlocks"]["583,64,423"])
    (HERE/"playtime.json").write_text(json.dumps(ledger,indent=2)+"\n")
