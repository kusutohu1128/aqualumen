"""Compare the packaged 24-tap box integration with individual model boxes on both GL drivers."""
import json
import os
import subprocess
import sys
from zipfile import ZipFile
import numpy as np
from window_room import HERE, ROOT, PREV, LAYOUT, PACKS, guarded
from glass_room import state
from score import rectangles

WORK = ROOT / "build/pane-beam/probe"
STAGES = ["post","red-ew","red-ns","corner","two-colours","split","opaque-edge","blue-ew"]
DYES = {"red":14,"blue":11}
COLOURS = np.array([[.85,.20,.16],[.19,.36,.86]])
# Map the existing glass-room models to a small light-field grid.
SHIFT = np.array([376.,121.,-440.])

def material_word(tag):
    if tag=="stone": return 1
    arms=sum(1<<i for i,side in enumerate(("west","east","north","south")) if side+"=true" in tag)
    return (arms<<6) + 32 + DYES[tag.split("_")[0]]

def prepare():
    WORK.mkdir(parents=True,exist_ok=True)
    name,digest=PACKS["candidate"]
    pack=ROOT/"dist"/f"Aqualumen-{name}.zip"
    assert guarded.sha(pack)==digest
    with ZipFile(pack) as z:
        def library(name): return z.read("shaders/lib/"+name+".glsl").decode()
        leaf=library("leaf_disk")
        geometry=leaf[leaf.index("bool leafConeTouches"):leaf.index("// Only take the single-block")]
        geometry+=leaf[leaf.index("vec2 leafDiskPoint"):leaf.index("vec3 singleLeafDisk")]
        shading=library("local_lighting")
        dye=shading[shading.index("vec3 lampGlass"):shading.index('#include "/lib/pane_transmission')]
        core=library("pane_beam")
        pane=library("pane_transmission")
    cases=[]
    for i,stage in enumerate(STAGES):
        rows=["if(scene=="+str(i)+") {"]
        for x,z in LAYOUT[stage]:
            tag=state(LAYOUT[stage],x,z)
            rows.append(f"if(c.x=={x-376} && c.z=={z+440} && c.y>=30 && c.y<32) return {material_word(tag)};")
        cases+=rows+["}"]
    preamble="""#version 430 compatibility
int scene;
int field(ivec3 c) {
"""+'\n'.join(cases)+"""
    return 0;
}
#define texelFetch(table,cell,lod) vec4(field(cell))
#define lampCellAddress(c) (c)
bool lampInGrid(ivec3 c) {return all(greaterThanEqual(c,ivec3(0))) && all(lessThan(c,ivec3(64)));}
"""
    main="""
layout(local_size_x=64) in;
layout(std430,binding=0) readonly buffer Input { vec4 entries[]; };
layout(std430,binding=1) writeonly buffer Output { float outputValues[]; };
void main() {
    uint id=gl_GlobalInvocationID.x;
    if(id>=outputValues.length()) return;
    vec4 a=entries[2*id], b=entries[2*id+1];
    int channel=int(a.w)%3;
    scene=int(a.w)/6;
    bool carried=((int(a.w)/3)&1)!=0;
    vec3 l=normalize(b.xyz-a.xyz);
    vec3 u=normalize(cross(l,abs(l.y)<.9 ? vec3(0,1,0):vec3(1,0,0)))*b.w;
    vec3 v=cross(l,u), lo,hi,dye;
    outputValues[id]=findPaneBox(a.xyz,b.xyz,u,v,carried,lo,hi,dye)
        ? samplePaneBox(b.xyz-a.xyz,u,v,lo,hi,dye)[channel] : -1.;
}
"""
    (WORK/"probe.csh").write_text(preamble+dye+pane+geometry+core+main)

def distance(a,d,box):
    lo=np.zeros(d.shape[:-1]); hi=np.ones_like(lo)
    for k in range(3):
        origin=a[:,None,k]
        speed=d[:,:,k]
        parallel=abs(speed)<1.e-9; den=np.where(parallel,1,speed)
        near=(box[k]-origin)/den;far=(box[k+3]-origin)/den
        inside=(box[k]<=origin)&(origin<box[k+3])
        lo=np.maximum(lo,np.where(parallel,np.where(inside,0,1),np.minimum(near,far)))
        hi=np.minimum(hi,np.where(parallel,np.where(inside,1,0),np.maximum(near,far)))
    return np.maximum(0,hi-lo)*np.linalg.norm(d,axis=2)

