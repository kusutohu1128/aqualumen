"""Tie the installable ZIP and both display paths back to the isolated Minecraft runs."""
from hashlib import sha256
import json
import sys
from zipfile import ZipFile
from packs import BASE,HERE,ROOT,WORK

sys.path.insert(0,str(HERE.parent/"2026-11-22-gpu-profile"))
from run import lab_check

def read(p):
    return json.loads(p.read_text())

def digest(p):
    return sha256(p.read_bytes()).hexdigest()

def audit():
    trial=WORK/"Aqualumen-Stained-Panes.zip"
    pack=ROOT/"dist"/trial.name
    with ZipFile(pack) as ship,ZipFile(trial) as test,ZipFile(BASE) as base:
        assert ship.namelist()==test.namelist() and all(ship.read(k)==test.read(k) for k in ship.namelist())
        changed=[k for k in ship.namelist() if k not in base.NameToInfo or ship.read(k)!=base.read(k)]
        assert set(changed)=={"shaders/block.properties",*("shaders/lib/"+name+".glsl" for name in
                               ["leaf_light","local_capture","local_lighting","pane_transmission","trace_diffuse_face"])}
    assert digest(BASE)=="1794d020679d80cb65986ed4a8f2f2b0f453b6e3d9ee04c560f0b43dd285439c"
    lab=lab_check()
    assert lab["selected"]=="Aqualumen-1.8.0.zip"
    runs={}
    for folder,source in [("control",WORK/"Aqualumen-Pane-Control-RGB.zip"),("pane",WORK/"Aqualumen-Stained-Panes-RGB.zip"),
                          ("appearance",trial),("timing-control",BASE),("timing-pane",pack)]:
        done=read(HERE/folder/"complete.json");pre=read(HERE/folder/"preflight.json")
        assert done["complete"] and done["originalWorldAndConfigUnchanged"] and not done["failure"]
        assert done["packSha256"]==done["sourcePackShaNow"]==digest(source) and done["shaderpackLogged"]
        assert pre["labBefore"]==pre["labAfter"]==lab and not pre["foreignObservations"]
        for stage in done["stages"]:
            assert digest(HERE/folder/(stage+"-ingame.png"))==done["screenshots"][stage]["ingame"]
        runs[folder]=dict(pack=done["packSha256"],renderer=done["gl"]["renderer"],size=done["size"],stages=done["stages"])
    cm=read(HERE/"control-score.json")["stages"];pm=read(HERE/"pane-score.json")["stages"]
    assert all(v["receivers"]==3681 for v in pm.values())
    assert cm["red-ew"]["tintedErrorsBytes"]["p95"]>71 and pm["red-ew"]["tintedErrorsBytes"]["p95"]<1
    assert cm["thick"]==pm["thick"]
    assert pm["air"]==pm["clear-again"]==cm["air"]
    assert all(s["tintedErrorsBytes"].get("p95",0)<2 for s in pm.values())
    frames={a:read(HERE/("timing-"+a)/"summary.json")["scenes"] for a in ("control","pane")}
    for a,row in frames.items():
        assert all(s["frames"]>=50 for s in row.values())
    checks={}
    for vendor in ("mesa","nvidia"):
        rays=read(HERE/("geometry-"+vendor+".json"))
        assert rays["rays"]==15488 and rays["checkedBlockStates"]==256 and rays["maxDistanceError"]<2e-5
        lines=(HERE/("compile-"+vendor+".txt")).read_text().splitlines()
        assert sum(s.startswith("PASS ") for s in lines)==38 and lines[-1].startswith("PASS compile/link only")
        checks[vendor]=dict(renderer=rays["renderer"],programs=37,rays=rays["rays"],maxDistanceError=rays["maxDistanceError"])
    v=HERE.parent/"2026-11-22-ceiling-return/village"
    ledger=read(HERE/"playtime.json")
    last=(ROOT/ledger["chains"][-1]["receipt"]).parent
    assert last.parent==v
    for play in (v/"house-poppy",last):
        r=read(play/"complete.json")
        assert r["labFilesUnchanged"] and r["modsUnchanged"] and r["previousSaveUnchanged"] and not r["benchmarkSentinelPresent"]
        assert r["cleanExit"] and not r["logErrors"] and not r["results"].get("failed")
    save=read(last/"save.json")
    data=dict(installableSHA256=digest(pack),trialSHA256=digest(trial),identicalUncompressedMembers=len(ship.namelist()),
              differencesFromDiffuseDisplay=changed,runs=runs,compileAndGeometry=checks,frames=frames,
              currentLab=lab,finalSave=save["archive"],finalSaveSHA256=save["sha256"],playtimeGameDays=ledger["gameDays"])
    (HERE/"verification.json").write_text(json.dumps(data,indent=2)+"\n")
    print(data["installableSHA256"],data["identicalUncompressedMembers"],data["playtimeGameDays"])

if __name__=="__main__":
    audit()
