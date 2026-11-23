"""Measure finite-source visibility on recorded land surfaces and near-degenerate box pairs."""
import ctypes as ct
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = ROOT / "build/torch-shadow-integral"
OLD = ROOT / "build/mixed-occluders"
PRIOR = HERE.parent / "2026-11-23-mixed-occluders"
NORMAL = ROOT / "dist/Aqualumen-Placed-Torch-Shadows.zip"
METER = OLD / "Aqualumen-Two-Opaque-Shadows-Polygon-Meter.zip"
VENDORS = {"10_nvidia":"RTX 3080 Ti", "50_mesa":"llvmpipe"}


def replace_solver(text, variant):
    if variant=="single":
        from edges import direct
        end="// The two masks"
        return direct(text,HERE).split(end,1)[0]+end+text.split(end,1)[1]
    if variant=="mask":
        from edges import mask
        return mask(text,HERE)
    if variant=="caps":
        from edges import caps
        return caps(text,HERE)
    if variant=="direct":
        from edges import direct
        return direct(text,HERE)
    if variant in ("chords","stable"):
        start=text.index("float boxSourceVisibility(")
        end=text.find("// The two masks",start)
        if end<0:
            end=text.index("bool rayEntersSolid(",start)
        shared=(HERE/"chords.glsl").read_text()
        if variant=="stable":
            shared=shared.replace("rimClip(base,dot(h.xy,tangent),span);",
                "rimClip(base,dot(sum2<2.?sumNormal:-diff,tangent),span);")
            shared=shared.replace("    float area=0.;",
                "    if(limit==first+1) return (acos(smallest)-smallest*sqrt(max(0.,(1.-smallest)*(1.+smallest))))/3.141592654;\n    float area=0.;")
        text=text[:start]+shared+"\n"+text[end:]
        start=text.index("void diskPlane(")
        end=text.find("// Only needed",start)
        if end<0:
            end=text.index("layout(local_size_x=",start)
        return (text[:start]+(HERE/"pair.glsl").read_text()+"\n"+text[end:]).replace("shadowPlanes(","boxPlanes(")
    start = text.index("float diskEdge(")
    end = text.index("float oneBlocker(", start)
    return text[:start] + (HERE / (variant+".glsl")).read_text() + "\n" + text[end:]


def build(variant, meter=False):
    original = METER if meter else NORMAL
    assert sha256(original.read_bytes()).hexdigest() == ("9520af30e588c9fb4cfa08ed6d83c5fba6c2c8fa28e606868f78678a758ed025"
        if meter else "9d2d40e8ea3e70dcc5709b21288bfe0e35c313cf112f755356c3c433452144e1")
    output = WORK / ("Aqualumen-Torch-" + variant + ("-meter" if meter else "") + ".zip")
    with ZipFile(original) as src, ZipFile(output,"w") as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename == "shaders/lib/local_lighting.glsl":
                data = replace_solver(data.decode(),variant).encode()
            dst.writestr(info,data)
    return output,sha256(output.read_bytes()).hexdigest()


def additional():
    # Axis-aligned full blocks share a face or an edge. Put the observer on,
    # or a few floating-point ulps around, a plane containing that edge.
    # The disk can likewise straddle an edge, a face, or an open corner.
    rng = np.random.default_rng(93321)
    count = 60000
    boxes = np.empty((count,4,3))
    boxes[:,0] = [-1,0,-1]
    boxes[:,1] = [0,2,0]
    boxes[:,2] = [0,0,0]
    boxes[:,3] = [1,1,1]
    boxes[::5,2:4,0] -= 1
    boxes[1::5,2:4,0] += 1
    theta = rng.uniform(0,2*np.pi,count)
    theta[::3] = np.pi/4 + (np.arange(len(theta[::3])) % 4)*np.pi/2
    radius = rng.uniform(1.5,9,count)
    eye = np.stack([radius*np.cos(theta),rng.uniform(-.3,3.2,count),radius*np.sin(theta)],axis=1)
    eps = 10**rng.uniform(-8.,-1.2,count) * rng.choice([-1,1],count)
    eye[::7,0] = eps[::7]
    eye[1::7,2] = eps[1::7]
    eye[2::7,1] = 1+eps[2::7]
    t = rng.uniform(.12,.95,count)
    pivot = np.zeros_like(eye)
    pivot[:,1] = rng.uniform(0,2,count)
    pivot[::4,1] = 1.
    pivot[1::4,1] = 0.
    tip = (pivot-eye)/t[:,None]
    tip += rng.normal(size=eye.shape)*eps[:,None]
    axis = tip/np.linalg.norm(tip,axis=1)[:,None]
    pole = np.eye(3)[(abs(axis[:,1])<.9).astype(int)]
    u = np.cross(axis,pole)
    u *= (.13 / np.linalg.norm(u,axis=1))[:,None]
    v = np.cross(axis,u)
    # Rotate the source parametrization and permute world axes.
    angle = rng.uniform(-np.pi,np.pi,count)
    c = np.cos(angle)[:,None]; s = np.sin(angle)[:,None]
    rows = np.zeros((count,7,4),np.float32)
    rows[:,:4,:3] = boxes-eye[:,None,:]
    rows[:,4,:3] = tip
    rows[:,5,:3] = u*c+v*s
    rows[:,6,:3] = v*c-u*s
    for k in (1,2):
        rows[k::3,:,:3] = np.roll(rows[k::3,:,:3],k,axis=-1)
    return rows


def test(variant):
    cases = np.concatenate([np.fromfile(OLD/"with-room.f32",np.float32).reshape(-1,7,4),additional()])
    assert len(cases) == 127599
    inp = WORK / "queries.f32"
    cases.tofile(inp)
    fn = ct.CDLL(str(OLD/"footprint.so")).pairArea
    fn.argtypes = [ct.c_int,ct.c_void_p,ct.c_void_p]
    fn.restype = None
    ref = np.empty(len(cases),np.float64)
    fn(len(cases),cases.ctypes.data,ref.ctypes.data)
    shader = WORK / (variant+".csh")
    original = (OLD/"polygon.csh").read_text()
    shader.write_text(original if variant=="polygon" else replace_solver(original,variant))
    report={}
    for vendor,display in VENDORS.items():
        out = WORK/(variant+"-"+vendor+".f32")
        env=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES="/usr/share/glvnd/egl_vendor.d/"+vendor+".json")
        log=subprocess.check_output(["flock","/tmp/aql-render21-1000.lock",OLD/"evaluate",shader,inp,out],env=env,text=True)
        assert display in log
        val=np.fromfile(out,np.float32)
        assert val.shape==ref.shape and np.isfinite(val).all()
        report[vendor]={"renderer":log.strip(),"groups":{}}
        for group,start,end in (("previous",0,40270),("touching",40270,54009),("diagonal",54009,67599),("nearEdges",67599,len(ref))):
            err=abs(val[start:end]-ref[start:end])
            worst=int(err.argmax()+start)
            report[vendor]["groups"][group]=dict(count=end-start,overTwo=int((err>2/255).sum()),
                overHalf=int((err>.5/255).sum()),mean=float(err.mean()),max=float(err.max()),
                worst=worst,reference=float(ref[worst]),value=float(val[worst]))
    (HERE/(variant+".json")).write_text(json.dumps(report,indent=2)+"\n")
    for vendor, record in report.items():print(vendor,[(k,v["overTwo"],round(v["max"],5)) for k,v in record["groups"].items()])


if __name__=="__main__":
    command,variant=sys.argv[1:]
    if command=="test":test(variant)
    elif command=="build":
        for meter in (False,True):print(*build(variant,meter))
    else:raise ValueError(command)
