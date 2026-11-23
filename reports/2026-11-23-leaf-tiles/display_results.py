"""Read the actual 8-bit Minecraft outputs for A/B/C, including their repeat captures."""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from packs import HERE, ROOT, package

WOOD=ROOT/"reports/2026-11-21-animal-light/woodland"
sys.path.insert(0,str(HERE.parent/"2026-11-23-oak-shadow"))
from ground import camera
import trail
WEIGHTS=np.array([.2126,.7152,.0722])
MODES=("base","leaf","tiled","tiled","leaf","base")


def delta_summary(v):
    return dict(median=float(np.median(v)),p05=float(np.quantile(v,.05)),
                p95=float(np.quantile(v,.95)),p99Abs=float(np.quantile(abs(v),.99)),
                maximumAbs=float(np.max(abs(v))),fractionAbsAtLeastTwo=float(np.mean(abs(v)>=2.)),
                fractionAbsAtLeastFour=float(np.mean(abs(v)>=4.)))


def ground_pixels(pose,survey,group):
    eye,forward,right,up=camera(pose)
    pts=[p["xz"] for p in survey[group]["points"]]
    pixels={}
    for x,z in pts:
        target=np.array([x,64.,z]); vec=target-eye
        f=vec@forward
        if f<=0: continue
        # The trip's options use 70° vertical FOV with camera bob/FOV effects disabled.
        scale=2*math.tan(math.radians(35))/900
        px=round(799.5+(vec@right)/(f*scale))
        py=round(449.5-(vec@up)/(f*scale))
        if not (4<=px<1596 and 4<=py<896) or trail.name(math.floor(x),63,math.floor(z))!="grass_block":
            continue
        clear=True
        for k in np.arange(.04,np.linalg.norm(vec)-.005,.035):
            cell=np.floor(eye+vec*k/np.linalg.norm(vec)).astype(int)
            if trail.name(*map(int,cell)) not in ("air","cave_air"):
                clear=False;break
        if clear: pixels[(x,z)]=(py,px)
    return pixels


def quantify(data):
    # Per-position results in a single pose. Compare the ordinary finished RGB,
    # after the pack's own bloom, exposure, shared shoulder, AA and gamma.
    rgb=np.asarray(data,dtype=np.float64)
    y=rgb@WEIGHTS
    return dict(referenceMinusBase=delta_summary(((y[1]-y[0])+(y[4]-y[5]))/2),
                tiledMinusReference=delta_summary(((y[2]-y[1])+(y[3]-y[4]))/2),
                tiledReferenceMaxChannelError=int(max(np.max(abs(rgb[2]-rgb[1])),np.max(abs(rgb[3]-rgb[4])))),
                baseRepeat=delta_summary(y[5]-y[0]),referenceRepeat=delta_summary(y[4]-y[1]),
                tiledRepeat=delta_summary(y[3]-y[2]))

def frame_stats(images):
    keys=("referenceMinusBase","tiledMinusReference","baseRepeat","referenceRepeat","tiledRepeat")
    samples={k:[] for k in keys}
    max_channel=0
    for top in range(0,900,60):
        strips=[im[top:top+60].reshape(-1,3) for im in images]
        keep=np.ones(len(strips[0]),dtype=bool)
        if top==840:
            keep.reshape(60,1600)[-4:,:8]=False  # test label only
        y=[(s@WEIGHTS)[keep] for s in strips]
        values=(((y[1]-y[0])+(y[4]-y[5]))/2, ((y[2]-y[1])+(y[3]-y[4]))/2,
                y[5]-y[0],y[4]-y[1],y[3]-y[2])
        for k,v in zip(keys,values):samples[k].append(v)
        for a,b in ((2,1),(3,4)):
            d=np.subtract(strips[a],strips[b],dtype=np.int16)
            max_channel=max(max_channel,int(abs(d[keep]).max()))
    return dict(points=1600*900-32,tiledReferenceMaxChannelError=max_channel,
                **{k:delta_summary(np.concatenate(v)) for k,v in samples.items()})


def analyze(folder):
    rec=json.loads((folder/"complete.json").read_text())
    assert rec["results"]["completed"]==["compare-frozen-leaf-return"] and not rec["results"].get("failed")
    assert all(rec[k] for k in ("cleanExit","labFilesUnchanged","modsUnchanged","previousSaveUnchanged","worldZipUnchanged"))
    assert not rec["logErrors"] and not rec["benchmarkSentinelPresent"]
    assert sha256(package(True)[1]).hexdigest()==rec["packSha256"]
    frozen=json.loads((folder/"frozen-sky.json").read_text())
    assert not frozen["daylightCycle"] and not frozen["weatherCycle"] and rec["savedLevel"]["DayTime"]==frozen["dayTime"]==68853
    origin=json.loads((WOOD/"oak-night-trail/identity.json").read_text())
    trail.world=Path(origin["world"])
    survey=json.loads((HERE.parent/"2026-11-23-oak-shadow/ground.json").read_text())["groups"]
    result=dict(renderer=rec["renderer"],packSHA=rec["packSha256"],dayTime=68853,exposure=11.25,views={},hashes={})
    registered={}
    for item in rec["results"]["displayGroups"]:
        label,pose=item["label"],item["pose"]
        images=[]
        for i,mode in enumerate(MODES):
            p=folder/f"{label}-{i}-{mode}-ingame.png"
            with Image.open(p) as im: pic=np.array(im.convert("RGB"))
            assert pic.shape==(900,1600,3) and tuple(pic[-2,2])==(74,{"base":1,"leaf":2,"tiled":3}[mode],213)
            result["hashes"][p.name]=sha256(p.read_bytes()).hexdigest()
            images.append(pic)
        groups={}
        groups["wholeFrame"]=frame_stats(images)
        if label!="forest":
            registered[label]={}
            for group in ("behindLog","besideLog"):
                pixels=ground_pixels(pose,survey,group)
                assert len(pixels)>=20
                y,x=np.array(list(pixels.values())).T
                sample=np.stack([im[y,x] for im in images])
                groups[group]=dict(points=len(pixels),**quantify(sample))
                luma=sample@WEIGHTS
                registered[label][group]=dict(zip(pixels,((luma[1]-luma[0])+(luma[4]-luma[5]))/2))
        result["views"][label]=dict(pose=pose,groups=groups)
    result["torchOnly"]={}
    for label in ("warm","soul"):
        result["torchOnly"][label]={}
        for group in ("behindLog","besideLog"):
            on=registered[label][group];off=registered["off"][group]
            match=sorted(on.keys() & off.keys())
            result["torchOnly"][label][group]=dict(points=len(match),**delta_summary(np.array([on[k]-off[k] for k in match])))
    (HERE/"display.json").write_text(json.dumps(result,indent=2)+"\n")

    font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",18)
    sheet=Image.new("RGB",(1200,502),(22,25,27))
    draw=ImageDraw.Draw(sheet)
    for i,title in enumerate(("プレビュー10相当","葉の反射あり","葉の反射あり・計算順変更")):
        path=folder/f"warm-{i}-{MODES[i]}-ingame.png"
        with Image.open(path) as im:
            sheet.paste(im.resize((400,225),Image.Resampling.LANCZOS),(400*i,40))
            sheet.paste(im.crop((630,380,1030,605)),(400*i,275))
        draw.text((400*i+12,5),title,font=font,fill="white")
    sheet.save(HERE/"forest-display.png")
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("run",nargs="?",default="oak-tiles-frozen");a=p.parse_args()
    r=analyze(WOOD/a.run)
    print(json.dumps(r["torchOnly"],indent=2))
