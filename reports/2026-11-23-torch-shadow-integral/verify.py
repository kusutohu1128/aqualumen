"""Link the reproducible package, game receipts, framerate, and independent GPU checks."""
from hashlib import sha256
import json
from pathlib import Path
import sys
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DENSITY=HERE.parent/"2026-11-23-torch-density"
sys.path.insert(0,str(HERE.parent/"2026-11-23-placed-penumbra"))
from score import check_record
sys.path.insert(0,str(HERE.parent/"2026-11-22-gpu-profile"))
from run import lab_check

SHIP="0ba3e7673ceef7d0f60529457e550e259006fe293b15390bcd3d38eebf500b2a"
BASE="9d2d40e8ea3e70dcc5709b21288bfe0e35c313cf112f755356c3c433452144e1"
CAPS="c32be3d49b7ad0ac80697b994861e74ee651e36df8f2b80f393cb12c2709f293"
METER="ad45a2a3e17cfa3e2d0d14bdc51616b6e3bf0eeae7cc60165635bd926a206551"
MOTION="0401a88c1232bd0e4726d55defb505e84b513968b795471ce000c039a9d608a5"
GEOMETRY="51f6ea11af39ef639c9cc60c2893d8c227020c6e793d6b56afbaa9bf846a5d90"
MOTION_METER="839d254fac19fd5c28c96c53b4e35baddfa2604e7509be386f916af3e4c0bad5"
OLD_METER="9520af30e588c9fb4cfa08ed6d83c5fba6c2c8fa28e606868f78678a758ed025"


def read(path):
    return json.loads(path.read_text())


