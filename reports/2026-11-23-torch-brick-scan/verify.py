"""Audit the two builds, fixed-scene observations, and the unchanged ordinary Lab."""
from hashlib import sha256
import json
from pathlib import Path
import sys
from zipfile import ZipFile

from make_rows import BASE, DIGEST, HERE, ROOT, WORK
sys.path.insert(0,str(HERE.parent/"2026-11-22-gpu-profile"))
from run import lab_check

DENSITY=HERE.parent/"2026-11-23-torch-density"
PREVIOUS=HERE.parent/"2026-11-23-torch-shadow-integral"
CANDIDATE=ROOT/"dist/Aqualumen-Torch-Shadow-Rows.zip"
RELEASE="d9a740d78c612634a5c197bb001a3bcc250f83d0e891d0cbb90363de334d7968"
TRIAL="2a69fd3773f3af3548bb0247db5903c3e1d1bf199d84e24cb72a4493636381c1"

def read(p):
    return json.loads(p.read_text())

def digest(p):
    return sha256(p.read_bytes()).hexdigest()

def timing(folder,expected):
    folder=DENSITY/("gp-density-"+folder)
    complete=read(folder/"complete.json")
    pre=read(folder/"preflight.json")
    assert complete["complete"] and not complete["failure"] and complete["originalWorldAndConfigUnchanged"]
    assert pre["labBefore"]==pre["labAfter"] and not pre["foreignObservations"]
    summary=read(folder/"summary.json")
    assert summary["packSha"]==complete["packSha256"]==complete["sourcePackShaNow"]==expected
    assert complete["size"]==[2560,1440] and "RTX 3080 Ti" in summary["renderer"]["renderer"]
    frame=summary["scenes"]["birch-4"]
    assert digest(folder/"birch-4-ingame.png")==frame["capture"]
    result={key:frame[key] for key in ("cpuMeanMs","cpuP99Ms","frames","firstFrame","lastFrame")}
    if "meanMs" in frame:
        result["gpuMeanMs"]={k:frame["meanMs"][k] for k in ("frame","quad/deferred","terrain/cutout")}
    return result

if __name__=="__main__":
    assert digest(CANDIDATE)==RELEASE and digest(BASE)==DIGEST
    other=WORK/"Aqualumen-Torch-rows.zip"
    assert digest(other)==TRIAL
    with ZipFile(CANDIDATE) as a,ZipFile(other) as b,ZipFile(BASE) as c:
        assert a.namelist()==b.namelist()==c.namelist()
        changed=[k for k in c.namelist() if c.read(k)!=a.read(k)]
        assert changed==["shaders/lib/local_lighting.glsl"]
        for k in a.namelist():
            if k in changed:
                clean=lambda src:[s.strip() for s in src.splitlines() if s.strip() and not s.lstrip().startswith(b"//")]
                assert clean(a.read(k))==clean(b.read(k))
            else: assert a.read(k)==b.read(k)
    windows={key:timing(folder,expected) for key,(folder,expected) in dict(
        oldFirst=("geometry",DIGEST),testFirst=("brick-rows",TRIAL),
        shipSecond=("brick-rows-release",RELEASE),oldSecond=("brick-rows-reference",DIGEST),
        oldProfile=("geometry-gpu",DIGEST),shipProfile=("brick-rows-gpu",RELEASE)).items()}
    differences=[windows[a]["cpuMeanMs"]-windows[b]["cpuMeanMs"] for a,b in
                 (("oldFirst","testFirst"),("oldSecond","shipSecond"))]
    compiled={}
    for vendor,gpu in (("10_nvidia","RTX 3080 Ti"),("50_mesa","llvmpipe")):
        lines=(HERE/(vendor+"-compile.log")).read_text().splitlines()
        renderer=next(line for line in lines if line.startswith("Renderer:"))
        assert gpu in renderer and lines[-1].startswith("PASS compile/link only")
        programs=sum(s.startswith("PASS ") for s in lines[:-1])
        assert programs==37
        compiled[vendor]=dict(renderer=renderer,programs=programs)
    optics={k:read(HERE/(k+"-comparison.json"))["total"] for k in ("forest","grove")}
    assert optics["forest"]["changedVisibility"]==optics["forest"]["changedFlags"]==optics["forest"]["changedActive"]==0
    animal=read(HERE/"grove-edits.json")
    assert animal["evaluationsAfterRemoval"]==0 and animal["trunkEdit"]["fullyLitAfterCut"]==animal["trunkEdit"]["restoredAfterReplant"]>0
    assert animal["farCowDifference"]["max"]==animal["restoredWhereCowCastShadow"]["max"]==0 and animal["cowDarkenedPartial"]>0
    lab=lab_check()
    assert lab==read((HERE/"grove/preflight.json"))["labAfter"]
    assert lab["selected"]=="Aqualumen-1.8.0.zip"
    data=dict(pack=RELEASE,previous=DIGEST,prototype=TRIAL,changedMembers=changed,compiled=compiled,
             frames=windows,pairedFrameIntervalSavingMs=differences,imageTotals=optics,
             coverage=read(HERE/"coverage.json"),animal={k:animal[k] for k in ("evaluationsAfterRemoval","cowDarkenedPartial",
                 "farCowDifference","restoredWhereCowCastShadow","trunkEdit","cowTravelMetres")},lab=lab)
    (HERE/"verification.json").write_text(json.dumps(data,indent=2)+"\n")
