"""Replay actual near-coincident and disjoint step shadows against the independent polygon oracle."""
import ctypes as ct
import json
import os
import subprocess
from build_trial import with_polygon
from pairs import WORK,HERE,basis
from score import ROOM_SOURCE,face_from_geometry,moments,np,unpack


def room_inputs(stage,step):
    tex,p,_=unpack(HERE/"step-meter"/(stage+"-ingame.png"),1)
    f=face_from_geometry(p,np.array([409.48,152.62,-405.95]))
    x,y,z=np.moveaxis(p,-1,0)
    mask=(f==6)&(abs(z+412)<.006)&(x>404)&(x<410)&(y>151)&(y<155)&(tex[:,:,0,2]>=64)
    pos=p[mask];start=pos+[0,0,.025]
    limits=np.array([[406,151,-410],[407,153,-409],step,np.array(step)+1])
    rows=np.zeros((len(pos),7,4),np.float32)
    rows[:,:4,:3]=limits[None,:,:]-start[:,None,:]
    rows[:,4,:3]=ROOM_SOURCE[0]-start
    rows[:,5,:3],rows[:,6,:3]=basis(ROOM_SOURCE[0]-pos)
    return rows

def main():
    shader=WORK/"pair.csh"
    fixed=WORK/"polygon.csh"
    fixed.write_text(with_polygon(shader.read_text()))
    previous=np.fromfile(WORK/"pair-input.f32",np.float32).reshape(-1,7,4)
    touching=room_inputs("touching",[406,151,-409])
    separate=room_inputs("separate",[407,151,-409])
    cases=np.concatenate([previous,touching,separate])
    groups={"replay":slice(0,len(previous)),"touching":slice(len(previous),len(previous)+len(touching)),
            "separate":slice(len(previous)+len(touching),None)}
    input_file=WORK/"with-room.f32";cases.tofile(input_file)
    fn=ct.CDLL(str(WORK/"footprint.so")).pairArea
    fn.argtypes=[ct.c_int,ct.c_void_p,ct.c_void_p]
    exact=np.empty(len(cases),np.float64);fn(len(cases),cases.ctypes.data,exact.ctypes.data)
    report={}
    for vendor in ("10_nvidia","50_mesa"):
        env={**os.environ,"__EGL_VENDOR_LIBRARY_FILENAMES":"/usr/share/glvnd/egl_vendor.d/"+vendor+".json"}
        report[vendor]={}
        for variant in (shader,fixed):
            target=WORK/(vendor+"-"+variant.stem+"-with-room.f32")
            log=subprocess.check_output(["flock","-x","/tmp/aql-render21-1000.lock",str(WORK/"evaluate"),
                        str(variant),str(input_file),str(target)],env=env,text=True)
            values=np.fromfile(target,np.float32)
            assert values.shape==exact.shape and np.isfinite(values).all()
            errs=abs(values-exact)
            report[vendor][variant.stem]=dict(renderer=log.strip(),groups={name:dict(
                error=moments(errs[subset]),overTwoBytes=int((errs[subset]>2/255.).sum())) for name,subset in groups.items()})
    return report

if __name__=="__main__":
    (HERE/"overlap-test.json").write_text(json.dumps(main(),indent=2)+"\n")
