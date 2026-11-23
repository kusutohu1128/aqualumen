"""Register six ordinary F2 frames to fixed pieces of ground beside the saved oak."""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
WOOD=HERE.parent/"2026-11-21-animal-light/woodland"
sys.path.insert(0,str(WOOD))
import trail

LOG=(568,64,418)
LIGHT=np.array([566.5,64.64,419.5])
PASS={"air","cave_air","torch","soul_torch"}
NAMES=["intact-lit","intact-off","intact-relit","cut-lit","cut-off","cut-relit"]


def hits(a,ends,lower):
    delta=ends-a
    # Keep a parallel ray inside an axis slab if its origin is inside it.
    with np.errstate(divide="ignore",invalid="ignore"):
        t0=(np.asarray(lower)-a)/delta
        t1=(np.asarray(lower)+1-a)/delta
    parallel=abs(delta)<1e-10
    inside=(np.asarray(lower)<=a)&(a<=np.asarray(lower)+1)
    near=np.where(parallel,np.where(inside,-np.inf,np.inf),np.minimum(t0,t1))
    far=np.where(parallel,np.where(inside,np.inf,-np.inf),np.maximum(t0,t1))
    return np.maximum(0,near.max(axis=-1))<np.minimum(1,far.min(axis=-1))


def clear_of_dropped_log(x,y,run,capture):
    # In these three F2 frames the cut log bobs in front of the grass.
    if run=="oak-opening-slabs" and capture.startswith("cut-"):
        return (x<550)|(x>710)|(y<230)|(y>425)
    return True


def camera(obs):
    eye=np.asarray(obs["xyz"])+[0,1.62,0]
    yaw,pitch=np.radians(obs["angle"])
    forward=np.array([-np.sin(yaw)*np.cos(pitch),-np.sin(pitch),np.cos(yaw)*np.cos(pitch)])
    right=np.cross(forward,[0,1,0])
    right/=np.linalg.norm(right)
    return eye,forward,right,np.cross(right,forward)


def verified_photos(directory):
    r=json.loads((directory/"complete.json").read_text())
    assert r["cleanExit"] and r["labFilesUnchanged"] and r["modsUnchanged"] and r["previousSaveUnchanged"] and r["worldZipUnchanged"] and not r["logErrors"]
    views=r["results"]["grassViews"]
    assert [v["name"] for v in views]==NAMES
    times=[v["pose"]["t"] for v in views]
    assert times==sorted(times) and len(set(times))==6
    observations=json.loads((directory/"positions.json").read_text())
    for i,label,target in ((0,"lamp-removed",[566,63,419]),(1,"lamp-placed",[566,64,419]),
                          (2,"select-lowest-log",[568,64,418]),(2,"floor-in-opening",[568,63,418]),
                          (3,"lamp-removed",[566,63,419]),(4,"lamp-placed",[566,64,419])):
        assert any(o["label"]==label and o["target"]==target and times[i]<o["t"]<times[i+1] for o in observations)
    failures=r["results"].get("failed",[])
    if failures:
        assert directory.name=="oak-opening-slabs" and len(failures)==1
        assert failures[0]["lastObservation"]["label"]=="post-built-final"
        assert failures[0]["lastObservation"]["t"]>times[-1]
    else:
        assert "cut-oak-and-build-lantern-post" in r["results"]["completed"]
    return r


