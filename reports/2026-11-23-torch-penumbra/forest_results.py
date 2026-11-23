"""Read the unchanged 1440p test world and record display differences for both study arms."""
import argparse
from hashlib import sha256
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from pack import HERE
DENSITY=HERE.parent/"2026-11-23-torch-density"
sys.path.insert(0,str(DENSITY))
from birch_pixels import REGIONS


def read(p):
    return json.loads(p.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hand-run", default="penumbra-hand-birch-4-r2")
    args = parser.parse_args()
    folders={"preview12":DENSITY/"gp-density-umbra-pilot-intervals",
             "allSources":HERE/"penumbra-birch-4","hand":HERE/args.hand_run}
    control=folders["preview12"]
    packages=read(HERE.parent/"2026-11-23-torch-umbra/package.json")
    assert packages["allUncompressedEntriesIdenticalToTrial"]
    assert read(control/"complete.json")["packSha256"]==packages["testedHash"]
    result={}
    old=None
    for name,folder in folders.items():
        r=read(folder/"complete.json")
        pre=read(folder/"preflight.json")
        assert r["complete"] and r["originalWorldAndConfigUnchanged"] and not r["failure"]
        assert r["shaderpackLogged"] and r["stages"]==["birch-4"]
        assert r["packSha256"]==r["sourcePackShaNow"] and r["size"]==[2560,1440]
        assert "RTX 3080 Ti" in r["gl"]["renderer"]
        assert pre["labBefore"]==pre["labAfter"] and not pre["foreignObservations"]
        for key in ("geometry","birch-world","observer"):
            assert read(control/(key+".json"))==read(folder/(key+".json"))
        path=folder/"birch-4-ingame.png"
        assert sha256(path.read_bytes()).hexdigest()==r["screenshots"]["birch-4"]["ingame"]
        with Image.open(path) as im:
            pic=np.asarray(im.convert("RGB")).astype(np.int16)
        if old is None: old=pic
        changes={}
        for key,(x,y,right,bottom) in REGIONS.items():
            d=abs(old[y:bottom,x:right]-pic[y:bottom,x:right]).max(2)
            changes[key]={"pixels":int(d.size),"maxRGB":int(d.max()),"p99RGB":float(np.quantile(d,.99)),"unchanged":int((d==0).sum())}
        timing=read(folder/"summary.json")["scenes"]["birch-4"]
        result[name]={"run":folder.name,"pack":r["packSha256"],"renderer":r["gl"]["renderer"],"frameIntervalMs":timing["cpuMeanMs"],
                      "p99FrameIntervalMs":timing["cpuP99Ms"],"frames":timing["frames"],"registeredRegions":changes}
    (HERE/"forest.json").write_text(json.dumps(result,indent=2)+"\n")
    for name,arm in result.items():print(name,arm["frameIntervalMs"],arm["registeredRegions"])


if __name__=="__main__":
    main()
