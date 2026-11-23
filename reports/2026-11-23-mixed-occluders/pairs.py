"""Exercise the exact two-silhouette solver on recorded Minecraft receivers and synthetic overlaps."""
import ctypes as ct
import json
import os
import subprocess
from zipfile import ZipFile

from attribute import registered_frames
from grid import BASE,HERE,ROOT,WORK
from score import FOREST_ANCHOR,FOREST_SOURCES,integral,np,moments


def boxes(entries):
    points=np.array([b["xyz"] for b in entries])
    for axis in range(3):
        for split in range(points[:,axis].min()+1,points[:,axis].max()+1):
            left=points[:,axis]<split
            parts=[points[left],points[~left]]
            if all(len(x) and np.prod(np.ptp(x,axis=0)+1)==len(x) for x in parts):
                return np.array([[x.min(axis=0),x.max(axis=0)+1] for x in parts]).reshape(4,3)
    return None


def basis(direction):
    direction=direction/np.linalg.norm(direction,axis=1)[:,None]
    poles=np.eye(3)[(abs(direction[:,1])<.9).astype(int)]
    u=np.cross(direction,poles)
    u*=.13/np.linalg.norm(u,axis=1)[:,None]
    return u,np.cross(direction,u)


def forest_queries():
    rows=json.loads((HERE/"forest-census.json").read_text())["rows"]
    base,trial,p,face,axis,cell,grid,registered=registered_frames()
    starts=p+.025*axis
    all_rows=[]; refs=[];previous=[]
    for i,src in enumerate(FOREST_SOURCES):
        a,b=base[:,:,i,2],trial[:,:,i,2]
        mask=registered&(a>=64)&(b>=64)&((a&12)==0)&((b&12)==0)&((b%4)==0)
        ref=integral(p,face,mask,src,FOREST_ANCHOR,grid)
        for row in rows:
            if row["source"]!=i or row["reason"]!="irregularSolids" or len(row["solid"])>12: continue
            rects=boxes(row["solid"])
            if rects is None: continue
            take=(ref>.005)&(ref<.995)&(cell==np.array(row["cell"])-FOREST_ANCHOR).all(axis=2)
            rays=np.zeros((int(take.sum()),7,4),np.float32)
            rays[:,:4,:3]=rects[None,:,:]-starts[take,None,:]
            rays[:,4,:3]=src-starts[take]
            rays[:,5,:3],rays[:,6,:3]=basis(src-p[take])
            all_rows.append(rays);refs.extend(ref[take]);previous.extend(trial[:,:,i,1][take]/255.)
    return np.concatenate(all_rows),np.array(refs),np.array(previous)


def synthetic():
    rng=np.random.default_rng(23579)
    n=12000
    rows=np.zeros((n,7,4),np.float32)
    delta=rng.normal(size=(n,3))
    delta*=rng.uniform(2,12,n)[:,None]/np.linalg.norm(delta,axis=1)[:,None]
    rows[:,4,:3]=delta
    rows[:,5,:3],rows[:,6,:3]=basis(delta)
    # Place each block face close to a ray towards the finite disk. Some
    # overlap on the disk although the blocks have very different depths.
    for start in (0,2):
        t=rng.uniform(.08,1.08,n)
        extent=rng.uniform(.3,2.,(n,3))
        lo=delta*t[:,None]-rng.uniform(0,1,(n,3))*extent
        coord=rng.integers(0,3,n)
        lo[np.arange(n),coord]=(delta*t[:,None])[np.arange(n),coord]-rng.integers(0,2,n)*extent[np.arange(n),coord]+rng.uniform(-.12,.12,n)
        rows[:,start,:3]=lo
        rows[:,start+1,:3]=lo+extent
    # Identical boxes, touching faces, and receiver-coplanar cases.
    rows[::7,2:4]=rows[::7,:2]
    rows[1::7,2,0]=rows[1::7,1,0]
    rows[1::7,3,0]=rows[1::7,2,0]+1.
    rows[2::7,0,0]=0.;rows[2::7,1,0]=1.
    return rows


