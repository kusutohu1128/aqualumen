#!/usr/bin/env python3
"""Extract shader-pack load -> first-rendered-frame timing per launch.

Anchors: client.log [HH:MM:SS] log lines + AQ_RENDER_FRAME_END <epoch_ms>.
The first world frame = first AQ_RENDER_FRAME_END after
'Creating pipeline for dimension minecraft:overworld'.
"""
import json, re, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
RUNS = Path(__file__).parent / "runs"
ORDER = ["gp-mf-a1-p13-compiler","gp-mf-b1-p14-nocompiler","gp-mf-c1-p14-compiler",
         "gp-mf-c2-p14-compiler","gp-mf-b2-p14-nocompiler","gp-mf-a2-p13-compiler"]

def logsec(line):
    m=re.match(r"\[(\d+):(\d+):(\d+)\]",line)
    return int(m.group(1))*3600+int(m.group(2))*60+int(m.group(3)) if m else None

def analyze(label):
    d=RUNS/label; log=(d/"client.log").read_text(errors="replace").splitlines()
    r={"label":label}
    # find key log lines (index + second-of-day)
    idx={}
    for i,l in enumerate(log):
        for key,pat in [("pack","Using shaderpack:"),("pipe","Creating pipeline for dimension"),
                        ("ready","AQ_PROFILE_READY"),("reload","Reloading ResourceManager")]:
            if pat in l and key not in idx: idx[key]=(i,logsec(l),l[:19])
    r["log"]=idx
    # first world-frame epoch after pipeline creation
    pipe_i=idx.get("pipe",(None,))[0]
    fep=None
    if pipe_i is not None:
        for l in log[pipe_i:]:
            m=re.search(r"AQ_RENDER_FRAME_END (\d+)",l)
            if m: fep=int(m.group(1)); break
    r["firstFrameEpochMs"]=fep
    if fep:
        dt=datetime.fromtimestamp(fep/1000,JST)
        r["firstFrameJst"]=dt.strftime("%H:%M:%S.")+f"{dt.microsecond//1000:03d}"
    # also: last frame epoch of run (for span)
    leps=[int(m.group(1)) for l in log for m in [re.search(r"AQ_RENDER_FRAME_END (\d+)",l)] if m]
    r["nFrameMarks"]=len(leps)
    if leps: r["lastFrameJst"]=datetime.fromtimestamp(leps[-1]/1000,JST).strftime("%H:%M:%S")
    return r

if __name__=="__main__":
    for l in ORDER:
        r=analyze(l)
        lg=r.get("log",{})
        print(f"{r['label']}")
        for k in ["reload","pack","pipe","ready"]:
            if k in lg: print(f"   {k:6s} @{lg[k][2]}  (sec={lg[k][1]})")
        print(f"   firstWorldFrame epoch={r.get('firstFrameEpochMs')} -> {r.get('firstFrameJst')}  marks={r.get('nFrameMarks')}")
