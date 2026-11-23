"""Audit the game's original F2s and measure same-frame 8-bit output and local gradients."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image, ImageDraw

from curves import HERE, LUMA, diffuse
from shore import STAGES, guarded


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(run,balanced):
    receipt=json.loads((run/"preflight.json").read_text())
    assert not receipt["underLock"]["foreign"]
    automatic=(run/"complete.json").is_file()
    packName="Aqualumen-Midtones-Pair.zip" if balanced else "Aqualumen-Diffuse-Pair.zip"
    digest= ("47918fdda9d02e9e89fbb239182c77bbebf0543e38587a56a0e56ff1d1e9eedb" if balanced else
             "1d21920d5c47463d723e2efda6bae7f11f3ac7cfc7a50d7757d4ce52264a1ca3")
    if automatic:
        completion=json.loads((run/"complete.json").read_text())
        assert completion["packSha256"]==completion["sourcePackShaNow"]==digest
        assert completion["complete"] and not completion["failure"] and completion["originalWorldAndConfigUnchanged"]
        assert receipt["labAfter"]==receipt["labBefore"] and not receipt["foreignObservations"] and receipt["samples"]>0
    else:
        assert not balanced
        assert guarded.lab_check()==receipt["labBefore"]
        game=Path((run/"private-game.txt").read_text())
        assert str(game).startswith("/tmp/aql-v190-run-")
        if game.is_dir():
            assert sha(game/"shaderpacks"/packName)==digest
        else:
            earlier=json.loads((HERE/"shore.json").read_text())["receipt"]
            assert earlier["sourcePackSha256"]==digest and earlier["labBeforeMatchesLive"]
    log=(run/"client.log").read_text()
    renderer=next(s for s in log.splitlines() if "OpenGL Renderer:" in s)
    assert "RTX 3080 Ti" in renderer and packName in log
    files={sha(p):p for p in (run/"f2").glob("*.png")}
    audit={}
    for stage in STAGES:
        frameSha=sha(run/(stage+"-ingame.png"))
        origin=files[frameSha]
        cap=datetime.strptime(origin.stem,"%Y-%m-%d_%H.%M.%S")
        times=[]
        for event in ("READY","STILL"):
            m=re.search(r"^\[(\d+:\d+:\d+)\].*?AQLAVA_"+event+"_"+stage+"_END",log,re.M)
            assert m is not None
            times.append(m[1])
        assert times[0]<cap.strftime("%H:%M:%S")<times[1]
        assert "AQLAVA_DRIFT_"+stage not in log and "AQLAVA_FAIL_"+stage not in log
        audit[stage]=dict(source=origin.name,sha256=frameSha,ready=times[0],still=times[1])
    return dict(renderer=renderer,labBeforeMatchesLive=True,sourcePackSha256=digest,frames=audit,
                automatedReceipt=automatic,note=("Full private runner receipt." if automatic else
                "Runner exited before writing the final receipt. F2 identity, READY/STILL and current Lab were audited separately."))


def read(run,name,tag="ingame"):
    frame=np.array(Image.open(run/f"{name}-{tag}.png").convert("RGB"))
    assert frame.shape==(900,1600,3)
    a,b,mask=frame[:450,:800],frame[:450,800:],frame[450:,:800]
    assert np.all((mask==0)|(mask==255))
    return a,b,mask


def population(a,b,region):
    p,q=a[region],b[region]
    if not len(p):
        return {"pixels":0}
    p,q=p.astype(float),q.astype(float)
    step=abs(p-q).max(axis=1)
    linearOld,linearNew=(p/255.)**2.2,(q/255.)**2.2
    oldy,newy=linearOld@LUMA,linearNew@LUMA
    lit=(linearOld.sum(axis=1)>.001)&(linearNew.sum(axis=1)>.001)
    oldFrac=linearOld[lit]/linearOld[lit].sum(axis=1,keepdims=True)
    newFrac=linearNew[lit]/linearNew[lit].sum(axis=1,keepdims=True)
    chromaticity=abs(oldFrac-newFrac).max(axis=1)
    def levels(y):
        return np.quantile(y,[.1,.5,.9,.99]).tolist()
    def flat_stats(code):
        return dict(clipped=int((code.max(axis=1)==255).sum()),black=int((code.max(axis=1)==0).sum()))
    changes=[]
    for old,new,src in ((a,b,region),(a.transpose(1,0,2),b.transpose(1,0,2),region.T)):
        keep=src[:,:-1]&src[:,1:]
        old_jump=abs(np.diff(old.astype(int),axis=1)).max(axis=2)
        new_jump=abs(np.diff(new.astype(int),axis=1)).max(axis=2)
        changes.append(new_jump[keep & (old_jump>=1) & (old_jump<=3)])
    jumps=np.concatenate(changes)
    return dict(pixels=len(p),oldLinearLuminance=levels(oldy),newLinearLuminance=levels(newy),
                oldLimits=flat_stats(p),newLimits=flat_stats(q),changed=int((step>0).sum()),
                codeDeltaP95=float(np.quantile(step,.95)),maxCodeDelta=float(step.max()),
                linearRgbFractionMaxDifferenceP95=float(np.quantile(chromaticity,.95)) if len(chromaticity) else None,
                adjacentPairsWithOldStep1to3=len(jumps),flattenedAdjacentPairs=int((jumps==0).sum()),
                expandedTo4OrMore=int((jumps>=4).sum()))


def run(balanced):
    folder=HERE/("shore-and-ore-balanced" if balanced else "shore-and-ore")
    receipt=audit(folder,balanced)
    canvas=Image.new("RGB",(1000,3*301+26),(25,26,29))
    draw=ImageDraw.Draw(canvas)
    for i,title in enumerate(("Rows","Diffuse Display")):
        draw.text((4+500*i,6),title,fill="white")
    stages={}
    for i,name in enumerate(STAGES):
        a,b,m=read(folder,name)
        sky,water,sun=(m[:,:,k]>0 for k in range(3))
        opaque=~(sky|water)
        groups={"sky":sky,"nearerTranslucent":water,"solarCentre":sun,"opaque":opaque,
                "darkOpaqueBelowCode80":opaque & (a.max(axis=2)<80)}
        if name=="ore-light":
            for label,(x0,y0,x1,y1) in {"redstoneOre":(365,146,434,215),"glowstone":(285,146,356,215)}.items():
                rect=np.zeros_like(sky)
                rect[y0:y1,x0:x1]=True
                assert not np.any(rect & (sky|water))
                groups[label]=rect
        stages[name]={key:population(a,b,mask) for key,mask in groups.items()}
        for j,half in enumerate((a,b)):
            thumb=Image.fromarray(half).resize((500,281),Image.Resampling.LANCZOS)
            canvas.paste(thumb,(j*500,26+i*301))
        draw.text((4,307+i*301),name,fill="white")
    gray=np.arange(256,dtype=float)/255.
    exposed=np.minimum(gray**2.2,.999999)/(1.-np.minimum(gray**2.2,.999999))
    real=diffuse(np.repeat(exposed[:,None],3,axis=1),.4 if balanced else 1.)
    new=np.rint(real[:,0]**(1/2.2)*255).astype(int)
    steps=np.diff(new)
    result=dict(receipt=receipt,stages=stages,grayRamp=dict(oldAdjacentSteps=255,
                zero=int((steps==0).sum()),two=int((steps==2).sum()),three=int((steps==3).sum()),maximum=int(steps.max())))
    canvas.save(HERE/("default-shore-comparison.jpg" if balanced else "shore-comparison.jpg"),quality=94)
    (HERE/("default-shore.json" if balanced else "shore.json")).write_text(json.dumps(result,indent=2)+"\n")

if __name__=="__main__":
    run("--balanced" in sys.argv)
