"""Archive the naturally timed niche outing after reading its actual saved blocks."""
import json
from pathlib import Path
import sys
from pack import HERE,ROOT
sys.path.insert(0,str(HERE.parent/"2026-11-22-ceiling-return"))
from save_checkpoint import preserve, load_gz
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
from playtime import extend


def main():
    wood=HERE.parent/"2026-11-21-animal-light/woodland"
    record=wood/sys.argv[1]
    run=json.loads((record/"complete.json").read_text())
    assert run["cleanExit"] and run["labFilesUnchanged"] and run["modsUnchanged"]
    assert run["revisit"]["sourceRun"]=="lake-to-stone-camp" and not (record/"frozen-sky.json").exists()
    assert run["results"]["mountedTorch"]==[599,72,425]
    world=Path(json.loads((record/"identity.json").read_text())["world"])
    data=load_gz(world/"level.dat")["Data"]
    assert data["GameRules"]["doDaylightCycle"]=="true" and data["GameRules"]["doWeatherCycle"]=="true"
    baseline=json.loads((wood/"lake-to-stone-camp/save.json").read_text())
    assert baseline["sha256"]=="9626bf40a74a9b8cd559b59179fe885467e927311e7d894226fd3f6a77a9f348"
    previous=json.loads((HERE.parent/"2026-11-23-wet-receiver/playtime.json").read_text())
    rows=previous["chains"]
    sha="18e666ae93ada4daf0a31fb822c23e82dd2240bf581018d11c08a54f476fe385"
    extend(rows,record,308060,sha,"cut-and-light-a-stone-niche")
    blocks={(599,72,425):"minecraft:wall_torch",(599,72,424):"minecraft:stone",(600,71,427):"minecraft:soul_lantern",
            (542,64,395):"minecraft:torch",(541,63,395):"minecraft:soul_lantern"}
    preserve(record,"Aqualumen-Torch-Niche",blocks)
    ticks=sum(r["lastTick"]-r["firstTick"] for r in rows)
    previous.update(ticks=ticks,gameDays=ticks/24000,walkedMetres=round(sum(r["walkedMetres"] for r in rows),2))
    (HERE/"playtime.json").write_text(json.dumps(previous,indent=2)+"\n")
    print(rows[-1],previous["gameDays"])

if __name__=="__main__":
    main()
