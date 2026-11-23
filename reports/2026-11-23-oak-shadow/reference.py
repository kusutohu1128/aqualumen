"""Compare the actual lampVisibility() return to double-precision disk/slab intersections."""
import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[1] / "build/oak-shadow"
SAMPLES = 16384


def rows():
    for scene in range(4):
        for z in (30.25, 28.25, 25.25):
            for radius in (.13, .32):
                front = 32.5 + .5 * (35.5-z) / 2.5
                for feature in ("edge", "corner"):
                    for shift in np.linspace(-.55, .55, 93):
                        xyz = (front+shift, 32.5 if feature=="edge" else front+.6*shift, z)
                        yield scene, feature, (*xyz,32.5,32.5,35.5,radius)
        for z in np.linspace(30.8,34.2,137):
            yield scene, "floor", (34.5,32.025,z,30.5,32.64,33.5,.13)


def reference(point, scene, disk):
    if scene==0:
        return 1.
    if scene==3:
        return None  # compare the two shaders on the identical captured cutout
    a,b=np.split(np.array(point[:6]),2)
    axis=b-a+np.array([0,.025,0])
    axis/=np.linalg.norm(axis)
    u=np.cross(axis, [0,1,0] if abs(axis[1])<.9 else [1,0,0])
    u*=point[-1]/np.linalg.norm(u)
    delta=b-a+disk[:,:1]*u+disk[:,1:]*np.cross(axis,u)
    blocked=np.zeros(len(disk),dtype=bool)
    for lower in ([(32,32,32)] if scene==1 else [(32,32,32),(33,32,32)]):
        left=(lower-a)/delta
        right=(np.array(lower)+1-a)/delta
        begin=np.maximum(np.minimum(left,right).max(axis=1),0.)
        end=np.minimum(np.maximum(left,right).min(axis=1),1.)
        blocked|=begin<end
    return 1.-float(blocked.mean())


def analyse(source, destination):
    lines=source.read_text().splitlines()
    renderer=next(s.removeprefix("renderer ") for s in lines if s.startswith("renderer "))
    values=[s.split() for s in lines if s and s[0].isdigit() and len(s.split())==5]
    samples=list(rows())
    assert len(values)==len(samples)
    i=np.arange(SAMPLES)
    angles=i*(np.pi*(3-np.sqrt(5)))+.731
    disk=np.c_[np.cos(angles),np.sin(angles)]*np.sqrt((i+.5)/SAMPLES)[:,None]
    output={}
    for val,(scene,feature,point) in zip(values,samples):
        s,_,stock,candidate,analytic=map(float,val)
        assert s==scene
        group=output.setdefault((scene,feature),[])
        group.append((stock,candidate,analytic,reference(point,scene,disk)))
    stats={}
    for (scene,feature),entries in output.items():
        m=np.array(entries,dtype=float)
        used=m[:,2]>=0
        base,cand,ref=m[:,0],m[:,1],m[:,3]
        key=f"{['empty','cube','two-cubes','cube-and-door'][scene]}/{feature}"
        rec=dict(receivers=len(m),analyticUsed=int(used.sum()),maxFallbackChange=float(np.max(abs(base[~used]-cand[~used]),initial=0)))
        if scene!=3:
            partial=(ref>.001)&(ref<.999)
            rec.update(penumbra=int(partial.sum()),analyticPenumbra=int((partial&used).sum()),
                       maxAnalyticError=float(np.max(abs(cand[used]-ref[used]),initial=0)),
                       meanSignedChange=float(np.mean(cand-base)))
            if partial.any():
                rec.update(stockMeanAbsoluteError=float(abs(base[partial]-ref[partial]).mean()),
                           candidateMeanAbsoluteError=float(abs(cand[partial]-ref[partial]).mean()),
                           stockLevels=len(np.unique(np.round(base[partial],4))),
                           candidateLevels=len(np.unique(np.round(cand[partial],4))))
        if scene==1 and feature in ("edge","corner"):
            slices=[]
            for idx,(z,r) in enumerate((z,r) for z in (30.25,28.25,25.25) for r in (.13,.32)):
                sweep=m[93*idx:93*(idx+1)]
                eligible=sweep[:,2]>=0
                large=[]
                for j in np.flatnonzero(eligible[1:]!=eligible[:-1]):
                    measured=sweep[j+1,1]-sweep[j,1]
                    expected=sweep[j+1,3]-sweep[j,3]
                    large.append(abs(measured-expected))
                offsets=np.linspace(-.55,.55,93)
                def width(col):
                    vals=sweep[:,col]
                    # First crossing on the outward sweep. The integration range
                    # must bracket both thresholds to give a physical width.
                    if vals[0]>=.10 or vals[-1]<=.90:return None
                    def first(v):
                        j=np.flatnonzero(vals>=v)[0]
                        t=(v-vals[j-1])/(vals[j]-vals[j-1])
                        return offsets[j-1]+t*(offsets[j]-offsets[j-1])
                    return round(float(first(.9)-first(.1)),5)
                slices.append(dict(receiverZ=z,lampRadius=r,referenceWidth=width(3),studyWidth=width(1),
                                   methodSwitches=len(large),maxExcessAtSwitch=max(large,default=None)))
            rec["sweeps"]=slices
        stats[key]=rec
    report=dict(renderer=renderer,referenceDiskRays=SAMPLES,groups=stats,
                notes="Each group includes all rows, including deliberate conservative fallbacks. Visibility is measured before shading, exposure and tone mapping.")
    destination.write_text(json.dumps(report,indent=2)+"\n")
    print(renderer,stats["cube/edge"],stats["cube/corner"])


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--analyse",nargs=2,type=Path)
    args=parser.parse_args()
    if args.analyse:
        analyse(*args.analyse)
    else:
        (WORK/"receivers.txt").write_text("".join(f"{s} "+" ".join(f"{p:.9f}" for p in point)+"\n" for s,_,point in rows()))
