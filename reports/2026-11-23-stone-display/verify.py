"""Audit the shipping pack, active Lab, captured settings and the actual timing interval."""
import json
from pathlib import Path
import re
from zipfile import ZipFile

from diffuse_meter import DIST, FLEX, ROOT, SHIP, WORK
from make_pack import HERE, sha256
from shore import guarded

DENSITY=HERE.parent/"2026-11-23-torch-density"

def load(path):
    return json.loads(path.read_text())

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def timing(label,pack):
    folder=DENSITY/label
    pre,done,summary=(load(folder/n) for n in ("preflight.json","complete.json","summary.json"))
    assert not pre["foreignObservations"] and pre["labBefore"]==pre["labAfter"] and pre["samples"]>0
    assert done["complete"] and not done["failure"] and done["originalWorldAndConfigUnchanged"]
    assert digest(pack)==done["sourcePackShaNow"]==summary["packSha"]==done["packSha256"]
    assert "RTX 3080 Ti" in done["gl"]["renderer"] and done["size"]==[2560,1440]
    row=summary["scenes"]["birch-4"]
    assert row["capture"]==digest(folder/"birch-4-ingame.png")
    return {k:row[k] for k in ("frames","cpuMeanMs","cpuP99Ms","firstFrame","lastFrame")}

def main():
    assert digest(FLEX)=="1794d020679d80cb65986ed4a8f2f2b0f453b6e3d9ee04c560f0b43dd285439c"
    assert (WORK/"check-release.zip").read_bytes()==FLEX.read_bytes()
    with ZipFile(FLEX) as new, ZipFile(SHIP) as base:
        assert new.testzip() is None and new.namelist()==base.namelist()
        changed=[n for n in new.namelist() if new.read(n)!=base.read(n)]
        assert set(changed)=={"shaders/final.fsh","shaders/shaders.properties","shaders/lang/en_US.lang","shaders/lang/ja_JP.lang"}
        src=new.read("shaders/final.fsh").decode()
        opts=new.read("shaders/shaders.properties").decode()
        m=re.search(r"^#define MIDTONE_CONTRAST (\S+) // \[([^\]]+)\]$",src,re.M)
        assert m[1]=="0.4" and m[2].split()==["0.0","0.2","0.4","0.6","0.8","1.0"]
        assert all("MIDTONE_CONTRAST" in next(line for line in opts.splitlines() if line.startswith(prefix)).split("=")[1].split()
                   for prefix in ("screen.LIGHT=","sliders="))
    gl={}
    for vendor,renderer in (("10_nvidia","RTX 3080 Ti"),("50_mesa","llvmpipe")):
        run=(HERE/(vendor+"-default.log")).read_text().splitlines()
        gl[vendor]=next(line for line in run if line.startswith("Renderer:"))
        assert renderer in gl[vendor] and "PASS final" in run and run[-1].startswith("PASS compile/link only")
    fixed=load(HERE/"default-shore.json")
    assert fixed["receipt"]["automatedReceipt"] and len(fixed["receipt"]["frames"])==3
    zero=load(HERE/"zero-setting.json")
    assert zero["maxCodeDelta"]==0 and zero["pairs"]==360000
    obs=load(HERE/"default-and-bark.json")["realStone"]
    fixedFrame=next(frame for frame in obs if frame["frame"]=="sample-1-held-0-ingame.png")
    assert all(fixedFrame["regions"][mat]["sameHDRAndMetadata"]==96 for mat in ("torchCore","nicheBack","leftWall","rightWall","ceiling"))
    assert all(frame["regions"]["torchCore"]["sameHDRAndMetadata"]==96 and frame["regions"]["nicheBack"]["sameHDRAndMetadata"]==96 for frame in obs)
    lab=guarded.lab_check()
    assert lab==load(DENSITY/"gp-density-midtones-default/preflight.json")["labAfter"]
    assert lab["selected"]=="Aqualumen-1.8.0.zip" and digest(WORK/"ordinary.zip")==lab["fileHashes"]["shaderpacks/Aqualumen-1.8.0.zip"]
    data=dict(pack=digest(FLEX),parent=digest(SHIP),changedMembers=changed,defaultStrength=.4,zeroSetting=zero,gl=gl,
        ordinarySelected=lab["selected"],ordinaryPack=digest(WORK/"ordinary.zip"),activeMods=lab["activeMods"],
        frameIntervals={key:timing(label,pack) for key,label,pack in (
            ("previous","gp-density-brick-rows-release",SHIP),("fullStrength","gp-density-diffuse-display",DIST),
            ("shippingDefault","gp-density-midtones-default",FLEX))})
    (HERE/"verification.json").write_text(json.dumps(data,indent=2)+"\n")
    print(data["frameIntervals"])

if __name__=="__main__":
    main()
