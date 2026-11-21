"""Compare the same bark, grass and background after a survival player changes the mounted torch."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

# Fractions of the common HUD-free 1280x720 saved image, away from hand, flame, crosshair and inventory.
regions={
    "oakBarkAboveFlame":(.455,.135,.538,.225),
    "oakBarkBesideFlame":(.430,.44,.458,.59),
    "grassBelowCanopy":(.194,.856,.265,.902),
    "birchInBackground":(.259,.409,.309,.479),
    "skyBehindTree":(.743,.399,.782,.445),
}
def measure(path,rect):
    rgb=np.asarray(Image.open(path).convert("RGB"))
    h,w=rgb.shape[:2]
    x0,y0,x1,y1=[round(f*(w if i%2==0 else h)) for i,f in enumerate(rect)]
    a=rgb[y0:y1,x0:x1].astype(np.float64)/255
    lin=np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
    lum=lin@np.array([.2126,.7152,.0722])
    return {"displayYMedian":round(float(np.median(lum)),5),"medianRGB8":np.rint(np.median(255*a,axis=(0,1))).astype(int).tolist(),
            "xyxy":[x0,y0,x1,y1]}
def run(root):
    actions=json.loads((root/"actions.json").read_text())
    poses=json.loads((root/"positions.json").read_text())
    measurements={}
    for action in actions:
        if action.get("before")!=[5,-59,-9] or action.get("removed")!=[6,-59,-9] or action.get("restored")!=action.get("before"):continue
        phase=action["phase"]
        removed=next(o for o in reversed(poses) if o["label"]=="trunk-after-torch-removal" and o["seconds"]<=action["seconds"])
        restored=next(o for o in reversed(poses) if o["label"]=="torch-replaced" and o["seconds"]<=action["seconds"])
        assert removed["angle"]==restored["angle"] and removed["xyz"]==restored["xyz"]
        matrices={}
        for name,rect in regions.items():
            m={state:measure(root/f"{phase}-oak-torch-{state}.jpg",rect) for state in ("on","off","restored")}
            off=m["off"]["displayYMedian"]
            m["onToOffRatio"]=round(m["on"]["displayYMedian"]/off,2) if off else None
            m["restoredToOffRatio"]=round(m["restored"]["displayYMedian"]/off,2) if off else None
            matrices[name]=m
        measurements[phase]={"eyeFeet":restored["xyz"],"rotation":restored["angle"],"regions":matrices}
    doc={"method":"Actual survival actions. Identical camera verified at removal and restoration. SDR sRGB is linearized before median luminance. Exposure, moving leaves/rain and naturally advancing time remain in the displayed pixels. The distant birch and sky give background comparison areas.","phases":measurements}
    (root/"torch-pixels.json").write_text(json.dumps(doc,indent=2)+"\n")
    for phase,trial in measurements.items():print(phase,[(r,v["onToOffRatio"],v["restoredToOffRatio"]) for r,v in trial["regions"].items()])
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("run",type=Path);run(p.parse_args().run)
