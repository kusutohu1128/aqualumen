"""Collect evidence from the actual profiles, visibility captures and cache probes."""
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-22-gpu-profile"))
from run import lab_check
DENSITY=HERE.parent/"2026-11-23-torch-density"
ROOT=HERE.parents[1]
PACK=ROOT/"build/torch-cell-shadow/Aqualumen-Torch-Cell-Shadow.zip"
OLD=ROOT/"dist/Aqualumen-Diffuse-Display.zip"

def read(p):
    return json.loads(p.read_text())

def sha(p):
    with p.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()

def frame(label, pack, profile):
    d=DENSITY/("gp-density-"+label)
    run,pre,data=[read(d/(n+".json")) for n in ("complete","preflight","summary")]
    assert run["complete"] and run["originalWorldAndConfigUnchanged"] and not run["failure"]
    assert pre["labBefore"]==pre["labAfter"] and not pre["foreignObservations"]
    assert sha(pack)==run["sourcePackShaNow"]==run["packSha256"]==data["packSha"]
    assert run["size"]==[2560,1440] and "RTX 3080 Ti" in run["gl"]["renderer"]
    r=data["scenes"]["birch-4"]
    assert r["capture"]==sha(d/"birch-4-ingame.png") and r["frames"]>1
    result={k:r[k] for k in ("frames","cpuMeanMs","cpuP99Ms")}
    if profile:
        result["gpuMs"]={k:r["meanMs"][k] for k in ("frame","quad/deferred","terrain/cutout",
                                                     "dispatch/shadowcomp5","dispatch/shadowcomp6")}
    else:
        assert "meanMs" not in r
    return result

def native(vendor,renderer):
    lines=(HERE/(vendor+"-cache.log")).read_text().splitlines()
    start=next(i for i,line in enumerate(lines) if line.startswith("renderer "))
    lines=lines[start:]
    assert renderer in lines[0]
    frames={}
    for line in lines[1:]:
        name,*values=line.split()
        assert len(values)==5
        frames[name]=dict(zip(("active","open","dark","reused","rayTested"),map(int,values),strict=True))
    assert len(frames)==15 and list(frames)[-1]=="return"
    assert frames["initial"]["dark"]>0 and frames["still"]["active"]==frames["still"]["reused"]
    return dict(renderer=lines[0],states=frames)

def main():
    before=sha(OLD);after=sha(PACK)
    assert before=="1794d020679d80cb65986ed4a8f2f2b0f453b6e3d9ee04c560f0b43dd285439c"
    assert after=="14e849c5b54ee04db05c75216a75764e865d553b711e67b180ed328c6afb7db0"
    with ZipFile(PACK) as a,ZipFile(OLD) as b:
        assert a.namelist()==b.namelist()
        changed=[name for name in a.namelist() if a.read(name)!=b.read(name)]
        assert set(changed)=={"shaders/shadowcomp6.csh","shaders/lib/local_lighting.glsl"}
    optics={k:read(HERE/(k+"-comparison.json"))["total"] for k in ("forest","grove")}
    for r in optics.values():
        assert r["compared"]>0 and r["partial"]>0
        assert r["changed"]==r["changedActivity"]==r["darkWasLit"]==r["newlyOpenWasShaded"]==0
    a=read(HERE/"grove-edits.json")
    assert a["trunkEdit"]["fullyLitAfterCut"]==a["trunkEdit"]["restoredAfterReplant"]>0
    assert a["evaluationsAfterRemoval"]==a["farCowDifference"]["max"]==a["restoredWhereCowCastShadow"]["max"]==0
    assert a["cowDarkenedPartial"]>0
    cache={k:native(k,v) for k,v in (("10_nvidia","RTX 3080 Ti"),("50_mesa","llvmpipe"))}
    assert cache["10_nvidia"]["states"]==cache["50_mesa"]["states"]
    timings={label:frame(label,pack,profile) for label,pack,profile in (
        ("midtones-default",OLD,False),("cell-shadow",PACK,False),("cell-second",PACK,False),
        ("cell-reference-second",OLD,False),("cell-shadow-gpu",PACK,True),("cell-reference-gpu",OLD,True))}
    lab=lab_check()
    assert lab==read(HERE/"forest/preflight.json")["labBefore"] and lab["selected"]=="Aqualumen-1.8.0.zip"
    out=dict(previous=before,candidate=after,changed=changed,visibility=optics,cache=cache,timings=timings,
             lab=lab,edits={k:a[k] for k in ("trunkEdit","evaluationsAfterRemoval","cowDarkenedPartial",
                                             "restoredWhereCowCastShadow","cowTravelMetres")})
    movies={}
    for name in ("cow-motion","glass-cow-motion"):
        folder=HERE/name
        clip=read(folder/"motion-score.json")
        proof=read(folder/"complete.json")
        assert proof["complete"] and proof["originalWorldAndConfigUnchanged"] and not proof["failure"]
        assert proof["packSha256"]==proof["sourcePackShaNow"]==clip["packSha256"]
        assert sha(folder/"cow-motion.mkv")==clip["movieSha256"] and clip["unequalChanges"]==0
        assert clip["changingWallSamples"]>0 and clip["uniqueFieldTotals"]["different"]==0
        movies[name]={k:v for k,v in clip.items() if k!="frames"}
    assert movies["glass-cow-motion"]["uniqueFieldTotals"]["bodyShadedNewClear"]>0
    out["motion"]=movies
    play=read(HERE/"playtime.json")
    world=read(HERE.parent/"2026-11-21-animal-light/woodland/cell-shadow-birch-west/save.json")
    assert sha(ROOT/world["archive"])==world["sha256"]
    assert world["verifiedBlocks"]["582,64,423"]=="minecraft:torch" and world["verifiedBlocks"]["584,64,424"]=="minecraft:air"
    out["survival"]=dict(archive=world["archive"],archiveSha256=world["sha256"],gameDays=play["gameDays"],walkedMetres=play["walkedMetres"])
    (HERE/"verification.json").write_text(json.dumps(out,indent=2)+"\n")
if __name__=="__main__":
    main()
