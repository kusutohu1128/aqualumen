"""Tie the corrected optical normal, ordinary Minecraft photos and distribution ZIP together."""
from hashlib import sha256
import json
import re
import sys
import tempfile
import subprocess
from pathlib import Path
from zipfile import ZipFile
import numpy as np
from measure import HERE,PREVIOUS,STAGES,CAL,read,receipt,frame
from release import ROOT,VERSION,SHA
from flat_surface import TRIAL
from forest import load_run,REGIONS

METER_SHA="2275262954eacdee221460df2494f5753a84060d04c3efa52c211b6de528db0e"
PROTOTYPE_SHA="a3faf8dc80629b2a25fedafec2f16174dbcaaf061807b81a6a6919d213045593"
SHIPPED_SHA="8df2a8fcd645d58f0423d8b9974f99a186022d345c44a2ef9404b05a9c6a52c2"


def room_times(folder):
    log=(folder/"client.log").read_text()
    assert "gpuProfilerSha256" not in read(folder/"observer.json")
    result={}
    # The middle camera changed. Only compare the two identical poses.
    for stage in ("wet-empty","wet-cleared"):
        start=log.index("[Server] AQLAVA_READY_"+stage+"_END")
        end=log.index("[Server] AQLAVA_STILL_"+stage+"_END",start)
        photo=log.index(".pngとして保存しました",start,end)
        window=log[photo:end]
        batches=re.findall(r"AQ_RENDER_INTERVALS_US (\d+) ([\d ]+)",window)[3:5]
        ends=dict(re.findall(r"AQ_RENDER_FRAME_END (\d+) (\d+)",window))
        assert len(batches)==2
        us,ids=[],[]
        for stamp,batch in batches:
            values=list(map(int,batch.split()))
            last=int(ends[stamp])
            us.extend(values)
            ids.extend(range(last-len(values)+1,last+1))
        assert ids==list(range(ids[0],ids[-1]+1))
        result[stage]=dict(frames=len(ids),meanMs=float(np.mean(us))/1000,
                           firstFrame=ids[0],lastFrame=ids[-1])
    return result


def main():
    geometry=dict(read(PREVIOUS/"wet-ownership/geometry.json"),middleCamera=[409.48,151,-405.95,143.8,18.])
    meter=receipt("corrected-stone-meter",METER_SHA,geometry)
    play=receipt("corrected-stone-release",SHIPPED_SHA,geometry)
    rows={}
    for stage in STAGES:
        rows[stage]={}
        for tag in meter["screenshots"][stage]:
            im=frame("corrected-stone-meter",meter,stage,tag)
            assert np.array_equal(im[2,8:264],CAL) and not (im[:,:,2]==252).any()
            mask=np.isin(im[:,:,2],[187,188])
            certified=(im[:,:,2]==188)
            assert mask.sum()>10000
            rows[stage][tag]=dict(samples=int(mask.sum()),canonical=int(certified.sum()),
                                  maxLocalCode=int(im[:,:,0][mask].max()),maxSpecularCode=int(im[:,:,1][mask].max()))
            normal=frame("corrected-stone-release",play,stage,tag)
            assert normal.shape==im.shape and not np.array_equal(normal[2,8:264],CAL)
    output=VERSION.with_name("Aqualumen-Wet-Plane-Study.zip")
    assert sha256(output.read_bytes()).hexdigest()==SHIPPED_SHA and sha256(TRIAL.read_bytes()).hexdigest()==PROTOTYPE_SHA
    with tempfile.TemporaryDirectory() as directory:
        target=Path(directory)/"study.zip"
        subprocess.run([sys.executable,str(ROOT/"tools/build.py"),"--wet-plane-study","--output",str(target)],check=True)
        assert target.read_bytes()==output.read_bytes()
    with ZipFile(output) as shipped, ZipFile(TRIAL) as photographed, ZipFile(VERSION) as preview:
        names=shipped.namelist()
        assert len(names)==len(set(names))==139 and set(names)==set(photographed.namelist())==set(preview.namelist())
        assert shipped.testzip() is None and all(shipped.read(k)==photographed.read(k) for k in names)
        changes=[k for k in names if shipped.read(k)!=preview.read(k)]
        assert changes==sorted(["shaders/lib/terrain.fsh.glsl","shaders/lib/rain_surface.glsl"])
    oldGeo,oldTime,oldImages=load_run("gp-density-preview13-release",SHA,False)
    newGeo,newTime,newImages=load_run("gp-density-wet-plane-study",SHIPPED_SHA,False)
    assert oldGeo==newGeo
    boxes={}
    for name,(x,y,right,bottom) in REGIONS.items():
        a=np.stack([im[y:bottom,x:right] for im in oldImages])
        b=np.stack([im[y:bottom,x:right] for im in newImages])
        stable=(np.ptp(a,axis=0).max(axis=2)<=1)&(np.ptp(b,axis=0).max(axis=2)<=1)
        gap=np.maximum(0,np.maximum(a.min(0)-b.max(0),b.min(0)-a.max(0))).max(axis=2)
        boxes[name]=dict(samples=int(stable.sum()),maxGap=int(gap[stable].max()) if stable.any() else None)
    trialGeo,trialReverse,_=load_run("gp-density-wet-plane-reverse",SHIPPED_SHA,False)
    controlGeo,controlReverse,_=load_run("gp-density-wet-plane-control",SHA,False)
    assert oldGeo==controlGeo==trialGeo
    result=dict(rainRoom=dict(stored=room_times(HERE/"stored"),wetPlane=room_times(HERE/"corrected-stone-release")),
                measurements=rows,changedShaders=changes,shippedSHA=SHIPPED_SHA,photographedSHA=SHIPPED_SHA,prototypeSHA=PROTOTYPE_SHA,
                equivalentShaderPackEntries=len(names),dryBirch=dict(preview13=oldTime,wetPlane=newTime,reverseWetPlane=trialReverse,reversePreview13=controlReverse,stableRegions=boxes))
    (HERE/"wet-plane.json").write_text(json.dumps(result,indent=2)+"\n")
    print(rows)
    print(result["dryBirch"])


if __name__=="__main__":
    main()