def main(extended=False,geometry=False,release=False):
    package=ROOT/"dist/Aqualumen-Torch-Shadow-Contours.zip"
    before=ROOT/"dist/Aqualumen-Placed-Torch-Shadows.zip"
    work=ROOT/"build/torch-shadow-integral"
    prototype=work/"Aqualumen-Torch-caps.zip"
    assert [sha256(p.read_bytes()).hexdigest() for p in (package,before,prototype)]==[SHIP,BASE,CAPS]
    with ZipFile(package) as a,ZipFile(prototype) as b,ZipFile(before) as c:
        assert a.namelist()==b.namelist()==c.namelist()
        entries=a.namelist()
        assert all(a.read(k)==b.read(k) for k in entries)
        changed=[k for k in entries if a.read(k)!=c.read(k)]
        assert changed==["shaders/lib/local_lighting.glsl"]
    motionPack=ROOT/"dist/Aqualumen-Torch-Shadow-Motion.zip"
    assert sha256(motionPack.read_bytes()).hexdigest()==MOTION
    with ZipFile(package) as a,ZipFile(motionPack) as b,ZipFile(work/"Aqualumen-Torch-motion24.zip") as proto:
        assert a.namelist()==b.namelist()==proto.namelist()
        assert [k for k in entries if a.read(k)!=b.read(k)]==changed
        assert all(b.read(k)==proto.read(k) for k in entries)
    lab=lab_check()
    assert lab["selected"]=="Aqualumen-1.8.0.zip"
    scenes={}
    captures=[(DENSITY/"gp-density-contours-bracket-base",BASE),(DENSITY/"gp-density-contours-bracket-ship",SHIP),
            (DENSITY/"gp-density-contours-gpu",SHIP),(DENSITY/"gp-density-two-caps",CAPS),
            (HERE/"birch-previous",OLD_METER),(HERE/"birch-two-caps",METER),
            (HERE/"corner-previous",OLD_METER),(HERE/"corner-contours",METER),(HERE/"contours-animal",METER),
            (HERE/"birch-motion24",MOTION_METER),(HERE/"motion24-animal",MOTION_METER),
            (DENSITY/"gp-density-motion24-ship",MOTION),(HERE/"ordinary-motion24",MOTION),
            (HERE/"ordinary-contours",SHIP)]
    if extended:
        adaptive="aa0afb78d16526bdea1dcf8ccaabf6d64bb93d5e06fc185634fe8691cecdf27d"
        meter="2ffa9fad13687aef960943b3faef03b6da53a2c8e5e9b4bea517b37da39fad57"
        for suffix,digest in (("",adaptive),("-meter",meter)):
            assert sha256((work/("Aqualumen-Torch-adaptive12"+suffix+".zip")).read_bytes()).hexdigest()==digest
        captures.extend([(HERE/"birch-adaptive12",meter),(DENSITY/"gp-density-adaptive12",adaptive),
                         (DENSITY/"gp-density-motion24-gpu",MOTION),(HERE/"night-ordinary-contours",SHIP),
                         (HERE/"night-ordinary-motion24",MOTION)])
        assert read(HERE/"adaptive12.json")["packSha"]==[METER,meter]
        assert read(DENSITY/"gp-density-adaptive12"/"summary.json")["packSha"]==adaptive
        gpu=read(DENSITY/"gp-density-motion24-gpu"/"summary.json")
        assert gpu["packSha"]==MOTION and gpu["scenes"]["birch-4"]["gpu"]["frames"]>0
        night=read(HERE/"night-ordinary-motion.json")
        for folder in ("night-ordinary-contours","night-ordinary-motion24"):
            assert read(HERE/folder/"geometry.json")["time"]==18000
        assert set(night["frames"])=={"left","centre"}
        assert all(v["largeVisibilityChanges"]["n"]>0 for v in night["frames"].values())
    if geometry:
        work_packs={"cone":"8a9a16d84b4dc4f2ffd55b16c5a17da4ba2049df6cc81b00902b6ac005d00ba9",
                    "cone-meter":"916ab4242ad4bac977f451184cd3f344e927c2a060f461638276a2af23ae7cd3",
                    "cone64":"a6d342d1400cca1504b6451b8740226e3859d1654cbea93a21479c67de95e2d9",
                    "cone64-meter":"738bee57d8142ef8deef9f2614e5b1863326176130c28f56999c394e40619920",
                    "joint-cone":"98285d9364545c9dbb1474e3a56ecfbe2bcb0125ba91b07c7c78750d79958636",
                    "joint-cone-meter":"aa92c7c50e97449b1a7cb9b4b0544e5189163e68df0e9901e592528977082c24"}
        for name,digest in work_packs.items():
            assert sha256((work/("Aqualumen-Torch-"+name+".zip")).read_bytes()).hexdigest()==digest
        geometryPack=ROOT/"dist/Aqualumen-Torch-Shadow-Geometry.zip"
        assert sha256(geometryPack.read_bytes()).hexdigest()==GEOMETRY
        with ZipFile(geometryPack) as a,ZipFile(work/"Aqualumen-Torch-joint-cone.zip") as b,ZipFile(package) as c:
            assert a.namelist()==b.namelist()==entries
            assert all(a.read(k)==b.read(k) for k in entries)
            assert [k for k in entries if c.read(k)!=a.read(k)]==changed
        for name in ("cone","cone64"):
            captures.extend([(DENSITY/("gp-density-"+name),work_packs[name]),
                             (HERE/("birch-"+name),work_packs[name+"-meter"])])
            summary=read(DENSITY/("gp-density-"+name)/"summary.json")
            assert summary["packSha"]==work_packs[name] and summary["scenes"]["birch-4"]["frames"]>0
            assert read(HERE/(name+"-sweep.json"))["packSha"]==[METER,work_packs[name+"-meter"]]
        captures.extend([(HERE/"settled-night-ordinary-contours",SHIP),(HERE/"settled-night-ordinary-motion24",MOTION),
                         (HERE/"cone64-animal-edits",work_packs["cone64-meter"]),
                         (HERE/"joint-animal",work_packs["joint-cone-meter"]),(HERE/"birch-joint",work_packs["joint-cone-meter"]),
                         (DENSITY/"gp-density-geometry",GEOMETRY)])
        assert read(DENSITY/"gp-density-geometry/summary.json")["packSha"]==GEOMETRY
        assert read(HERE/"joint-sweep.json")["packSha"]==[METER,work_packs["joint-cone-meter"]]
        warmup=read(HERE/"settled-night-ordinary-motion.json")["warmup"]
        assert all(r["milliseconds"]>=45000 and r["renderedFrames"]>=150 for r in warmup.values())
        previous_room=read(HERE/"cone64-animal.json")
        assert previous_room["farCowDifference"]["max"]>0
        restoration=read(HERE/"joint-animal.json")
        for k in ("restoredWhereCowCastShadow","farCowDifference","restoration","afterCowDifference"):
            assert restoration[k]["n"]>0 and restoration[k]["max"]==0
        assert restoration["evaluationsAfterRemoval"]==0 and restoration["cowDarkenedPartial"]>0
        edit=restoration["trunkEdit"]
        assert edit["fullyLitAfterCut"]==edit["restoredAfterReplant"]>0
        assert read(HERE/"pilot-blocks-extent.json")["maxBoundedError"]==0
    if release:
        captures.extend([(HERE/"settled-night-ordinary-geometry",GEOMETRY),(DENSITY/"gp-density-geometry-gpu",GEOMETRY)])
        gpu=read(DENSITY/"gp-density-geometry-gpu"/"summary.json")
        assert gpu["packSha"]==GEOMETRY and gpu["scenes"]["birch-4"]["gpu"]["frames"]>0
        assert read(HERE/"settled-night-ordinary-geometry.json")["warmup"]["ordinary-geometry"]["milliseconds"]>=45000
    for folder,expected in captures:
        receipt=read(folder/"complete.json")
        for scene in receipt["stages"]:
            assert check_record(folder,folder/(scene+"-ingame.png"))==expected
        assert read(folder/"preflight.json")["labAfter"]==lab
        scenes[folder.name]=dict(stages=receipt["stages"],pack=expected,renderer=receipt["gl"]["renderer"])
    native={}
    cases=read(HERE/"caps.json")
    for vendor,renderer in (("10_nvidia","RTX 3080 Ti"),("50_mesa","llvmpipe")):
        lines=(HERE/("compile-"+vendor+".log")).read_text().splitlines()
        assert renderer in lines[0] and lines[-1].startswith("PASS compile/link only")
        groups=cases[vendor]["groups"]
        assert all(g["overHalf"]==0 for g in groups.values())
        assert read(HERE/"voxel-cases.json")["caps"][vendor]["overTwo"]==0
        native[vendor]=dict(programs=sum(l.startswith("PASS ") for l in lines[:-1]),renderer=lines[0],
                            originalAndGrazing=sum(g["count"] for g in groups.values()),
                            voxelInputs=read(HERE/"voxel-cases.json")["caps"][vendor]["count"])
        motionLines=(HERE/("motion-compile-"+vendor+".log")).read_text().splitlines()
        assert renderer in motionLines[0] and motionLines[-1].startswith("PASS compile/link only")
        native[vendor]["motionPrograms"]=sum(l.startswith("PASS ") for l in motionLines[:-1])
        if geometry:
            geometryLines=(HERE/("joint-compile-"+vendor+".log")).read_text().splitlines()
            assert renderer in geometryLines[0] and geometryLines[-1].startswith("PASS compile/link only")
            native[vendor]["geometryPrograms"]=sum(l.startswith("PASS ") for l in geometryLines[:-1])
            assert native[vendor]["programs"]==native[vendor]["geometryPrograms"]==37
    motionRoom=read(HERE/"motion-animal.json")
    room=read(HERE/"animal.json")
    for test in (room,motionRoom):
        for k in ("restoration","farCowDifference","afterCowDifference","restoredWhereCowCastShadow"):
            assert test[k]["n"]>0 and test[k]["max"]==0
        assert test["cowDarkenedPartial"]==test["restoredWhereCowCastShadow"]["n"]>0
    assert room["evaluationsAfterRemoval"]==motionRoom["evaluationsAfterRemoval"]==0
    assert read(HERE/"motion24.json")["cellBoundaries"]["same"]["newOver10"]<read(HERE/"motion24.json")["cellBoundaries"]["same"]["oldOver10"]
    result=dict(motion=MOTION,motionAnimal={k:motionRoom[k] for k in ("restoredWhereCowCastShadow","farCowDifference","restoration")},
                ship=SHIP,prototype=CAPS,previous=BASE,identicalMembers=len(entries),changed=changed,
                gpuChecks=native,game=scenes,ordinaryLab=lab,restoredCowPoints=room["restoredWhereCowCastShadow"]["n"])
    if geometry:
        result.update(geometry=GEOMETRY,geometryAnimal={k:restoration[k] for k in
                      ("restoredWhereCowCastShadow","farCowDifference","restoration","evaluationsAfterRemoval","trunkEdit")})
    return result


if __name__=="__main__":
    mode=tuple(sys.argv[1:])
    outputs={():"verification.json",("--all",):"verification-final.json",("--geometry",):"geometry-verification.json",
             ("--release",):"release-verification.json"}
    report=main(bool(mode),mode in (("--geometry",),("--release",)),mode==("--release",))
    (HERE/outputs[mode]).write_text(json.dumps(report,indent=2)+"\n")
