"""Compare calibrated screen readings on the rear wall to model-derived geometry."""
import ctypes
import importlib.util
import json
from pathlib import Path
import sys
from zipfile import ZipFile
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORK=ROOT/"build/stained-panes"
def load():
    # The historic reader imports a sibling named pack.
    old=HERE.parent/"2026-11-23-placed-penumbra"
    sys.path.insert(0,str(old))
    spec=importlib.util.spec_from_file_location("placed_visibility_score",old/"score.py")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod
reader=load()
JAR=Path.home()/".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/libraries/com/mojang/minecraft/1.21.1/minecraft-1.21.1-client.jar"

def rectangles(columns):
    with ZipFile(JAR) as jar:
        def get(p):return json.loads(jar.read("assets/minecraft/"+p+".json"))
        result=[]
        for x,z,tag in columns:
            name=tag.split("[")[0]
            dye=int(name.startswith("blue"))
            if not name.endswith("pane"):
                result.append([x,151,z,x+1,153,z+1,dye]);continue
            states=dict(i.split("=") for i in tag.split("[")[1][:-1].split(","))
            for part in get("blockstates/"+name)["multipart"]:
                # The 'noside' pieces only close the visible faces of the post.
                model=part["apply"]["model"].split(":")[1]
                if "noside" in model or any(states[k]!=v for k,v in part.get("when",{}).items()):continue
                parent=get("models/"+model)["parent"].split(":")[-1]
                elem=get("models/"+parent)["elements"][0]
                pts=np.array([elem["from"],elem["to"]],float)/16-.5
                for _ in range(part["apply"].get("y",0)//90):
                    pts[:,[0,2]]=np.stack([-pts[:,2],pts[:,0]],axis=1)
                lo=pts.min(axis=0)+.5;hi=pts.max(axis=0)+.5
                result.append([x+lo[0],151,z+lo[2],x+hi[0],153,z+hi[2],dye])
    return np.ascontiguousarray(result,np.float64).reshape(-1,7)

def metrics(arr):
    if not arr.size:return {"count":0}
    return dict(count=len(arr),mean=float(arr.mean()),p95=float(np.quantile(arr,.95)),p99=float(np.quantile(arr,.99)),maximum=float(arr.max()))

def analyze(label):
    folder=HERE/label
    geo=json.loads((folder/"geometry.json").read_text())
    receipt=json.loads((folder/"complete.json").read_text());rows={}
    ray=ctypes.CDLL(str(WORK/"reference.so")).integrate
    ray.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p]
    for stage in receipt["stages"]:
        photo=folder/(stage+"-ingame.png")
        digest=reader.check_record(folder,photo)
        lamps,p,_=reader.unpack(photo,1)
        active=lamps[:,:,2,0]==1
        wall=(abs(p[:,:,2]+412)<.0005)&(p[:,:,0]>404.04)&(p[:,:,0]<409.96)&(p[:,:,1]>151.04)&(p[:,:,1]<154.96)
        wall&=(reader.face_from_geometry(p,np.array([409.48,152.62,-405.95]))==6)&active
        pflat=np.ascontiguousarray(p[wall][::4]);rgb=lamps[:,:,0][wall][::4].astype(float)
        b=rectangles(geo["columns"][stage]);ref=np.empty_like(pflat)
        ray(len(ref),pflat.ctypes.data,len(b),b.ctypes.data,1536,ref.ctypes.data)
        delta=abs(rgb-ref*255).max(axis=1)
        colored=ref.min(axis=1)<.985
        clear=ref.min(axis=1)>.99999
        words=lamps[:,:,1][wall].astype(np.int32)@np.array([1,256,65536]);values,counts=np.unique(words,return_counts=True)
        rows[stage]=dict(receivers=len(delta),tinted=int(colored.sum()),allErrorsBytes=metrics(delta),
                         tintedErrorsBytes=metrics(delta[colored]),clearErrorsBytes=metrics(delta[clear]),
                         meanObservedRGB=rgb.mean(axis=0).tolist(),meanReferenceRGB=(255*ref.mean(axis=0)).tolist(),
                         centreField={str(k):int(n) for k,n in zip(values,counts)})
    (HERE/(label+"-score.json")).write_text(json.dumps(dict(pack=digest,stages=rows),indent=2)+"\n")
    for s,r in rows.items():print(s,r["receivers"],r["tinted"],round(r["allErrorsBytes"]["mean"],2),r["tintedErrorsBytes"].get("p95"),r["clearErrorsBytes"].get("maximum"),r["centreField"])
if __name__=="__main__":analyze(sys.argv[1])
