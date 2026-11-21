"""Compare reprojected opaque surfaces beside the saved soul torch in ordinary survival frames."""
from functools import lru_cache
from pathlib import Path
import json,sys,math
import numpy as np
from PIL import Image
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parents[2]/'reports/2026-11-21-rain-eaves/fixture'))
from anvil import World
r=here/'reopen-and-relight'
complete=json.loads((r/'complete.json').read_text())
grid=World(Path(json.loads((r/'identity.json').read_text())['world']))
@lru_cache(maxsize=100000)
def name(cell):
    return (grid.block(*cell) or 'unavailable').split('[')[0].split(':')[-1]
air={'air','cave_air','torch','soul_torch'}
def first(eye,delta,reach):
    cell=np.floor(eye).astype(int); step=np.sign(delta).astype(int)
    inv=np.divide(1,np.abs(delta),out=np.full(3,np.inf),where=np.abs(delta)>1e-9)
    next_t=(np.where(step>0,cell+1-eye,eye-cell))*inv
    t=0.;normal=np.zeros(3)
    for _ in range(80):
        c=tuple(int(v) for v in cell);b=name(c)
        if b not in air:return c,b,normal,eye+delta*t
        axis=np.argmin(next_t);t=next_t[axis]
        if t>reach:break
        cell[axis]+=step[axis];next_t[axis]+=inv[axis]
        normal=np.zeros(3);normal[axis]=-step[axis]
    return None
def norm(v):return v/np.linalg.norm(v)
h,w=900,1600
scale=math.tan(math.radians(35))*2/h
cam={};photos={}
for k in ('reopened','both-off','restored'):
    o=complete['results'][k]['obs']
    eye=np.array(o['xyz'])+[0,1.62,0]; yaw,pitch=np.radians(o['angle'])
    fw=np.array([-np.sin(yaw)*np.cos(pitch),-np.sin(pitch),np.cos(yaw)*np.cos(pitch)])
    right=norm(np.cross(fw,[0,1,0])); up=np.cross(right,fw)
    cam[k]=(eye,fw,right,up)
    photos[k]=np.asarray(Image.open(r/complete['results'][k]['images'][1]).convert('RGB'))
lamp=np.array([565.5,64.64,425.5]); eye,fw,right,up=cam['reopened']
offers={}
for py in range(90,766,15):
    for px in range(65,1515,15):
        if px>1000 and py>605:continue  # player's foreground hand
        ray=norm(fw+(px+.5-w/2)*scale*right+(h/2-py-.5)*scale*up)
        hit=first(eye,ray,18)
        if hit is None:continue
        c,b,n,point=hit
        kind='trunk' if b.endswith('_log') else 'grass' if b=='grass_block' and n[1]>.9 else None
        if not kind:continue
        to=lamp-point;d=np.linalg.norm(to)
        if d<.5 or d>6.5 or np.dot(n,to/d)<.2: continue
        inside=(point-n*.001)-np.floor(point-n*.001)
        tangent=np.abs(n)<.1
        if min(inside[tangent].min(),(1-inside[tangent]).min())<.13:continue
        if first(point+.015*n,norm(lamp-(point+.015*n)),np.linalg.norm(lamp-(point+.015*n))-.04) is not None:continue
        obs={};valid=True
        for label,(a,v,vr,vu) in cam.items():
            delta=point-a; f=np.dot(v,delta)
            x=round(w/2-.5+np.dot(vr,delta)/f/scale);y=round(h/2-.5-np.dot(vu,delta)/f/scale)
            h2=first(a,norm(delta),np.linalg.norm(delta)+.03)
            if h2 is None or h2[0]!=c or not np.allclose(h2[2],n) or not (4<x<w-4 and 4<y<h-4):
                valid=False;break
            obs[label]={'xy':[x,y],'medianDisplayRGB':np.median(photos[label][y-2:y+3,x-2:x+3],axis=(0,1)).astype(int).tolist()}
        if not valid:continue
        score=np.dot(n,to/d)/(d*d)
        if kind not in offers or score>offers[kind][0]:
            offers[kind]=(score,dict(cell=[int(v) for v in c],block=b,point=point.round(3).tolist(),normal=n.tolist(),lampDistance=round(d,3),observations=obs))
out={'note':'Selection uses saved opaque geometry and cosine/distance squared for the strongest open light path. Ordinary world time advances and camera positions differ. Medians of 5 x 5 display pixels, not radiance. Any intermediate leaf, glass, plant or unavailable cell excludes a ray.',
     'worldTimeAtEnd':complete['savedLevel']['DayTime'],'patches':{k:v[1] for k,v in offers.items()}}
(r/'relight-patches.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out['patches']))
