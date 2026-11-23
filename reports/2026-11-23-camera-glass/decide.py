"""Compare both implementations, including same-camera controls and clone receipts."""
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
import json
import sys
import numpy as np
from PIL import Image
from room import HERE,ROOT,STUDY,BASE,STAGES
from readout import measure
def read(p):return json.loads(p.read_text())
def digest(p):return sha256(p.read_bytes()).hexdigest()
def captured(run):
    f=HERE/run
    c,p=read(f/"complete.json"),read(f/"preflight.json")
    assert c["complete"] and c["originalWorldAndConfigUnchanged"] and "3080 Ti" in c["gl"]["renderer"]
    assert p["labBefore"]==p["labAfter"] and not p["foreignObservations"]
    assert not any("AQLAVA_FAIL_" in l or "AQLAVA_DRIFT_" in l for l in (f/"client.log").read_text().splitlines())
    return c
def images(a,b,names):
    d={}
    for n in names:
        file=n+"-ingame.png"
        img=lambda folder:np.asarray(Image.open(HERE/folder/file).convert("RGB"),dtype=int)
        delta=np.abs(img(a)-img(b))
        d[n]=dict(differentPixels=int(np.sum(np.any(delta>0,axis=2))),aboveOneByte=int(np.sum(np.any(delta>1,axis=2))),
                  meanAbs=float(np.mean(delta)),maxAbs=int(np.max(delta)))
    return d
if __name__=="__main__":
    pack=ROOT/"build/camera-glass/Aqualumen-Glass-View-Pass.zip"
    captured_names=("base-room","base-meter","study-room","study-meter","frames-1440","water-meter","underwater-path",
                    "pass-frames","pass-meter","pass-room")
    receipts={n:captured(n) for n in captured_names}
    for name,path in (("study-room",STUDY),("frames-1440",STUDY),("base-room",BASE),("pass-frames",pack),("pass-room",pack)):
        assert receipts[name]["packSha256"]==digest(path)
    dry=read(HERE/"transmission.json")["study-meter"]
    replicated={}
    for n in STAGES:
        other=measure(HERE/"pass-meter"/(n+"-ingame.png"))
        error=float(np.max(np.abs(np.array(other["median"])-dry[n]["expected"])))
        replicated[n]={"median":other["median"],"error":error}
        assert error<.011,(n,error)
    stats={}
    for name,path in (("original",HERE.parent/"2026-11-23-screen-windows/screen-room"),("combined",HERE/"frames-1440"),("separate",HERE/"pass-frames")):
        frame=read(path/"summary.json")
        stats[name]={s:{k:frame["scenes"][s][k] for k in ("frames","cpuMeanMs","cpuP99Ms")} for s in ("air","red-ew")}
    decision=dict(base=digest(BASE),combined=digest(STUDY),separate=digest(pack),timings=stats,calibration=replicated,
                  meterPixelDifferences=images("study-meter","pass-meter",STAGES),
                  ordinaryPixelDifferences=images("study-room","pass-room",("none","one","mix","front")),
                  labAfter=read(HERE/"pass-room/preflight.json")["labAfter"],renderer=receipts["pass-room"]["gl"]["renderer"])
    (HERE/"decision.json").write_text(json.dumps(decision,indent=2)+"\n")
