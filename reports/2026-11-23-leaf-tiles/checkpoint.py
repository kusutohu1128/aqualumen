"""Verify the shoreline changes in the actual save and advance only its canonical chain."""
from pathlib import Path
import json
import sys
from packs import HERE,ROOT
sys.path.insert(0,str(HERE.parent/"2026-11-22-ceiling-return"))
from save_checkpoint import preserve
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
from playtime import extend
from mcnbt import Region,block_at

if __name__=="__main__":
    source=HERE.parent/"2026-11-21-animal-light/woodland"/(sys.argv[1] if len(sys.argv)>1 else "lakeside-lanterns")
    result=json.loads((source/"complete.json").read_text())
    activity="light-two-shores-and-open-inlet"
    assert result["results"]["completed"]==[activity] and not result["results"].get("failed")
    assert result["revisit"]["sourceRun"]=="oak-opening"
    assert result["savedLevel"]["Time"]==result["savedLevel"]["DayTime"]>71979
    world=Path(json.loads((source/"identity.json").read_text())["world"])
    blocks={(571,65,420):"lantern",(556,63,420):"lantern",(541,63,395):"soul_lantern",
            (541,62,394):"water",(540,62,394):"water"}
    region=Region(world/"region/r.1.0.mca")
    def block(x,y,z):
        return block_at(region.chunk(x//16,z//16),x,y,z)
    inlet=block(541,62,394); original=block(540,62,394)
    assert inlet["Name"]==original["Name"]=="minecraft:water" and original["Properties"]["level"]=="0"
    preserve(source,"Aqualumen-Lakeside-Lanterns",{k:"minecraft:"+v for k,v in blocks.items()})
    data=json.loads((HERE.parent/"2026-11-23-oak-shadow/playtime.json").read_text())
    extend(data["chains"],source,308060,"a5f2507b0c6cc6dd05630b4c01f9dbf3fc5a1f52ba58aa7213aed17085ab5bc9",activity)
    data["ticks"]=sum(r["lastTick"]-r["firstTick"] for r in data["chains"])
    data["gameDays"]=data["ticks"]/24000
    data["walkedMetres"]=round(sum(r["walkedMetres"] for r in data["chains"]),2)
    (HERE/"playtime.json").write_text(json.dumps(data,indent=2)+"\n")
    (HERE/"water-entry.json").write_text(json.dumps(dict(dugCell=inlet,neighbour=original,receipt=str(source.relative_to(ROOT)/"complete.json")),indent=2)+"\n")