def prepare():
    with ZipFile(BASE) as pack:
        source=pack.read("shaders/lib/local_lighting.glsl").decode()
    helpers=source[source.index("void rimClip("):source.index("float simpleBrickVisibility(")]
    ray=source[source.index("bool rayEntersSolid("):source.index("vec3 jointDiskSamples(")]
    kernel="""layout(local_size_x=64) in;
layout(std430,binding=0) readonly buffer Queries {vec4 q[];};
layout(std430,binding=1) writeonly buffer Answers {float outValue[];};
void main() {
    int i=int(gl_GlobalInvocationID.x);if(i>=outValue.length()) return;
    int k=7*i;
    vec2 witness;
    outValue[i]=twoBlockers(q[k].xyz,q[k+1].xyz,q[k+2].xyz,q[k+3].xyz,
        q[k+4].xyz,q[k+5].xyz,q[k+6].xyz,vec3(.1301),witness);
}
"""
    (WORK/"pair.csh").write_text("#version 430 compatibility\n"+helpers+ray+(HERE/"two_boxes.glsl").read_text()+kernel)
    fixture=(HERE.parent/"2026-11-23-torch-open-volume/cache_probe.cpp").read_text()
    prefix=fixture[:fixture.index("static GLuint image(")].replace("../../tools/glcheck.cpp",str(ROOT/"tools/glcheck.cpp"))
    (WORK/"evaluate.cpp").write_text(prefix+(HERE/"evaluate.cpp").read_text())
    subprocess.run(["c++","-std=c++17","-O1",str(WORK/"evaluate.cpp"),"-o",str(WORK/"evaluate"),"-lepoxy","-lEGL"],check=True)
    subprocess.run(["c++","-std=c++17","-O3","-fPIC","-shared",str(HERE/"footprint.cpp"),"-o",str(WORK/"footprint.so")],check=True)


def run():
    prepare()
    forest,refs,previous=forest_queries()
    queries=np.concatenate([forest,synthetic()])
    swapped=queries[:,[2,3,0,1,4,5,6],:].copy()
    table=np.concatenate([queries,swapped])
    table.tofile(WORK/"pair-input.f32")
    fn=ct.CDLL(str(WORK/"footprint.so")).pairArea
    fn.argtypes=[ct.c_int,ct.c_void_p,ct.c_void_p]
    exact=np.empty(len(table),np.float64)
    fn(len(table),table.ctypes.data,exact.ctypes.data)
    assert np.max(abs(exact[:len(queries)]-exact[len(queries):]))<1e-8
    stats=dict(realPartialReceivers=len(forest),synthetic=len(queries)-len(forest),
               oldVsIndependentRays=moments(abs(previous-refs)),
               analyticVsIndependentRays=moments(abs(exact[:len(forest)]-refs)),drivers={})
    for vendor in ("10_nvidia","50_mesa"):
        output=WORK/(vendor+"-pair.f32")
        env={**os.environ,"__EGL_VENDOR_LIBRARY_FILENAMES":"/usr/share/glvnd/egl_vendor.d/"+vendor+".json"}
        log=subprocess.check_output(["flock","-x","/tmp/aql-render21-1000.lock",str(WORK/"evaluate"),
            str(WORK/"pair.csh"),str(WORK/"pair-input.f32"),str(output)],env=env,text=True)
        gpu=np.fromfile(output,np.float32)
        assert gpu.shape==exact.shape and np.isfinite(gpu).all()
        err=abs(gpu-exact)
        worst=np.argsort(err)[-4:][::-1]
        stats["drivers"][vendor]=dict(renderer=log.strip(),realError=moments(err[:len(forest)]),
                  allError=moments(err),overTwoBytes=int((err>2/255.).sum()),
                  symmetry=moments(abs(gpu[:len(queries)]-gpu[len(queries):])),
                  worst=[dict(index=int(k),truth=float(exact[k]),gpu=float(gpu[k]),coords=table[k,:,:3].tolist()) for k in worst])
    return stats

if __name__=="__main__":
    (HERE/"two-box-probe.json").write_text(json.dumps(run(),indent=2)+"\n")
