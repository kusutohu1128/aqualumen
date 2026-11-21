"""Compare the raw Iris visibility with ray intersections on the surveyed ground plot."""
import argparse
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image


def header(rgb):
    wire = rgb[-1,:148]
    if not (wire[:,2] == 255).all():
        raise ValueError("Missing float header marker")
    floats = np.array(struct.unpack("<74f", wire[:,:2].copy().tobytes()))
    if floats[-1] != 123.5 or not np.isfinite(floats).all():
        raise ValueError("Invalid float header")
    matrix = lambda start: floats[start:start+16].reshape(4,4).T
    return matrix(0), matrix(16), floats[32:35], floats[35:38], floats[38:41], matrix(41), matrix(57)


def boxes():
    for z in range(341,344):
        yield (130,63,z),(133,64+z-341,z+1)
        yield (136+6/16,63,z+6/16),(136+10/16,64,z+10/16)
    for y in (6,12):
        yield (136+7/16,63+y/16,341.5),(136+9/16,63+(y+3)/16,343.5)


def blocked(points, direction, max_t=np.inf):
    hit = np.zeros(len(points),dtype=bool)
    with np.errstate(divide="ignore",invalid="ignore"):
        for lo,hi in boxes():
            a=(lo-points)/direction
            b=(hi-points)/direction
            inside = (points >= lo) & (points <= hi)
            parallel = np.abs(direction) < 1e-10
            near = np.where(parallel, np.where(inside,-np.inf,np.inf), np.minimum(a,b)).max(axis=1)
            far = np.where(parallel, np.where(inside,np.inf,-np.inf), np.maximum(a,b)).min(axis=1)
            hit |= (far >= np.maximum(near, 0)) & (near < max_t)
    return hit


def step_edges(rgb, invproj, invview, camera, light):
    # Straight upper east rims cast an edge onto y=63. Sample the middle of
    # each tread, clear of risers, fence geometry and the camera silhouette.
    if -light[0] / light[1] < .3:
        return []
    out=[]
    for i in range(3):
        x_edge=133-(i+1)*light[0]/light[1]
        if x_edge+.22 >= 138:
            continue
        x_offset=np.linspace(-.22,.22,441)
        rows=[]
        locations=[]
        for z in np.linspace(341.25+i,341.75+i,31):
            pts=np.column_stack((x_edge+x_offset, np.full(441,63.0001), np.full(441,z)))
            if blocked(pts,camera+invview[:3,3]-pts,1).any():
                continue
            # Omit scanlines crossed by the separate fence shadow.
            if not blocked(pts[:1],light)[0] or blocked(pts[-1:],light)[0]:
                continue
            clip=np.column_stack((pts-camera,np.ones(441)))@np.linalg.inv(invview).T@np.linalg.inv(invproj).T
            uv=clip[:,:2]/clip[:,3:]*.5+.5
            pixels=rgb[(rgb.shape[0]-1-(uv[:,1]*rgb.shape[0]).astype(int)),(uv[:,0]*rgb.shape[1]).astype(int)]
            if np.any(np.abs(pixels[:,2]/255-light[1]) > .012):
                continue
            v=pixels[:,1].astype(float)/255
            crossings=np.where((v[:-1]<.5)&(v[1:]>=.5))[0]
            if len(crossings)!=1 or v[0]>.1 or v[-1]<.9:
                continue
            j=crossings[0]
            rows.append(float(x_offset[j]+(.5-v[j])/(v[j+1]-v[j])*.001))
            locations.append(float(z))
        if rows:
            out.append(dict(stepHeightMetres=i+1,lines=len(rows),medianSignedMetres=float(np.median(rows)),
                            p90AbsoluteMetres=float(np.percentile(np.abs(rows),90)), scanlines=list(zip(locations,rows))))
    return out


def measure(path):
    rgb = np.array(Image.open(path).convert("RGB"))
    invproj, invview, camera, sun, light, view, proj = header(rgb)
    height,width=rgb.shape[:2]
    xx,zz = np.meshgrid(np.arange(130.005,138,.01),np.arange(340.005,345,.01))
    points=np.stack([xx.ravel(),np.full(xx.size,63.0001),zz.ravel()],axis=1)
    eye=camera+invview[:3,3]
    if np.linalg.norm(eye-[134,67.62,335])>.06:
        raise ValueError("Effective eye differs from the fixed camera")
    p4=np.column_stack([points-camera,np.ones(len(points))])
    clip=p4 @ np.linalg.inv(invview).T @ np.linalg.inv(invproj).T
    uv=clip[:,:2]/clip[:,3:]*.5+.5
    visible=(clip[:,3]>0)&(uv>0).all(axis=1)&(uv<1).all(axis=1)&~blocked(points,eye-points,1)
    px=np.clip(np.floor(uv[:,0]*width).astype(int),0,width-1)
    py=np.clip(height-1-np.floor(uv[:,1]*height).astype(int),0,height-1)
    colors=rgb[py,px]
    visible &= abs(colors[:,2].astype(float)/255-max(0,sun[1])) < .012
    if visible.sum()<1000:
        raise ValueError("Ground normal or camera projection did not match")
    if not (np.abs(sun-light)<.015).all():
        raise ValueError("Solar direction differs materially from shadow-light direction")
    # A 6 cm exclusion around silhouettes separates the fully lit/blocked
    # interiors from finite shadow-map resolution and deliberate filtering.
    rays=[blocked(points+np.array([dx,0,dz]),light) for dx in (-.06,0,.06) for dz in (-.06,0,.06)]
    dark=np.logical_and.reduce(rays)&visible
    lit=~np.logical_or.reduce(rays)&visible
    v=colors[:,1]/255.
    def stats(mask):
        a=v[mask]
        return dict(samples=len(a),meanVisibility=float(a.mean()),fractionLit=float((a>.9).mean()),
                    fractionDark=float((a<.1).mean())) if len(a) else dict(samples=0)
    local=points-camera
    outcome,ct=np.unique(colors[visible,0],return_counts=True)
    return dict(gridMetres=.01,marginMetres=.06,eye=eye.tolist(),sun=sun.tolist(),shadowLight=light.tolist(),
                shadowView=view.tolist(), shadowProjection=proj.tolist(), visibleSamples=int(visible.sum()),
                pathByteCounts={str(k):int(n) for k,n in zip(outcome,ct)}, expectedLit=stats(lit),
                expectedBlocked=stats(dark), unoccludedNearSteps=stats(lit&(local[:,0]<0)),
                nearContactShadow=stats(dark&(points[:,0]>133)&(points[:,0]<133.35)),
                stepEdges=step_edges(rgb,invproj,invview,camera,light))


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("png",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    result=measure(args.png)
    with args.output.open("x") as stream:
        json.dump(result,stream,indent=2)
    print({k:v for k,v in result.items() if k not in ("shadowView","shadowProjection")})
