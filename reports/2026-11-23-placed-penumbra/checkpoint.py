"""Continue the three verified clocks only after reading the placed torch from the save."""
import json
import sys
from pathlib import Path
from pack import HERE, ROOT
sys.path.insert(0,str(HERE.parent/"2026-11-22-ceiling-return"))
from save_checkpoint import preserve,load_gz
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
from playtime import extend

def main():
    record=HERE.parent/"2026-11-21-animal-light/woodland"/sys.argv[1]
    run=json.loads((record/"complete.json").read_text())
    assert run["labFilesUnchanged"] and run["modsUnchanged"] and "RTX 3080 Ti" in str(run["renderer"])
    assert run["revisit"]["sourceRun"]=="stone-torch-niche" and not (record/"frozen-sky.json").exists()
    assert run["results"]["placedTorch"]==[584,64,424] and run["results"]["birch"]==[583,64,424]
    world=Path(json.loads((record/"identity.json").read_text())["world"])
    data=load_gz(world/"level.dat")["Data"]
    assert all(data["GameRules"][k]=="true" for k in ("doDaylightCycle","doWeatherCycle"))
    led=json.loads((HERE.parent/"2026-11-23-torch-open-volume/playtime.json").read_text())
    rows=led["chains"]
    extend(rows,record,308060,"b224ea6f9424ad7dd8424f2c192e1708f97f734a802870cea42ebb722dcb4c02","place-a-torch-beside-the-birch")
    preserve(record,"Aqualumen-Birch-Torch-Walk",{(584,64,424):"minecraft:torch",(583,64,424):"minecraft:birch_log",
               (599,72,425):"minecraft:wall_torch",(600,71,427):"minecraft:soul_lantern"})
    ticks=sum(r["lastTick"]-r["firstTick"] for r in rows)
    led.update(ticks=ticks,gameDays=ticks/24000,walkedMetres=round(sum(r["walkedMetres"] for r in rows),2))
    (HERE/"playtime.json").write_text(json.dumps(led,indent=2)+"\n")
    print(led["gameDays"],rows[-1])
if __name__=="__main__": main()
