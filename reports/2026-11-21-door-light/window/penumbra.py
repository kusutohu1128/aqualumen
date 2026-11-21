"""Compare displayed aperture edges with independent area integration across the lantern."""
import argparse
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
args=argparse.ArgumentParser(description=__doc__)
args.add_argument("--after", choices=("area", "coplanar"), default="area")
after=args.parse_args().after
prefix="shipped-" if after=="coplanar" else ""
run = json.loads((HERE/after/"complete.json").read_text())
base = json.loads((HERE/"projection-final/complete.json").read_text())
before = json.loads((HERE/"baseline/complete.json").read_text())
runtime = json.loads((HERE.parents[1]/"2026-11-20-underwater-refinement/local-launch.json").read_text())
with zipfile.ZipFile(next(p for p in runtime["cp"] if p.endswith("minecraft-1.21.1-client.jar"))) as z:
    pixels = np.array(Image.open(io.BytesIO(z.read("assets/minecraft/textures/block/oak_door_top.png"))).convert("RGBA"))[:,:,3]
# Connected transparent rectangles, UV in atlas top-left origin.
seen=set()
windows=[]
for v,u in zip(*np.where(pixels<26)):
    if (u,v) in seen:
        continue
    pending=[(u,v)]
    group=set()
    while pending:
        i,j=pending.pop()
        if not (0<=i<16 and 0<=j<16) or (i,j) in group or pixels[j,i]>=26:
            continue
        group.add((i,j))
        pending.extend([(i+1,j),(i-1,j),(i,j+1),(i,j-1)])
    seen.update(group)
    xs,ys=zip(*group)
    bounds=(min(xs),max(xs)+1,min(ys),max(ys)+1)
    assert len(group)==(bounds[1]-bounds[0])*(bounds[3]-bounds[2])
    windows.append(bounds)
assert len(windows)==4

patch=run["images"]["oak"]["patches"][0]["patch"]
row=(patch[1]+patch[3])//2
scale = 720/(2*math.tan(math.radians(65/2)))
cols=np.arange(440,840)
rcv_x=6.5+(cols+.5-640)*2.4/scale
rcv_y=2.5-(row+.5-360)*2.4/scale
# Integrate equal area polar strata. Sample the real depth of each aperture:
# a chord must enter AND leave through the same hole to cross the panel.
centre=np.array([6.5,2.5,6.5])
def coverage(n):
    k=np.arange(n)
    radius=np.sqrt((k+.5)/n)*.13
    phi=k*math.pi*(3-math.sqrt(5))
    disk_u=radius*np.cos(phi); disk_v=radius*np.sin(phi)
    profile=[]
    for x in rcv_x:
        wall=np.array([x,rcv_y,0.0])
        origin=wall+[0,0,.025]
        light=centre-wall
        light/=np.linalg.norm(light)
        u=np.cross(light,[0,1,0]); u/=np.linalg.norm(u)
        v=np.cross(light,u)
        rays=centre[:,None]+u[:,None]*disk_u+v[:,None]*disk_v-origin[:,None]
        near=origin[:2,None]+rays[:2,:]*((3-origin[2])/rays[2,:])
        far=origin[:2,None]+rays[:2,:]*((3+3/16-origin[2])/rays[2,:])
        allowed=np.zeros(n,dtype=bool)
        for x0,x1,t0,t1 in windows:
            valid=np.ones(n,dtype=bool)
            for q in (near,far):
                # Closed door facing south, packed flip U and flip V.
                uu=(7-q[0])*16; vv=(3-q[1])*16
                valid &= (uu>=x0)&(uu<x1)&(vv>=t0)&(vv<t1)
            allowed |= valid
        profile.append(allowed.mean())
    return np.array(profile)
reference=coverage(4096)
convergence=float(np.max(abs(reference-coverage(16384))))
def observed(folder):
    rgb=np.array(Image.open(HERE/folder/"oak.png").convert("RGB"))[row, cols,:] /255.
    mapped=rgb**2.2
    red=mapped[:,0]/(1-mapped.max(axis=1))
    dark=np.median(red[reference<.001]); bright=np.median(red[reference>.999])
    assert bright>2*dark
    return np.clip((red-dark)/(bright-dark),0,1)
edge=(reference>.03)&(reference<.97)
assert sum(edge)>40
metrics={}
for name in ("projection-final",after):
    a=observed(name)
    metrics[name]=dict(edgeRMSE=float(np.sqrt(np.mean((a[edge]-reference[edge])**2))),edgeMAE=float(np.abs(a[edge]-reference[edge]).mean()),
                       maxStep=float(abs(np.diff(a)).max()))
report=dict(afterSHA256=run["sha256"],row=int(row),x=[int(cols[0]),int(cols[-1])],edgePixels=int(sum(edge)),diskSamples=4096,convergence4096vs16384=convergence,
            measurements=metrics,description="display red after inverse pack tone curve and within-row dark/lit calibration; not an absolute radiance readback")
with (HERE/(prefix+"edge-profile.json")).open("x") as f: json.dump(report,f,indent=2)
print(report)
sheet=Image.new("RGB",(1080,400),(21,24,28))
font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",19)
for i,(name,label) in enumerate([("projection-final","3点で評価した初期版"),(after,"扉の光路を32点で評価")]):
    photo=Image.open(HERE/name/"oak.png").convert("RGB")
    x=i*540
    sheet.paste(photo.crop((475,190,805,398)).resize((540,342),Image.Resampling.LANCZOS),(x,0))
    ImageDraw.Draw(sheet).text((x+13,353),label,font=font,fill="white")
sheet.save(HERE/(prefix+"edge-comparison.jpg"),quality=94)