def sample(dir_,prefix="ground"):
    assert prefix in ("ground","slabs-ground")
    receipt=verified_photos(dir_)
    views=receipt["results"]["grassViews"]
    assert [v["name"] for v in views]==NAMES
    photos=[np.array(Image.open(dir_/(n+"-ingame.png")).convert("RGB")) for n in NAMES]
    cams=[camera(v["pose"]) for v in views]
    assert all(np.array_equal(c[0],cams[0][0]) for c in cams), "different receiver sight lines"
    h,w=photos[0].shape[:2]
    assert (h,w)==(900,1600) and all(p.shape==photos[0].shape for p in photos)
    scale=2*math.tan(math.radians(35))/h
    trail.world=Path(json.loads((dir_/"identity.json").read_text())["world"])
    assert trail.name(*LOG)=="air"
    geometry=[(x,y,z) for x in range(565,574) for y in range(64,68) for z in range(415,424)
              if trail.name(x,y,z) not in PASS]
    ring=(np.arange(129)+.5)/129
    angle=2.399963229728653*np.arange(129)
    disk=(.13*np.sqrt(ring))[:,None]*np.array([np.cos(angle),np.sin(angle)]).T
    groups={"behindLog":[],"besideLog":[]}
    for x in np.arange(569.06,572,.10):
        for z in np.arange(416.07,419.85,.10):
            if trail.name(math.floor(x),63,math.floor(z))!="grass_block":continue
            point=np.array([x,64.,z])
            # Reject plants and any intervening blocks on every camera-to-ground path.
            if any(hits(cams[0][0],point,cell) for cell in geometry+[LOG]):continue
            a=point+[0,.025,0]
            axis=LIGHT-point;axis/=np.linalg.norm(axis)
            u=np.cross(axis,[0,1,0]);u/=np.linalg.norm(u)
            ends=LIGHT+disk[:,:1]*u+disk[:,1:]*np.cross(axis,u)
            if any(hits(a,ends,cell).any() for cell in geometry):continue
            occluded=hits(a,ends,LOG)
            if not (occluded.all() or not occluded.any()):continue
            obs=[]
            for capture,(eye,fw,right,up),photo in zip(NAMES,cams,photos):
                v=point-eye
                f=v@fw
                if f<=0:break
                px=round(w/2-.5+(v@right)/(f*scale));py=round(h/2-.5-(v@up)/(f*scale))
                if not (15<px<w-15 and 20<py<h-80) or (px>960 and py>580):break
                if not clear_of_dropped_log(px,py,dir_.name,capture):break
                obs.append(([px,py],np.median(photo[py-2:py+3,px-2:px+3],axis=(0,1))))
            if len(obs)==6:
                groups["behindLog" if occluded.all() else "besideLog"].append((point,obs))
    weights=np.array([.2126,.7152,.0722])
    sampledata={}
    for label,samples in groups.items():
        if not samples:raise ValueError("No receivers in "+label)
        luma=np.array([[rgb@weights for _,rgb in obs] for _,obs in samples])
        entry=dict(count=len(samples),medianDisplayLuma=dict(zip(NAMES,np.round(np.median(luma,axis=0),2))))
        for off,lit,relit,phase in ((1,0,2,"intact"),(4,3,5,"cut")):
            for col,suffix in ((lit,"LitMinusOff"),(relit,"RelitMinusOff")):
                d=luma[:,col]-luma[:,off]
                entry[phase+suffix]=np.round(np.percentile(d,[10,50,90]),2).tolist()
        entry["points"]=[dict(xz=p[[0,2]].round(3).tolist(),pixels=[xy for xy,_ in obs]) for p,obs in samples]
        sampledata[label]=entry
    panel=Image.fromarray(photos[0]).resize((800,450))
    draw=ImageDraw.Draw(panel)
    for label,color in (("besideLog","#46ddfa"),("behindLog","#ffbc46")):
        for _,obs in groups[label]:
            x,y=obs[0][0];x//=2;y//=2
            draw.ellipse((x-1,y-1,x+1,y+1),fill=color)
    panel.save(HERE/(prefix+"-receivers.png"))
    result=dict(source=str(dir_.relative_to(HERE.parents[1])),renderer=receipt["renderer"],pack=receipt["packSha256"],
                basis="Fixed world points on grass, 5x5 median RGB per registered point, Rec709 weights applied to 8-bit display channels. Percentiles P10/P50/P90 of paired differences. Natural time, indirect light and exposure contribute. Gold overlay denotes full occultation by the removed log, cyan denotes unoccluded samples. Hand area excluded.",groups=sampledata)
    (HERE/(prefix+".json")).write_text(json.dumps(result,indent=2)+"\n")
    print([(k,{a:b for a,b in v.items() if a!="points"}) for k,v in sampledata.items()])


if __name__=="__main__":
    source=(WOOD/sys.argv[1]).resolve()
    prefix={"oak-opening":"ground","oak-opening-slabs":"slabs-ground"}[source.name]
    sample(source,prefix)
