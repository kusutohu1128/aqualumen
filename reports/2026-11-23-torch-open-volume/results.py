"""Decode the registered F2s, lossless transitions and uninstrumented render intervals."""
from hashlib import sha256
import json
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
from room import HERE, PACKS, STAGES
from pack import BASE_SHA

DENSITY=HERE.parent/"2026-11-23-torch-density"
WEIGHTS=np.array([.2126,.7152,.0722])


def read(path):
    return json.loads(path.read_text())


def receipt(directory,sha):
    r=read(directory/"complete.json")
    p=read(directory/"preflight.json")
    assert r["complete"] and not r["failure"] and r["originalWorldAndConfigUnchanged"]
    assert r["packSha256"]==r["sourcePackShaNow"]==sha and r["shaderpackLogged"]
    assert "RTX 3080 Ti" in r["gl"]["renderer"] and p["labAfter"]==p["labBefore"]
    assert not p["foreignObservations"] and p["samples"]>0
    return r


def rgb(path):
    with Image.open(path) as im: return np.array(im.convert("RGB"))


def photo(directory,record,stage):
    p=directory/f"{stage}-ingame.png"
    assert sha256(p.read_bytes()).hexdigest()==record["screenshots"][stage]["ingame"]
    return rgb(p)


def channels(img):
    counts=img[:,::2]
    direct=img[:,1::2]
    return dict(calls=counts[:,:,0]%16,surface=counts[:,:,0]//16,open=counts[:,:,1]%16,
                reused=counts[:,:,1]//16,body=counts[:,:,2]//16,bad=counts[:,:,2]%16,vis=direct[:,:,0])


def decoded(img):
    ramp=np.repeat(np.arange(256,dtype=np.uint8)[:,None],3,axis=1)
    assert np.array_equal(img[-3,:256],ramp)
    # The marker occupies the third row from the bottom. Stop five rows early.
    return channels(img[:-5])


def totals(d):
    assert (d["open"]<=d["calls"]).all() and (d["reused"]<=1).all()
    return dict(calls=int(d["calls"].sum()),open=int(d["open"].sum()),
                reused=int((d["open"]*d["reused"]).sum()),entityCandidates=int(d["body"].sum()),
                disagreements=int(d["bad"].sum()))


def forest():
    times={}
    stills={}
    geometry=read(DENSITY/"gp-density-open-volume-control-a/geometry.json")
    for name,sha in (("control-a",BASE_SHA),("trial-a",PACKS["trial"][1]),
                     ("cell-a",PACKS["cell"][1]),("cell-b",PACKS["cell"][1]),("control-b",BASE_SHA)):
        path=DENSITY/("gp-density-open-volume-"+name)
        r=receipt(path,sha)
        assert r["stages"]==["birch-4"] and r["size"]==[2560,1440]
        assert read(path/"geometry.json")==geometry
        assert "gpuProfilerSha256" not in read(path/"observer.json")
        s=read(path/"summary.json")["scenes"]["birch-4"]
        times[name]={k:s[k] for k in ("cpuMeanMs","cpuP99Ms","frames")}
        if name in ("control-a","cell-a"):
            stills[name]=np.stack([rgb(path/f"birch-4-{kind}.png") for kind in ("ingame","x11-a","x11-b")]).astype(np.int16)
    regions={}
    for key,(x,y,right,bottom) in {"shadedBark":(770,390,925,760),"sunlitGrass":(1580,895,1740,960)}.items():
        a,b=(stills[n][:,y:bottom,x:right] for n in ("control-a","cell-a"))
        stable=(np.ptp(a,axis=0).max(2)<=1)&(np.ptp(b,axis=0).max(2)<=1)
        gap=np.maximum(0,np.maximum(a.min(0)-b.max(0),b.min(0)-a.max(0))).max(2)
        assert stable.any()
        regions[key]=dict(samples=int(stable.sum()),maxChannelGap=int(gap[stable].max()),
                          anyChannelGap=int(np.count_nonzero(gap[stable])))
    meters={}
    for key,mode in (("readout","meter"),("cell-readout","cell-meter")):
        path=DENSITY/("gp-density-open-volume-"+key)
        r=receipt(path,PACKS[mode][1])
        assert read(path/"geometry.json")==geometry
        m=decoded(photo(path,r,"birch-4"))
        meters[mode]=totals(m)
        assert meters[mode]["open"]>10000
    return dict(timing=times,diagnostics=meters,stableRegions=regions)


def grove():
    cache=HERE/"grove-cell-meter"
    ref=receipt(cache,PACKS["cell-meter"][1])
    assert ref["stages"]==STAGES
    scene=read(cache/"geometry.json")
    assert scene["shiftedX"]==407.83 and scene["source"]=="405 151 -408"
    masks={n:decoded(photo(cache,ref,n)) for n in STAGES}
    sums={n:totals(m) for n,m in masks.items()}
    assert all(sums[n]["calls"]==0 for n in ("shade","extinguished"))
    assert all(sums[n]["reused"]>0 for n in ("torch","trunk","shifted","home","trunk-cut"))
    # A surface must survive insertion of the trunk, still face the source
    # and return to its original visibility after the trunk is removed.
    samples={}
    for label,face in (("grassFloor",1),("backWall",2)):
        stages=("torch","trunk","home","trunk-cut")
        match=np.logical_and.reduce([(masks[n]["surface"]==face)&(masks[n]["calls"]==1) for n in stages])
        openBefore=masks["torch"]["vis"]==255
        shadow=masks["trunk"]["vis"]==0
        dark=match & openBefore & shadow & (masks["home"]["vis"]==0) & (masks["trunk-cut"]["vis"]==255)
        samples[label]=dict(trunkUmbraPixels=int(dark.sum()),matchedPixels=int(match.sum()),
                           restoredVisible=int((match & openBefore & (masks["trunk-cut"]["vis"]==255)).sum()))
        for mode in ("control","cell"):
            path=HERE/f"grove-{mode}"
            run=receipt(path,PACKS[mode][1])
            registered=read(path/"geometry.json")
            assert all(registered[k]==v for k,v in scene.items() if k!="shiftedX")
            if "shiftedX" in registered: assert registered["shiftedX"]==scene["shiftedX"]
            photos={n:photo(path,run,n)[:-5,::2] for n in ("shade","torch","trunk","trunk-cut","extinguished")}
            delta=photos["torch"].astype(float)@WEIGHTS-photos["shade"].astype(float)@WEIGHTS
            # With the torch removed, preview 13 shades this surface forward
            # and sets no deferred lamp-owner marker. The fixed camera, floor
            # and wall are guarded in both stages; use the lit world-face mask.
            lit=match & openBefore
            assert np.any(lit)
            samples[label][mode]=dict(litSamples=int(lit.sum()),litMedianGain8bit=float(np.median(delta[lit])),
                                      brighterByTwo=int((delta[lit]>=2).sum()),
                                      medianUmbraRGB={n:np.median(im[dark],axis=0).tolist() for n,im in photos.items()} if dark.any() else {})
    txt=(cache/"client.log").read_text().split("[Server] AQ_WALK_START")[-1].split("[Server] AQ_WALK_END")[0]
    points=np.array([list(map(int,p)) for p in re.findall(r'\[Server\] AQ_WALK_MM (-?\d+) (-?\d+) (-?\d+)',txt)])/1000
    assert len(points)>2
    return dict(diagnostics=sums,surfaces=samples,cowPositions=len(points),cowDisplacementMetres=float(np.linalg.norm(points[-1]-points[0])))


def transitions(path):
    size=512*256*3
    proc=subprocess.Popen(["ffmpeg","-v","error","-i",str(path),"-pix_fmt","rgb24","-f","rawvideo","-"],stdout=subprocess.PIPE)
    summary=dict(frames=0,uniqueAdjacent=0,queries=0,open=0,reused=0,bad=0,entityCandidates=0)
    prev=b""
    while True:
        raw=proc.stdout.read(size)
        if not raw: break
        assert len(raw)==size
        summary["frames"]+=1
        if raw==prev: continue
        prev=raw
        summary["uniqueAdjacent"]+=1
        m=channels(np.frombuffer(raw,dtype=np.uint8).reshape(256,512,3))
        v=totals(m)
        for k,s in (("queries","calls"),("bad","disagreements"),("open","open"),("reused","reused"),("entityCandidates","entityCandidates")):
            summary[k]+=v[s]
    assert proc.wait()==0 and summary["uniqueAdjacent"]>5
    return summary


def native():
    rows={}
    renderers={}
    for tag in ("rtx","mesa"):
        lines=(HERE/f"cache-probe-{tag}.log").read_text().splitlines()
        renderers[tag]=next(line[9:] for line in lines if line.startswith("renderer "))
        rows[tag]={m[1]:list(map(int,m.groups()[1:])) for line in lines
                   if (m:=re.fullmatch(r"([a-z-]+) (\d+) (\d+) (\d+)",line))}
    assert "RTX 3080 Ti" in renderers["rtx"] and "llvmpipe" in renderers["mesa"]
    assert rows["rtx"]==rows["mesa"] and len(rows["rtx"])==14
    return dict(renderers=renderers,states=rows["rtx"],queriesPerRenderer=sum(v[0] for v in rows["rtx"].values()))


if __name__=="__main__":
    clip=HERE/"grove-cell-meter/late-transitions.mkv"
    first=HERE/"grove-placement/transitions.mkv"
    receipt(first.parent,PACKS["cell-meter"][1])
    result=dict(forest=forest(),grove=grove(),native=native(),movie=dict(window=read(clip.with_name("late-capture.json")),observed=transitions(clip)),
                placement=dict(window=read(first.with_name("capture.json")),observed=transitions(first)))
    (HERE/"results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    assert all(v["disagreements"]==0 for v in (*result["forest"]["diagnostics"].values(),*result["grove"]["diagnostics"].values()))
    assert result["movie"]["observed"]["bad"]==result["placement"]["observed"]["bad"]==0
