"""Follow registered wet grass across a lamp-grid boundary using recorded F3 coordinates."""
from collections import defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import sys
import numpy as np
from display_results import WOOD, HERE, ROOT, camera, WEIGHTS, trail
sys.path.insert(0,str(ROOT/"reports/2026-11-21-rain-eaves/journey"))
import hud
SIZE=(1600,900); EDGE=568.

def load_run(run, expected):
    d=WOOD/run
    r=json.loads((d/"complete.json").read_text())
    assert r["results"]["completed"]==["cross-under-rainy-oak"] and not r["results"].get("failed")
    assert not r["logErrors"] and not r["benchmarkSentinelPresent"]
    assert all(r[k] for k in ("cleanExit","labFilesUnchanged","modsUnchanged","previousSaveUnchanged","worldZipUnchanged"))
    assert r["packSha256"]=="fb3026acb3535855bad31671c4fc3f1bccf50d75004960a085b6db4f1905b583"
    assert r["savedLevel"]["raining"] and r["savedLevel"]["DayTime"]==66000
    assert [s["light"] for s in r["results"]["stormCrossings"]]==expected
    return d,r

def project(points,xyz,angle):
    eye,fw,right,up=camera(dict(xyz=xyz,angle=angle))
    vec=points-eye; f=vec@fw
    scale=2*math.tan(math.radians(35))/900
    return np.column_stack([799.5+(vec@right)/(f*scale),449.5-(vec@up)/(f*scale)])

def viewable(eye,targets):
    # Reject ground obstructed by a block or plant using the identical archived terrain.
    keep=[]
    for point in targets:
        ray=point-eye; steps=math.ceil(np.linalg.norm(ray)/.05)
        keep.append(all(trail.name(*map(int,np.floor(eye+ray*(k/steps)))) in ("air","cave_air")
                        for k in range(steps)))
    return np.asarray(keep,dtype=bool)

def ground(crossings):
    # Texel centres, 16 per block per axis, sampled from exactly the same world points.
    pts=np.array([(570+(u+.5)/16,64.,419+(v+.5)/16) for u in range(64) for v in range(32)])
    keep=np.array([trail.name(math.floor(x),63,math.floor(z))=="grass_block" for x,_,z in pts])
    for leg in crossings:
        _,y,z=leg["before"]["xyz"]; angle=leg["before"]["angle"]
        for x in np.arange(567.,569.01,.25):
            pose=(x,y,z); pix=project(pts,pose,angle)
            # F3 text, reticle, hotbar and held hand are outside this rectangle.
            valid=(pix[:,0]>840)&(pix[:,0]<1070)&(pix[:,1]>478)&(pix[:,1]<780)
            keep&=valid
            ids=np.where(keep)[0]
            keep[ids]&=viewable(np.array(pose)+[0,1.62,0],pts[ids])
    assert keep.sum()>=45,keep.sum()
    return pts[keep]

def get_frames(path):
    opts=["ffmpeg","-v","error","-i",str(path),"-f","rawvideo","-threads","1","-pix_fmt","rgb24","pipe:1"]
    with subprocess.Popen(opts,stdout=subprocess.PIPE) as ff:
        size=SIZE[0]*SIZE[1]*3
        while True:
            data=ff.stdout.read(size)
            if not data: break
            assert len(data)==size
            yield np.frombuffer(data,np.uint8).reshape(900,1600,3)
        assert ff.wait()==0

def fit_sides(series, radius):
    x=np.array([p[0]-EDGE for p in series]); y=np.array([p[1] for p in series])
    intercepts=[];errors=[];counts=[]
    for side in (-1,1):
        valid=(x*side>=0)&(x*side<=radius)
        if valid.sum()<2: return None
        a,b=np.polyfit(x[valid],y[valid],1)
        intercepts.append(b);counts.append(int(valid.sum()))
        errors.append(float(np.sqrt(np.mean((a*x[valid]+b-y[valid])**2))))
    return dict(extrapolatedJump=float(intercepts[1]-intercepts[0]),pointsPerSide=counts,rmsPerSide=errors)

def track(folder,leg,pts):
    values=defaultdict(list);readable=0; frames=0
    for frame in get_frames(folder/leg["video"]):
        frames+=1;pos=hud.position(frame)
        if not pos:continue
        readable+=1
        if abs(pos[0]-EDGE)>1 or abs(pos[1]-64.)>.01:continue
        pixel=np.rint(project(pts,pos,leg["before"]["angle"])).astype(int)
        x,y=pixel.T
        # A 3x3 footprint reduces texture aliasing near the moving block face.
        samples=np.stack([frame[y+j,x+i]@WEIGHTS for j in (-1,0,1) for i in (-1,0,1)])
        values[pos[0]].append(float(np.median(np.median(samples,axis=0))))
    series=sorted([x,float(np.median(ys))] for x,ys in values.items())
    left=[p for p in series if p[0]<EDGE];right=[p for p in series if p[0]>=EDGE]
    assert len(left)>=2 and len(right)>=2 and readable/frames>.80,(frames,readable,series)
    return dict(frames=frames,readablePoses=readable,uniquePositions=len(series),observed=series,
                beforeBoundary=left[-1],afterBoundary=right[0],actualStep=right[0][1]-left[-1][1],
                fitted={str(r):fit_sides(series,r) for r in (.6,.8,1.)})

def main():
    plain,p=load_run("rainy-oak-walk-r2",["warm","soul","empty"])
    folder,r=load_run("rainy-oak-tracked-r2",["warm-track","empty-track"])
    source=json.loads((WOOD/"oak-night-trail/identity.json").read_text())
    trail.world=Path(source["world"])
    legs=r["results"]["stormCrossings"]; points=ground(legs)
    report=dict(packSHA=p["packSha256"],renderer=p["renderer"],dayTime=66000,weather="rain",edgeX=EDGE,
                registeredPoints=points.tolist(),leafBlocksOverPath=p["results"]["leafBlocksOverPath"],crossings={})
    for d,record in ((plain,p),(folder,r)):
        for leg in record["results"]["stormCrossings"]:
            video=d/leg["video"]
            info=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0","-count_frames",
                          "-show_entries","stream=width,height,codec_name,nb_read_frames,duration","-of","json",str(video)]))["streams"][0]
            assert (info["width"],info["height"])==SIZE and int(info["nb_read_frames"])>=20
            row=dict(before=leg["before"]["xyz"],after=leg["after"]["xyz"],media=info,
                     video=str(video.relative_to(ROOT)),sha256=sha256(video.read_bytes()).hexdigest())
            if leg in legs: row["registeredGrass"]=track(d,leg,points)
            report["crossings"][leg["light"]]=row
    (HERE/"storm-motion.json").write_text(json.dumps(report,indent=2)+"\n")
    for leg in legs:
        v=report["crossings"][leg["light"]]["registeredGrass"];print(leg["light"],v)

if __name__=="__main__":main()
