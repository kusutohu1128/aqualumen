"""Measure saved screen output on the stone and the static emitting part of the wall torch."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
WOOD = HERE.parent / "2026-11-21-animal-light/woodland"
# Coordinates apply to the 1600x900 camera centred on the wall torch after the climb.
REGIONS = {"torchCore": [796,375,811,387], "animatedFlame": [789,314,806,352],
           "nicheBack": [861,348,972,450], "leftWall": [290,420,650,565],
           "rightWall": [1120,400,1430,520], "ceiling": [240,110,530,180]}

def measure(path):
    with Image.open(path) as image:
        rgb=np.asarray(image.convert("RGB"))
    assert rgb.shape == (900,1600,3)
    output={}
    for key,(x0,y0,x1,y1) in REGIONS.items():
        pix=rgb[y0:y1,x0:x1].reshape(-1,3)
        srgb=pix/255.
        linear=np.where(srgb<=.04045,srgb/12.92,((srgb+.055)/1.055)**2.4)
        y=linear@np.array([.2126,.7152,.0722])
        p10,med,p90=np.quantile(y,[.1,.5,.9])
        output[key] = dict(n=len(y),displayLuminanceMedian=round(float(med),5),
             contrastP90ToP10=round(float(p90/p10),4) if p10>0 else None,
             medianRgb=np.median(pix,axis=0).tolist(),anyChannel255=int(np.any(pix==255,axis=1).sum()))
    return output

if __name__=="__main__":
    if len(sys.argv)==1:
        run=WOOD/"row-scan-camp-walk"
        files=[run/(s+"-ingame.png") for s in ("niche-empty-hand","niche-held-torch")]
        out=HERE/"niche-pixels.json"
    else:
        run=WOOD/sys.argv[1]
        files=sorted(run.glob("sample-*-ingame.png"))
        assert len(files)==9
        out=HERE/"niche-repeat-pixels.json"
    result=dict(regions=REGIONS,frames={f.name:measure(f) for f in files})
    out.write_text(json.dumps(result,indent=2)+"\n")
