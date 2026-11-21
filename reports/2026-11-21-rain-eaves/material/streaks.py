"""Compare transient rain streak colours above fixed receivers in ordinary game recordings."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import numpy as np

here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"fixture"))
import fixture as patio

def masks(width,height,stride=4):
    pose=patio.POSES["a"]
    x=np.arange(2,width,stride)
    y=np.arange(2,height,stride)
    fields={name:np.zeros((len(y),len(x)),bool) for name in ("wall","stone","smooth","air")}
    for j,yy in enumerate(y):
        for i,xx in enumerate(x):
            ray=patio.ray(pose,xx+.5,yy+.5)
            material,_,pos=patio.first_hit("on",pose["eye"],ray)
            if material==patio.WALL and pos and abs(pos[2]-1)<.002:
                name="wall"
            elif material==patio.STONE:
                name="stone"
            elif material==patio.SMOOTH:
                name="smooth"
            elif material is None and ray[1]>.04:
                name="air"
            else:continue
            fields[name][j,i]=True
    assert min(np.count_nonzero(m) for m in fields.values())>50
    return fields

def intensity(data):
    return .2126*data[...,0]+.7152*data[...,1]+.0722*data[...,2]

def stats(clip,fields):
    raw=subprocess.check_output(["ffmpeg","-v","error","-i",str(clip),"-pix_fmt","rgb24","-f","rawvideo","pipe:1"])
    frames=np.frombuffer(raw,np.uint8).reshape(-1,720,1280,3)[:,2::4,2::4]
    assert len(frames)==32
    group={}
    for name,mask in fields.items():
        rgb=frames[:,mask,:].astype(np.float32)
        base=np.median(rgb,axis=0)
        delta=rgb-base
        lum=intensity(delta)
        # A signed per-channel increment retains dim, blue soul illumination,
        # even when it does not clear a luminance-only threshold.
        events=delta.max(axis=2)>10
        if events.any():
            mean=np.mean(delta[events],axis=0)
        else:
            mean=np.zeros(3)
        group[name]={"pixelsPerFrame":int(mask.sum()),"frames":len(frames),"eventFraction":float(events.mean()),
            "p99PositiveDeltaY8":float(np.quantile(np.maximum(lum,0),.99)),
            "p99NegativeDeltaY8":float(np.quantile(np.maximum(-lum,0),.99)),"eventMeanDeltaRGB8":mean.tolist()}
    return group

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run",type=Path)
    arg=parser.parse_args()
    receipt=json.loads((arg.run/"complete.json").read_text())
    assert not receipt["diagnosticShader"] and receipt["sourceUnchanged"]
    fields=masks(1280,720)
    by_state={}
    for name in ("clear_lamp","warm_rain","lamp_off","soul_rain","lamp_back"):
        clip=arg.run/(name+".mkv")
        assert hashlib.sha256(clip.read_bytes()).hexdigest()==receipt["samples"][name]["sha256"]
        by_state[name]=stats(clip,fields)
        print(name,by_state[name]["wall"])
    report={"pack":receipt["pack"],"packSHA":receipt["sha256"],
            "method":"32 consecutive RGB8 frames at 8 Hz. Compare each pixel to its own temporal median. Areas classified by the fixed game camera and independent patio geometry. Scene movement, precipitation animation and display exposure are all present in these ordinary images.",
            "stages":by_state}
    (arg.run/"streaks.json").write_text(json.dumps(report,indent=2)+"\n")