def expected(a,b,radii,stage):
    l=b-a
    l/=np.linalg.norm(l,axis=1)[:,None]
    axis=np.tile([0.,1.,0.],(len(l),1)); axis[abs(l[:,1])>=.9]=[1.,0.,0.]
    u=np.cross(l,axis); u/=np.linalg.norm(u,axis=1)[:,None]
    u*=radii[:,None];v=np.cross(l,u)
    i=np.arange(24); angle=i*2.39996323+.417; r=np.sqrt((i+.5)/24)
    d=(b-a)[:,None,:]+u[:,None,:]*(r*np.cos(angle))[None,:,None]+v[:,None,:]*(r*np.sin(angle))[None,:,None]
    throughput=np.ones(d.shape)
    for x,z in LAYOUT[stage]:
        tag=state(LAYOUT[stage],x,z)
        for box in rectangles([(x,z,tag)]):
            box[:3]-=SHIFT; box[3:6]-=SHIFT
            length=distance(a,d,box)
            if tag=="stone": throughput*=np.where(length>1.e-8,0.,1.)[:,:,None]
            else: throughput*=COLOURS[int(box[-1])][None,None,:]**length[:,:,None]
    return throughput.mean(axis=1)

def check():
    prepare()
    rng=np.random.default_rng(419)
    a=rng.uniform([27,29,26],[34,34,28],(320,3)).astype("f")
    b=rng.uniform([28.5,30,32.2],[32.5,33,34.5],a.shape).astype("f")
    # Include beams directed back through the stack, and a camera exactly beside
    # a pane edge. Starting on the plane exercises its half-open ownership.
    a=np.concatenate([a,b,np.array([[30.4375,30.5,30.3],[30.5625,30.5,30.6]],dtype="f")])
    b=np.concatenate([b,a[:320],np.array([[30.4375,31.,33.5],[30.5625,31.,33.5]],dtype="f")])
    radii=rng.choice([.13,.18,.22],len(a)).astype("f")
    inputs=[]; refs=[]
    for i,stage in enumerate(STAGES):
        refs.append(expected(a.astype(float),b.astype(float),radii.astype(float),stage))
        for carried in range(2):
            for channel in range(3):
                data=np.zeros((len(a),2,4),dtype="f")
                data[:,0,:3]=a;data[:,1,:3]=b;data[:,0,3]=i*6+carried*3+channel;data[:,1,3]=radii
                inputs.append(data)
    np.concatenate(inputs).tofile(WORK/"rays.bin")
    results={}
    for vendor in ("mesa","nvidia"):
        env=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES="/usr/share/glvnd/egl_vendor.d/"+("50_mesa.json" if vendor=="mesa" else "10_nvidia.json"))
        if vendor=="mesa": env.update(LIBGL_ALWAYS_SOFTWARE="1",GALLIUM_DRIVER="llvmpipe",LP_NUM_THREADS="2")
        out=WORK/(vendor+".bin")
        exe=ROOT/"build/stained-panes/geometry/probe"
        if not exe.exists():
            from probe_geometry import prepare as build_probe
            build_probe()
        renderer=subprocess.check_output([exe,WORK,WORK/"rays.bin",out],text=True,env=env)
        assert ("RTX 3080 Ti" if vendor=="nvidia" else "llvmpipe") in renderer
        actual=np.fromfile(out,"f").reshape(len(STAGES),2,3,len(a)).transpose(0,1,3,2)
        rows={}
        for idx,stage in enumerate(STAGES):
            valid=actual[idx,:,:,0]>=0
            assert np.array_equal((actual[idx]>=0),np.repeat(valid[:,:,None],3,axis=2))
            ref=np.broadcast_to(refs[idx],actual[idx].shape)
            errors=np.abs(actual[idx]-ref)[valid]
            rows[stage]=dict(accepted=int(valid.sum()),examined=valid.size,
                             maxError=float(errors.max()) if errors.size else None,
                             carriedAccepted=int(valid[1].sum()))
            if errors.size: assert errors.max()<.00025,(vendor,stage,rows[stage])
        assert rows["red-ew"]["carriedAccepted"]>100
        results[vendor]=dict(renderer=renderer.strip(),stages=rows)
    (HERE/"synthetic.json").write_text(json.dumps(results,indent=2)+"\n")

if __name__=="__main__": check()
