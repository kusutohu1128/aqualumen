"""Look for the actual penumbra on the ordinary, photographed grass in both clients."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from ground import HERE,WOOD,LOG,LIGHT,PASS,NAMES,camera,clear_of_dropped_log,trail,verified_photos


def cameras(run):
    r=verified_photos(run)
    views=r["results"]["grassViews"]
    assert [v["name"] for v in views]==NAMES and r["labFilesUnchanged"] and r["cleanExit"]
    return [(camera(v["pose"]),np.asarray(Image.open(run/(n+"-ingame.png")).convert("RGB"))) for n,v in zip(NAMES,views)]


def crosses(a,b,cell):
    # The last dimension contains xyz. a and b may each be a single endpoint.
    ray=b-a
    with np.errstate(divide="ignore",invalid="ignore"):
        t0=(cell-a)/ray;t1=(np.asarray(cell)+1-a)/ray
    fixed=abs(ray)<1e-10;inside=(a>=cell)&(a<=np.asarray(cell)+1)
    lo=np.where(fixed,np.where(inside,-np.inf,np.inf),np.minimum(t0,t1))
    hi=np.where(fixed,np.where(inside,np.inf,-np.inf),np.maximum(t0,t1))
    return np.maximum(0,lo.max(axis=-1))<np.minimum(1,hi.min(axis=-1))


def project(cam,points,w,h):
    (eye,fw,right,up)=cam
    rel=points-eye
    depth=rel@fw
    scale=2*np.tan(np.radians(35))/h
    x=np.rint(w/2-.5+(rel@right)/(scale*depth)).astype(int)
    y=np.rint(h/2-.5-(rel@up)/(scale*depth)).astype(int)
    return x,y,(depth>0)&(x>10)&(x<w-10)&(y>15)&(y<h-80)&~((x>960)&(y>580))


def scene():
    source=WOOD/"oak-opening"
    trail.world=Path(json.loads((source/"identity.json").read_text())["world"])
    solids=[(x,y,z) for x in range(565,574) for y in range(64,68) for z in range(415,424) if trail.name(x,y,z) not in PASS]
    pts=np.array([(x,64.,z) for x in np.arange(569.03,572,.025) for z in np.arange(416.03,419.85,.025)
                  if trail.name(int(x),63,int(z))=="grass_block"])
    return pts,solids


def visibility(pts,solids):
    # Sample the complete finite disk. The only permitted light blocker is the cut log.
    a=pts+[0,.025,0]
    l=LIGHT-pts;l/=np.linalg.norm(l,axis=1,keepdims=True)
    u=np.cross(l,[0,1,0]);u/=np.linalg.norm(u,axis=1,keepdims=True);v=np.cross(l,u)
    blocked=np.zeros(len(pts));clean=np.ones(len(pts),dtype=bool)
    # Reject the entire cone conservatively if any other cell could intersect it.
    for cell in solids:
        delta=LIGHT-a
        spread=.13*np.sqrt(u*u+v*v)
        # A cone is contained by its centre segment tested against an expanded cell.
        lo=np.asarray(cell)-spread;hi=np.asarray(cell)+1.+spread
        with np.errstate(divide="ignore"):
            t0=(lo-a)/delta;t1=(hi-a)/delta
        clean&=np.maximum(0,np.minimum(t0,t1).max(axis=1))>=np.minimum(1,np.maximum(t0,t1).min(axis=1))
    for k in range(257):
        r=.13*np.sqrt((k+.5)/257);phi=k*2.399963229728653+.193
        end=LIGHT+r*(np.cos(phi)*u+np.sin(phi)*v)
        blocked+=crosses(a,end,LOG)
    return 1-blocked/257,clean


def compare(arms):
    pts,solids=scene()
    fraction,valid=visibility(pts,solids)
    data={}
    for label,run in arms.items():
        cols=[]
        for name,(cam,image) in zip(NAMES,cameras(run)):
            for cell in solids+[LOG]: valid&=~crosses(cam[0],pts,cell)
            h,w=image.shape[:2];x,y,inside=project(cam,pts,w,h)
            valid&=inside & clear_of_dropped_log(x,y,run.name,name)
            x=x.clip(2,w-3);y=y.clip(2,h-3)
            patches=np.stack([image[y+dy,x+dx] for dx in (-1,0,1) for dy in (-1,0,1)],axis=1)
            cols.append(np.median(patches,axis=1)@np.array([.2126,.7152,.0722]))
        data[label]=np.asarray(cols)
    groups={"blocked":fraction==0,"open":fraction==1}
    for i in range(5):
        groups[f"partial-{i}"]=(fraction>i/5)&(fraction<(i+1)/5)
    summary={}
    for key,mask in groups.items():
        mask&=valid
        n=int(mask.sum())
        row={"points":n}
        if n:
            row["medianDiskVisibility"]=float(np.median(fraction[mask]))
            for label,cols in data.items():
                q=cols[:,mask]
                pre=(q[0]+q[2])/2-q[1];post=(q[3]+q[5])/2-q[4]
                row[label]={"intactLitMinusOff":round(float(np.median(pre)),3),"cutLitMinusOff":round(float(np.median(post)),3)}
        summary[key]=row
    return dict(samples=257,spacing=.025,basis="Common world coordinates, conservative clear ground paths. Median of paired (lit+relit)/2 minus off in display-code luma. Natural exposure, dawn, texture and indirect light contribute; no linear relation to disk visibility is assumed.",groups=summary)


if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument("--stock-only",action="store_true");args=ap.parse_args()
    arms={"stock":WOOD/"oak-opening"}
    if not args.stock_only: arms["slabs"]=WOOD/"oak-opening-slabs"
    out=compare(arms)
    f=HERE/("edge-stock.json" if args.stock_only else "edge-comparison.json")
    f.write_text(json.dumps(out,indent=2)+"\n")
    print(out["groups"])
