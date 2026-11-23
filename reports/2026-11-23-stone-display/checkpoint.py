"""Preserve the excavation and advance the same survival timeline exactly once."""
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

if __name__=="__main__":
    run=WOOD/"stone-display-wider-camp"
    original=read(WOOD/"row-scan-camp-walk/save.json")
    rec=read(run/"complete.json")
    assert rec["results"]["openedStone"]==[598,72,425] and rec["labFilesUnchanged"] and rec["modsUnchanged"]
    world=Path(read(run/"identity.json")["world"])
    rules=load_gz(world/"level.dat")["Data"]["GameRules"]
    assert rules["doDaylightCycle"]==rules["doWeatherCycle"]=="true"
    expected={tuple(map(int,k.split(","))):m for k,m in original["verifiedBlocks"].items()}
    expected.update({(598,72,425):"minecraft:air",(598,72,424):"minecraft:stone"})
    preserve(run,"Aqualumen-Widened-Torch-Niche",expected)
    ledger=read(HERE.parent/"2026-11-23-torch-brick-scan/playtime.json")
    extend(ledger["chains"],run,308060,"98dc4b848a7d461d0a4ad1045e565edb97c739f3c40661fffc95df5bd574b53d","widen-the-torch-niche")
    ticks=sum(row["lastTick"]-row["firstTick"] for row in ledger["chains"])
    ledger.update(ticks=ticks,gameDays=ticks/24000,walkedMetres=round(sum(row["walkedMetres"] for row in ledger["chains"]),2))
    ledger["newSession"]=dict(elapsedWorldTicks=rec["savedLevel"]["Time"]-rec["revisit"]["sourceSavedTime"],
        afterJoinPipelineSeconds=rec["pipelineSecondsAfterJoin"],controlWindowSeconds=rec["seconds"],
        walkedMetres=rec["walkedAfterReloadMetres"],displayedFps=rec["displayedFps"])
    (HERE/"playtime.json").write_text(json.dumps(ledger,indent=2)+"\n")
