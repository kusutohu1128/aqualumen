"""Look for edge cases reachable by a torch at its Minecraft offset and a flat receiver."""
import ctypes as ct
import json
import os
import subprocess

import numpy as np
from integral import HERE,OLD,WORK,VENDORS


def geometry():
    rng=np.random.default_rng(261123)
    n=240000
    a=np.broadcast_to([0,0,0],(n,3))
    b=np.broadcast_to([1,2,1],(n,3))
    c=np.broadcast_to([1,0,1],(n,3)).copy()
    c[::2,2]=0
    d=c+1
    lampCell=rng.integers([-4,0,-4],[6,4,6],size=(n,3))
    lamp=lampCell+np.array([.5,.64,.5])
    corner=rng.integers([0,0,0],[3,3,3],size=(n,3)).astype(float)
    corner[::2]=[1,1,1]
    corner[1::4,1]=rng.uniform(.1,1.9,len(corner[1::4]))
    ray=corner-lamp
    at=np.arange(n)
    axis=rng.integers(0,3,n)
    sign=np.sign(-ray[at,axis])
    plane=corner[at,axis]+np.sign(ray[at,axis])*rng.integers(1,7,n)
    plane=np.rint(plane)
    scale=(plane+.025*sign-lamp[at,axis])/np.where(ray[at,axis]!=0,ray[at,axis],1.)
    bias=np.eye(3)[axis]*sign[:,None]*.025
    x=lamp+scale[:,None]*ray-bias
    x[at,axis]=plane
    offset=10**rng.uniform(-8,-1,n)*rng.choice([-1,1],n)
    offset[::3]=0.
    x[at,(axis+1)%3]+=offset
    receiver=np.floor(x-bias).astype(int)
    support=lampCell-[0,1,0]
    def inside(cells,lo,hi):
        return ((cells>=lo)&(cells<hi)).all(axis=1)
    keep=(scale>1)&(np.linalg.norm(lamp-x,axis=1)<12)&(sign!=0)
    for lo,hi in ((a,b),(c,d)):
        keep &= ~inside(lampCell,lo,hi)&~inside(receiver,lo,hi)
    keep &= ~np.all(receiver==lampCell,axis=1)&~np.all(receiver==support,axis=1)
    # The floor/wall, and the block supporting the torch, may also intercept
    # the source. Keep the receiver in front and rule out the support even
    # with a conservative radius-sized expansion, unless it is a known blocker.
    start=x+bias
    delta=lamp-start
    with np.errstate(divide="ignore",invalid="ignore"):
        t0=(support-.1301-start)/delta;t1=(support+1.1301-start)/delta
    hit=(np.maximum(0,np.minimum(t0,t1).max(axis=1))<np.minimum(1,np.maximum(t0,t1).min(axis=1)))
    keep &= ~hit|inside(support,a,b)|inside(support,c,d)
    # Match the positive, camera-relative light grid and float32 subtraction.
    origin=np.array([-30,-30,-30],np.float32)
    pos=(x[keep]-origin).astype(np.float32)
    start=pos+bias[keep].astype(np.float32)
    lights=(lamp[keep]-origin).astype(np.float32)
    v=lights-pos
    v/=np.linalg.norm(v,axis=1)[:,None]
    pole=np.eye(3,dtype=np.float32)[(abs(v[:,1])<.9).astype(int)]
    u=np.cross(v,pole)
    u*=.13/np.linalg.norm(u,axis=1)[:,None]
    rows=np.zeros((len(v),7,4),np.float32)
    for i,blocks in enumerate((a,b,c,d)):
        rows[:,i,:3]=(blocks[keep]-origin).astype(np.float32)-start
    rows[:,4,:3]=lights-start
    rows[:,5,:3]=u
    rows[:,6,:3]=np.cross(v,u)
    return rows,np.column_stack([x[keep],lampCell[keep],receiver[keep],c[keep],axis[keep],sign[keep]])


def run():
    rows,detail=geometry()
    path=WORK/"voxel.f32"
    rows.tofile(path)
    fn=ct.CDLL(str(OLD/"footprint.so")).pairArea
    fn.argtypes=[ct.c_int,ct.c_void_p,ct.c_void_p]
    fn.restype=None
    ref=np.empty(len(rows),np.float64)
    fn(len(rows),rows.ctypes.data,ref.ctypes.data)
    out={}
    for variant in ("polygon","caps"):
        out[variant]={}
        for vendor,renderer in VENDORS.items():
            dst=WORK/("voxel-"+variant+"-"+vendor+".f32")
            env=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES="/usr/share/glvnd/egl_vendor.d/"+vendor+".json")
            log=subprocess.check_output(["flock","/tmp/aql-render21-1000.lock",OLD/"evaluate",WORK/(variant+".csh"),path,dst],env=env,text=True)
            assert renderer in log
            values=np.fromfile(dst,np.float32)
            assert values.shape==ref.shape and np.isfinite(values).all()
            e=abs(ref-values)
            w=int(e.argmax())
            out[variant][vendor]=dict(count=len(ref),partial=int(((ref>.005)&(ref<.995)).sum()),overTwo=int((e>2/255).sum()),
                max=float(e[w]),worst=w,reference=float(ref[w]),value=float(values[w]),receiver=detail[w,:3].tolist(),
                torch=detail[w,3:6].tolist(),receiverBlock=detail[w,6:9].tolist(),secondBlock=detail[w,9:12].tolist(),
                normalAxis=int(detail[w,12]),normalSign=int(detail[w,13]),renderer=log.strip())
    (HERE/"voxel-cases.json").write_text(json.dumps(out,indent=2)+"\n")


if __name__=="__main__":run()
