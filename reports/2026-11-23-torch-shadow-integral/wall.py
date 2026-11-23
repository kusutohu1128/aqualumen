"""Measure the existing grove's actual torch, blocks and receiver wall at grazing angles."""
import ctypes as ct
import json
import os
import subprocess
import numpy as np
from integral import HERE, WORK, OLD, VENDORS


def points():
    lamp=np.array([405.5,151.64,-407.5])
    # The wall is at z=-412 and shader rays start 2.5 cm in front of it.
    # Its centre line, the shared vertical block edge and the torch align
    # when receiver x=409.975. Include immediately neighbouring float32s.
    spacing=np.spacing(np.float32(25.975))
    dx=np.r_[[-.05,-.02,-.01,-.005],np.arange(-32,33)*spacing,[.005,.01,.02,.05]]
    y=np.linspace(151.01,154.99,512)
    x,y=np.meshgrid(409.975+dx,y)
    p=np.column_stack([x.ravel(),y.ravel(),np.full(x.size,-412.)])
    # The real shader uses grid-relative coordinates. Reproduce float32
    # subtraction and receiver offset in the same coordinate system.
    anchor=np.array([384,128,-432],np.float32)
    pos=(p-anchor).astype(np.float32)
    start=pos+np.array([0,0,.025],np.float32)
    src=(lamp-anchor).astype(np.float32)
    axis=src-pos
    axis/=np.linalg.norm(axis,axis=1)[:,None]
    pole=np.eye(3,dtype=np.float32)[(abs(axis[:,1])<.9).astype(int)]
    u=np.cross(axis,pole)
    u*=.13/np.linalg.norm(u,axis=1)[:,None]
    boxes=np.array([[406,151,-410],[407,153,-409],[407,151,-409],[408,152,-408]],np.float32)-anchor
    rows=np.zeros((len(p),7,4),np.float32)
    rows[:,:4,:3]=boxes[None,:,:]-start[:,None,:]
    rows[:,4,:3]=src-start
    rows[:,5,:3]=u
    rows[:,6,:3]=np.cross(axis,u)
    return p,rows


def test():
    p,rows=points()
    inp=WORK/"wall.f32"
    rows.tofile(inp)
    fn=ct.CDLL(str(OLD/"footprint.so")).pairArea
    fn.argtypes=[ct.c_int,ct.c_void_p,ct.c_void_p]
    fn.restype=None
    ref=np.empty(len(rows),np.float64)
    fn(len(rows),rows.ctypes.data,ref.ctypes.data)
    report={}
    for variant in ("polygon","chords"):
        report[variant]={}
        for vendor,renderer in VENDORS.items():
            dst=WORK/("wall-"+vendor+"-"+variant+".f32")
            env=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES="/usr/share/glvnd/egl_vendor.d/"+vendor+".json")
            log=subprocess.check_output(["flock","/tmp/aql-render21-1000.lock",OLD/"evaluate",WORK/(variant+".csh"),inp,dst],env=env,text=True)
            assert renderer in log
            out=np.fromfile(dst,np.float32)
            assert np.isfinite(out).all()
            e=abs(out-ref)
            k=int(e.argmax())
            report[variant][vendor]=dict(count=len(p),overTwo=int((e>2/255).sum()),worst=int(k),position=p[k].tolist(),
                max=float(e[k]),reference=float(ref[k]),value=float(out[k]))
    (HERE/"grove-wall.json").write_text(json.dumps(report,indent=2)+"\n")
    print(report)


if __name__=="__main__":test()
