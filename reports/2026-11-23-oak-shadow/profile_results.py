"""Collect the exact white-birch, four-torch windows recorded by the three private packs."""
import json
from pathlib import Path

import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ARMS=(("stock","gp-density-oak-stock-b"),("box","gp-density-oak-study-a-r1"),("slabs","gp-density-oak-slabs-c-r1"))


def load(path):
    return json.loads(path.read_text())


def main():
    runs={}
    for label,folder in ARMS:
        arm=HERE/folder
        r=load(arm/"complete.json")
        pre=load(arm/"preflight.json")
        assert not r.get("failure") and r["complete"] and r["originalWorldAndConfigUnchanged"] and r["size"]==[2560,1440]
        assert not pre["foreignObservations"] and pre["labAfter"]==pre["labBefore"]
        w=load(arm/"summary.json")["scenes"]["birch-4"]
        runs[label]=dict(acquired=pre["underLock"]["at"],source=str(arm.relative_to(ROOT)),pack=r["packSha256"],renderer=r["gl"]["renderer"],
                         frames=w["frames"],frameIntervalMeanMs=w["cpuMeanMs"],frameIntervalP99Ms=w["cpuP99Ms"],
                         gpuMeanMs={key:w["meanMs"][key] for key in ("frame","terrain/solid","terrain/cutout","terrain/translucent")},
                         gpuP95Ms=w["gpu"]["ranges"]["frame"]["p95Ms"],capture=w["capture"])
    roi=load(HERE.parent/"2026-11-23-torch-density/birch-highlight.json")["bark"]
    left,top,right,bottom=roi
    def trunk(arm):
        path=ROOT/runs[arm]["source"]/"birch-4-ingame.png"
        with Image.open(path) as img:
            return np.asarray(img.convert("RGB").crop((left,top,right,bottom)),dtype=int)
    base=trunk("stock")
    display={}
    for arm in ("box","slabs"):
        diff=abs(base-trunk(arm)).max(axis=2)
        display[arm]=dict(equalPixels=int((diff==0).sum()),pixels=int(diff.size),
                          p99MaxChannelChange=float(np.quantile(diff,.99)),maxChange=int(diff.max()))
    report=dict(birchBarkRectangle=roi,birchBarkDisplayDifference=display,scene="birch-4, four placed torches, 2560x1440, 12 chunks, private fixed scene, GPU timestamps enabled",
                order=sorted(runs,key=lambda k:runs[k]["acquired"]),runs=runs,
                note="A single instrumented ten-second window per arm. The CPU interval includes waiting for the GPU and VirtualGL transport.")
    (HERE/"profile.json").write_text(json.dumps(report,indent=2)+"\n")
    print({k:(v["gpuMeanMs"]["frame"],v["frameIntervalMeanMs"]) for k,v in runs.items()})


if __name__=="__main__":
    main()
