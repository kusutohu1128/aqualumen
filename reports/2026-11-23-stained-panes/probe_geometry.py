"""Exercise all pane connection masks against disjoint boxes from the pinned game models."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from zipfile import ZipFile
import numpy as np
from score import HERE, ROOT, WORK, rectangles

WORK = WORK / "geometry"
WORK.mkdir(parents=True,exist_ok=True)
PACK = ROOT / "dist/Aqualumen-Stained-Panes.zip"
DYES = "white orange magenta light_blue yellow lime pink gray light_gray cyan purple blue brown green red black".split()
SIDES = ("west","east","north","south")


def prepare():
    with ZipFile(PACK) as z:
        (WORK/"pane.glsl").write_bytes(z.read("shaders/lib/pane_transmission.glsl"))
        props=z.read("shaders/block.properties").decode()
    entries={}
    for k,v in re.findall(r"^block\.(11[0-9]{3})\s*=\s*(minecraft:\S+)",props,re.M):
        cells=v.split(":")
        entries[int(k)] = (cells[1],dict(q.split("=") for q in cells[2:]))
    for mask in range(16):
        for dye,name in enumerate(DYES):
            assert entries[11000+mask*16+dye]==(name+"_stained_glass_pane",state(mask))
    old=(HERE.parent/"2026-11-23-torch-open-volume/cache_probe.cpp").read_text()
    (WORK/"egl_probe_context.h").write_text(old[:old.index("static int linear")])
    (WORK/"probe.csh").write_text("""#version 430 compatibility
vec3 lampGlass(int dye) {return vec3(1);}
#include "/pane.glsl"
layout(local_size_x=64) in;
layout(std430,binding=0) readonly buffer Input { vec4 entries[]; };
layout(std430,binding=1) writeonly buffer Output { float paths[]; };
void main() {
    uint id=gl_GlobalInvocationID.x;
    if(id>=paths.length()) return;
    vec4 a=entries[2*id], b=entries[2*id+1];
    paths[id]=paneDistance(int(b.w),a.xz,b.xz-a.xz,distance(a.xyz,b.xyz));
}
""")
    flags=subprocess.check_output(["pkg-config","--cflags","--libs","epoxy","egl"],text=True).split()
    subprocess.run(["g++","-O1","-ffunction-sections","-fdata-sections","-Wl,--gc-sections","-std=c++17",
                    "-I",WORK,"-I",HERE.parent/"2026-11-23-torch-open-volume",HERE/"pane_probe.cpp","-o",WORK/"probe",*flags],check=True)

def state(mask):
    return {side:str(bool(mask&(1<<i))).lower() for i,side in enumerate(SIDES)}

def fixture():
    rng=np.random.default_rng(20261123)
    points=[]
    for x in (0.,7/16, .5,9/16,1.):
        for z in (0.,7/16, .5,9/16,1.):
            a=[x,0.,z]
            for b in ([x,1.,z],[1-x,1.,z],[x,1.,1-z],[1-z,1.,1-x]):
                points.append((a,b))
                points.append((b,a))
    fixed=np.array(points)
    rays=np.concatenate([fixed,rng.random((768,2,3))]).astype(np.float32)
    delta=rays[:,1].astype(float)-rays[:,0];length=np.linalg.norm(delta,axis=1)
    output=[]; ref=[]
    for mask in range(16):
        s=state(mask)
        tag="red_stained_glass_pane["+",".join(k+"="+v for k,v in s.items())+"]"
        boxes=rectangles([(0,0,tag)])
        paths=np.zeros(len(rays))
        for x,y,z,X,Y,Z,dye in boxes:
            lo=np.zeros(len(rays));hi=np.ones(len(rays))
            for axis,lower,upper in [(0,x,X),(2,z,Z)]:
                origin=rays[:,0,axis].astype(float); d=delta[:,axis]; parallel=d==0
                valid=(origin>=lower)&(origin<upper)
                den=np.where(parallel,1,d)
                a=(lower-origin)/den;b=(upper-origin)/den
                lo=np.maximum(lo,np.where(parallel,np.where(valid,0,1),np.minimum(a,b)))
                hi=np.minimum(hi,np.where(parallel,np.where(valid,1,0),np.maximum(a,b)))
            paths+=np.maximum(0.,hi-lo)*length
        ref.append(paths)
        entry=np.zeros((len(rays),2,4),np.float32);entry[:,:,:3]=rays;entry[:,1,3]=mask
        output.append(entry)
    np.array(output).tofile(WORK/"rays.bin")
    return np.concatenate(ref)

def check(vendor, trace):
    reference=fixture(); meta={}
    output=WORK/(vendor+".bin")
    env=os.environ.copy()
    env["__EGL_VENDOR_LIBRARY_FILENAMES"]="/usr/share/glvnd/egl_vendor.d/"+("50_mesa.json" if vendor=="mesa" else "10_nvidia.json")
    if vendor=="mesa":
        env.update(LIBGL_ALWAYS_SOFTWARE="1",GALLIUM_DRIVER="llvmpipe",LP_NUM_THREADS="2")
    cmd=[WORK/"probe",WORK,WORK/"rays.bin",output]
    if trace:
        recording=WORK/(vendor+".trace")
        cmd=["apitrace","trace","--api","egl","--output",recording,*cmd]
    renderer=subprocess.check_output(cmd,env=env,text=True).strip()
    gpu=np.fromfile(output,np.float32)
    assert gpu.shape==reference.shape
    error=abs(gpu-reference)
    assert np.max(error)<2e-5 and (("llvmpipe" if vendor=="mesa" else "3080 Ti") in renderer), (renderer,error.max())
    if trace:
        dump=subprocess.check_output(["apitrace","dump","--grep=glDispatchCompute|glGetBufferSubData",recording],text=True)
        assert "glDispatchCompute(" in dump and "glGetBufferSubData(" in dump
        meta["apitraceCalls"]=dump.strip().splitlines()
    meta.update(renderer=renderer,rays=len(reference),connectionMasks=16,checkedBlockStates=256,
                packSha256=hashlib.sha256(PACK.read_bytes()).hexdigest(),maxDistanceError=float(np.max(error)),
                meanDistanceError=float(np.mean(error)),outputSha256=hashlib.sha256(output.read_bytes()).hexdigest())
    (HERE/("geometry-"+vendor+".json")).write_text(json.dumps(meta,indent=2)+"\n")
    print(renderer, len(reference), error.max())

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("action",choices=("prepare","mesa","nvidia"))
    ap.add_argument("--trace",action="store_true")
    a=ap.parse_args()
    if a.action=="prepare":prepare()
    else:check(a.action,a.trace)
