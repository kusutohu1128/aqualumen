"""Decode the normal displayed pixels and the adjacent raw diagnostic rows."""
import json
from pathlib import Path

import numpy as np
from PIL import Image

here=Path(__file__).resolve().parent
run=here/"display-readback"
done=json.loads((run/"complete.json").read_text())
plan=json.loads((run/"plan.json").read_text())
data={}
for row in plan["roles"]:
    with Image.open(run/(row["name"]+".png")) as shot:
        pixels=np.array(shot.convert("RGB"),dtype=np.float64)
    patches={}
    for s in row["samples"]:
        x,y,x1,y1=s["patch"]
        crop=pixels[y:y1,x:x1,:]
        rows=(pixels.shape[0]-1-np.arange(y,y1))%4
        displayed=crop[rows==0].mean(axis=(0,1))
        opaque,scene,local=np.square(crop[rows==1]/255.0).mean(axis=(0,1))
        exposure,translucent,emissive=(crop[rows==2]/255.0).mean(axis=(0,1))
        hdr=np.square(crop[rows==3]/255.0).mean(axis=(0,1))
        patches[s["name"]]=dict(displayRGB8=displayed.round(3).tolist(),opaqueY=round(opaque,6),sceneY=round(scene,6),
            localY=round(local,6),exposure=round(exposure*4.0,4),nearerLayer=round(translucent,4),emitter=round(emissive,4),
            sceneLinearRGB=hdr.round(5).tolist())
    data[row["name"]]=patches
with (here/"display-stage-results.json").open("x") as out:
    json.dump(dict(sha256=done["sha256"],renderer=done["renderer"],measurement="Interleaved rows. Production passes unmodified up to the final shader. HDR decoded per pixel.",roles=data),out,indent=2)
for n,patches in data.items():
    print(n,patches["soul"])
