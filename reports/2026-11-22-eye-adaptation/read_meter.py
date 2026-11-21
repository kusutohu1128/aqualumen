"""Read untouched F2 pixels and the time series from the lossless diagnostic strip."""
import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

here=Path(__file__).resolve().parent
village=here.parent/"2026-11-22-ceiling-return/village"
names=("exposure","lampGain","darkness","smoothSky","sceneR","sceneG","sceneB",
       "localLuminance","instantSky","rain","worldTime","frame","baseAmbient","valid")


def decode(strip):
    rgb=strip[4,4::8,:3].astype(int)
    if list(rgb[0]) != [82,177,48] or list(rgb[-1]) != [219,58,161]:
        return None
    fields=rgb[1:-1]
    if not np.all(fields[:,2]==(165 ^ fields[:,0] ^ fields[:,1])):
        return None
    values=(fields[:,0]*256+fields[:,1])/65535
    d=dict(zip(names, map(float,values)))
    for k in ("exposure","baseAmbient"):
        d[k]*=32
    for k in ("sceneR","sceneG","sceneB","localLuminance"):
        d[k]=2**(d[k]*4)-1
    d["worldTime"]=round(d["worldTime"]*24000)
    d["frame"]=round(d["frame"]*65535)
    assert d["valid"]==1
    return d


def read(run, forest=False):
    d=(here.parent/"2026-11-22-forest-cave" if forest else village)/run
    receipt=json.loads((d/"complete.json").read_text())
    assert receipt["cleanExit"] and receipt["previousSaveUnchanged"] and not receipt["benchmarkSentinelPresent"]
    assert receipt["labFilesUnchanged"] and not receipt["logErrors"] and "RTX 3080 Ti" in receipt["renderer"]
    assert not receipt["results"].get("failed") and not receipt["results"].get("stripFailure"), receipt["results"]
    photos={}
    for p in sorted(d.glob("*-ingame.png")):
        frame=np.asarray(Image.open(p).convert("RGB"))
        s=decode(frame[860:868,16:144])
        assert s is not None,p
        s["sha256"]=hashlib.sha256(p.read_bytes()).hexdigest()
        s["displayRGB"]=frame[180:255,1150:1250].mean(axis=(0,1)).round(3).tolist()
        photos[p.name.removesuffix("-ingame.png")]=s
    raw=subprocess.check_output(["ffmpeg","-v","error","-i",str(d/"meter.mkv"),"-f","rawvideo","-pix_fmt","rgb24","pipe:1"])
    frames=np.frombuffer(raw,dtype=np.uint8).reshape(-1,8,128,3)
    series=[]
    for i,frame in enumerate(frames):
        s=decode(frame)
        if s is not None:
            series.append(dict(seconds=round(i/12,3),**s))
    assert len(series)>.70*len(frames) and len({s["frame"] for s in series})>50
    with (here/(run+".csv")).open("w") as stream:
        w=csv.DictWriter(stream,fieldnames=series[0]);w.writeheader();w.writerows(series)
    result={"pack":receipt["packSha256"],"photos":photos,"validFrames":len(series),"capturedFrames":len(frames),
            "renderedFramesSampled":len({s["frame"] for s in series}),"path":str(d.relative_to(here.parent)),
            "routeTicks":[receipt["revisit"]["sourceSavedTime"],receipt["savedLevel"]["Time"]]}
    (here/(run+".json")).write_text(json.dumps(result,indent=2)+"\n")
    for label,s in photos.items():
        print(label,"exposure",round(s["exposure"],4),"scene",*[round(s[k],5) for k in ("sceneR","sceneG","sceneB")],
              "local",round(s["localLuminance"],5),"display",s["displayRGB"])
    print("valid/captured frames",len(series),len(frames))


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run")
    ap.add_argument("--forest",action="store_true")
    args=ap.parse_args()
    read(args.run,args.forest)
