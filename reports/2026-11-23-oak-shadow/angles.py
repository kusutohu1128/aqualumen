"""Stress every signed major axis, adjacent boxes, disjoint boxes and a third blocker."""
from pathlib import Path
import argparse
import json
import numpy as np
from reference import HERE,WORK,SAMPLES

BOXES={1:[(32,32,32)],4:[(32,32,32),(33,32,33)],5:[(32,32,32),(33,32,33),(33,33,33)],6:[(32,32,32),(32,33,32)]}


def points():
    for scene in BOXES:
        rng=np.random.default_rng(9130)
        for major in range(3):
            for sign in [-1,1]:
                for i in range(100):
                    # Aim near an edge of either blocker. The point oracle below
                    # uses the AABB slabs and does not project the cube faces.
                    cell=np.asarray(BOXES[scene][i%len(BOXES[scene])])
                    target=cell+rng.uniform(.04,.96,3)
                    side=(major+1+i%2)%3
                    target[side]=cell[side]+rng.choice([0.,1.])+rng.uniform(-.15,.15)
                    vector=rng.uniform(-.75,.75,3)
                    vector[major]=sign
                    source=np.floor(target+vector*rng.uniform(2.4,5.5))+.5
                    start=target+(target-source)*rng.uniform(.55,2.7)
                    radius=rng.uniform(.08,.38)
                    yield scene,f"{'xyz'[major]}{'+' if sign>0 else '-'}",(*start,*source,radius)


def analyse(file,out):
    lines=file.read_text().splitlines()
    renderer=next(s[9:] for s in lines if s.startswith("renderer "))
    values=np.array([[float(v) for v in s.split()] for s in lines if s and s[0].isdigit()])
    dataset=list(points())
    assert len(values)==len(dataset)
    i=np.arange(SAMPLES)
    theta=2.399963229728653*i+.731
    disk=np.sqrt((i+.5)/SAMPLES)[:,None]*np.c_[np.cos(theta),np.sin(theta)]
    stats={}
    for (scene,axis,point),line in zip(dataset,values):
        number,_,stock,study,area=line
        assert number==scene
        a,b=np.split(np.array(point[:6]),2)
        l=b-a+[0,.025,0];l/=np.linalg.norm(l)
        u=np.cross(l,[0,1,0] if abs(l[1])<.9 else [1,0,0]);u*=point[-1]/np.linalg.norm(u)
        delta=b-a+disk[:,:1]*u+disk[:,1:]*np.cross(l,u)
        occlusion=np.zeros(SAMPLES,dtype=bool)
        for cell in BOXES[scene]:
            t0=(cell-a)/delta;t1=(np.array(cell)+1-a)/delta
            occlusion|=np.maximum(0,np.minimum(t0,t1).max(axis=1))<np.minimum(1,np.maximum(t0,t1).min(axis=1))
        ref=1.-occlusion.mean()
        stats.setdefault((scene,axis),[]).append((stock,study,area,ref))
    metrics={}
    for (scene,axis),entries in stats.items():
        w=np.array(entries);used=w[:,2]>=0.;partial=(w[:,3]>.001)&(w[:,3]<.999)
        abs_err=np.abs(w[:,1]-w[:,3])
        metrics[f"{scene}/{axis}"]=dict(points=len(w),used=int(used.sum()),partial=int(partial.sum()),usedPartial=int((used&partial).sum()),
             maxAcceptedError=float(np.max(abs_err[used],initial=0.)),
             maxRejectedChange=float(np.max(np.abs(w[~used,0]-w[~used,1]),initial=0.)))
    report=dict(renderer=renderer,rays=SAMPLES,geometry=BOXES,groups=metrics)
    out.write_text(json.dumps(report,indent=2)+"\n")
    print(renderer,max(r["maxAcceptedError"] for r in metrics.values()))


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--analyse",type=Path,nargs=2)
    args=ap.parse_args()
    if args.analyse: analyse(*args.analyse)
    else:
        (WORK/"angles.txt").write_text("".join(str(s)+" "+" ".join(f"{p:.9f}" for p in point)+"\n" for s,_,point in points()))
