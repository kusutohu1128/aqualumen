"""Check the relocated torch in the saved region and extend the existing survival timeline."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
WOOD=HERE.parent/"2026-11-21-animal-light/woodland"
sys.path.insert(0,str(HERE.parent/"2026-11-22-ceiling-return"))
from save_checkpoint import preserve, load_gz
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
from playtime import extend

def read(path):
    return json.loads(path.read_text())

def save(run):
    previous=read(WOOD/"stone-display-wider-camp/save.json")
    record=read(run/"complete.json")
    assert record["results"]["removedTorch"]==[584,64,424]
    assert record["results"]["newTorch"]==[582,64,423]
    assert record["modsUnchanged"] and record["labFilesUnchanged"]
    world=Path(read(run/"identity.json")["world"])
    rules=load_gz(world/"level.dat")["Data"]["GameRules"]
    assert rules["doDaylightCycle"]==rules["doWeatherCycle"]=="true"
    expected={tuple(map(int,k.split(","))):m for k,m in previous["verifiedBlocks"].items()}
    expected.update({(584,64,424):"minecraft:air",(582,64,423):"minecraft:torch",
                     (583,64,424):"minecraft:birch_log"})
    ledger=read(HERE.parent/"2026-11-23-stone-display/playtime.json")
    interrupted=WOOD/"cell-shadow-birch-relocation"
    first=read(interrupted/"complete.json")
    partial=read(interrupted/"save.json")
    assert record["revisit"]["sourceRun"]=="cell-shadow-birch-relocation"
    assert partial["verifiedBlocks"]["584,64,424"]==partial["verifiedBlocks"]["582,64,423"]=="minecraft:air"
    assert first["revisit"]["sourceRun"]=="stone-display-wider-camp"
    assert first["revisit"]["sourceSavedTime"]==previous["time"]
    assert first["savedLevel"]["Time"]==partial["time"]==record["revisit"]["sourceSavedTime"]
    assert partial["seed"]==308060 and first["packSha256"]==record["packSha256"]
    assert first["worldZipUnchanged"] and first["previousSaveUnchanged"] and first["labFilesUnchanged"]
    assert first["cleanExit"] and not first["logErrors"] and not first["benchmarkSentinelPresent"]
    assert first["savedLevel"]["allowCommands"]==partial["gameType"]==0
    assert (interrupted/"birch-east-extinguished-ingame.png").is_file()
    rows=ledger["chains"]
    assert [r for r in rows if r["seed"]==308060][-1]["lastTick"]==previous["time"]
    rows.append(dict(seed=308060,firstTick=previous["time"],lastTick=partial["time"],
                     walkedMetres=first["walkedAfterReloadMetres"],receipt=str((interrupted/"complete.json").relative_to(HERE.parents[1])),
                     activity="Walk down from camp and remove the east torch; west placement resumed from these saved bytes."))
    extend(ledger["chains"],run,308060,"14e849c5b54ee04db05c75216a75764e865d553b711e67b180ed328c6afb7db0",
           "finish-the-birch-torch-relocation")
    preserve(run,"Aqualumen-Relit-Birch",expected)
    ticks=sum(r["lastTick"]-r["firstTick"] for r in ledger["chains"])
    ledger.update(ticks=ticks,gameDays=ticks/24000,walkedMetres=round(sum(r["walkedMetres"] for r in ledger["chains"]),2))
    ledger["newSession"]=dict(elapsedWorldTicks=record["savedLevel"]["Time"]-record["revisit"]["sourceSavedTime"],
                             afterJoinPipelineSeconds=record["pipelineSecondsAfterJoin"],controlWindowSeconds=record["seconds"],
                             walkedMetres=record["walkedAfterReloadMetres"],displayedFps=record["displayedFps"])
    ledger["firstLeg"]=dict(elapsedWorldTicks=partial["time"]-previous["time"],afterJoinPipelineSeconds=first["pipelineSecondsAfterJoin"],
                            controlWindowSeconds=first["seconds"],walkedMetres=first["walkedAfterReloadMetres"])
    (HERE/"playtime.json").write_text(json.dumps(ledger,indent=2)+"\n")
if __name__=="__main__":
    save(WOOD/sys.argv[1])
