"""Archive the private survival result and append only its uninterrupted ticks."""
from pathlib import Path
import json
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-22-ceiling-return"))
from save_checkpoint import preserve
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
from playtime import extend

if __name__=="__main__":
    source=HERE.parent/"2026-11-21-animal-light/woodland/oak-opening"
    original=HERE.parent/"2026-11-23-torch-density/playtime.json"
    activity="cut-oak-and-build-lantern-post"
    record=json.loads((source/"complete.json").read_text())
    assert record["labFilesUnchanged"] and record["modsUnchanged"] and activity in record["results"]["completed"]
    blocks={(561,63,422):"torch",(565,64,425):"soul_torch",(566,64,419):"torch",(568,64,418):"air",
            (568,65,418):"oak_log",(571,64,420):"oak_log",(571,65,420):"lantern"}
    preserve(source,"Aqualumen-Oak-Lantern-Post",{k:"minecraft:"+v for k,v in blocks.items()})
    data=json.loads(original.read_text())
    extend(data["chains"],source,308060,"a5f2507b0c6cc6dd05630b4c01f9dbf3fc5a1f52ba58aa7213aed17085ab5bc9",activity)
    data["ticks"]=sum(r["lastTick"]-r["firstTick"] for r in data["chains"])
    data["gameDays"]=data["ticks"]/24000
    data["walkedMetres"]=round(sum(r["walkedMetres"] for r in data["chains"]),2)
    (HERE/"playtime.json").write_text(json.dumps(data,indent=2)+"\n")
    print(data["gameDays"],data["walkedMetres"])
