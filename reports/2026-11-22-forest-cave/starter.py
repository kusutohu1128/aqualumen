"""Package only level.dat, letting the Minecraft client generate the surveyed staircase."""
import gzip
import hashlib
import io
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

here=Path(__file__).resolve().parent
root=here.parents[1]
sys.path.insert(0,str(here.parent/"2026-11-21-leaf-light/play"))
from build_world import level, HOTBAR


def main():
    route=json.loads((here/"route.json").read_text())
    x,y,z=route["endpoints"][0]
    scene=dict(seed=route["seed"],worldFolder="Aqualumen-Forest-Cave",start_daytime=3800,
               clear_weather_ticks=0,stormTicksAtStart=12000,spawn=dict(feet=[x+.5,y,z+.5],yaw=180.,pitch=8.))
    nbt=level(scene,"Aqualumen Forest Cave",HOTBAR,initial_storm_ticks=scene["stormTicksAtStart"])
    blob=io.BytesIO()
    with ZipFile(blob,"w") as pack:
        entry=ZipInfo(scene["worldFolder"]+"/level.dat",(2026,11,22,0,0,0))
        entry.external_attr=0o644<<16
        pack.writestr(entry,gzip.compress(nbt,mtime=0),compress_type=ZIP_DEFLATED)
    target=root/"build"/(scene["worldFolder"]+".zip")
    data=blob.getvalue()
    if target.exists():
        assert target.read_bytes()==data
    else:
        target.write_bytes(data)
    scene["sha256"]=hashlib.sha256(data).hexdigest()
    (here/"starter.json").write_text(json.dumps(scene,indent=2)+"\n")
    print(target,scene["sha256"])


if __name__=="__main__":
    main()
