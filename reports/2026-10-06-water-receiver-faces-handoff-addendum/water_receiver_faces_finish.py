"""Verify live ordinary handoff; retain CPU checks/source/images; exclusive seal."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from water_normal_pause_event import verify_pause_event

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/2026-10-06-water-receiver-faces"
GAME=Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft")
PROBE="aqualumen-receiver-material-probe-0.1.0-v1.jar"

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open("xb") as stream:stream.write(source.read_bytes())
def save(name,value):
    with (OUT/name).open("x") as stream:json.dump(value,stream,indent=2,sort_keys=True)

def main(pid,handle,runtime,pause):
    if (OUT/"SHA256SUMS").exists():raise ValueError("Never overwrite a seal")
    if not runtime.startswith("2026-10-06_") or not pause.startswith("2026-10-06_"):
        raise ValueError("Exact screenshot scope required")
    if Path(runtime).name!=runtime or Path(pause).name!=pause or runtime==pause:
        raise ValueError("Distinct exact screenshot filenames required")
    baseline=json.loads((OUT/"fresh-normal-baseline.json").read_text())
    if baseline!=json.loads((OUT/"normal-restored.json").read_text()) or baseline!=json.loads((OUT/"normal-exact-before-reopening.json").read_text()):
        raise ValueError("Ordinary before-reopening exactness failed")
    if {p.name:sha(p) for p in (GAME/"mods").glob("*.jar")}!=baseline["activeMods"]:
        raise ValueError("Active Mod identity changed")
    controls=baseline["instrumentationEntryPointsAbsent"]+["aqualumen-receiver-material-probe.properties"]
    if any((GAME/"config"/name).exists() for name in controls):raise ValueError("TEST control still active")
    if any(p.name.startswith("aqualumen-receiver-material-probe-") for p in (GAME/"mods").glob("*.jar")):
        raise ValueError("Probe still active")
    if sha(GAME/"shaderpacks/Aqualumen-0.6.0.zip")!="6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73":
        raise ValueError("Normal pack changed")
    if "shaderPack=Aqualumen-0.6.0.zip" not in (GAME/"config/iris.properties").read_text():raise ValueError("Normal pack selection changed")
    proc=Path("/proc")/str(pid)
    if (proc/"comm").read_text().strip()!="java":raise ValueError("Actual normal Java not live")
    lockfds=[int(p.name) for p in (proc/"fd").iterdir() if p.readlink()==GAME/"saves/新規ワールド/session.lock"]
    if len(lockfds)!=1:raise ValueError("Exact ordinary lock not held")
    audit=json.loads((OUT/"actual-face-audit.json").read_text())
    if audit["qualifiedFirstFaces"]!=16 or audit["sourceUploaded"] or audit["fullGoalAchieved"]:
        raise ValueError("Face audit scope changed")
    receipt=json.loads((ROOT/"reports/2026-10-06-water-occluded-main/native-v4-receipt.json").read_text())
    for name,digest in receipt["sourceSHA256"].items():
        if sha(ROOT/name)!=digest:raise ValueError("Previous shader/native seam changed: "+name)
    if (ROOT/"build"/PROBE).read_bytes()!=(ROOT/"build/aqualumen-receiver-material-probe-0.1.0-rebuild-proof-v2.jar").read_bytes():
        raise ValueError("Deterministic producer rebuild differs")
    if sha(OUT/PROBE)!=sha(ROOT/"build"/PROBE):raise ValueError("Actual installed producer identity differs")
    log=(GAME/"logs/latest.log").read_text()
    # Event chronology is necessary but not a replacement for actually viewing
    # both screenshots before invoking this recorder.
    verify_pause_event(log,runtime,pause)
    if ("OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti" not in log or "Using shaderpack: Aqualumen-0.6.0.zip" not in log
            or "0.2.0 contact bridge initialized" not in log or "aqualumen_receiver_material_probe" in log
            or "Saving and pausing game" not in log or "OpenGL debug message" in log):
        raise ValueError("Fresh normal NVIDIA/pack/physics/pause proof unavailable")
    copy(GAME/"logs/latest.log",OUT/"normal-final-runtime.log")
    for original,name in [(runtime,"normal-runtime.png"),(pause,"normal-pause.png"),
                           ("2026-10-06_15.27.58.png","test-runtime.png"),
                           ("2026-10-06_15.27.58_2.png","test-save-quit-focus.png"),
                           ("2026-10-06_15.28.16.png","test-saving-not-quit.png"),
                           ("2026-10-06_15.28.29.png","test-title-no-quit-focus.png"),
                           ("2026-10-06_15.28.59.png","test-title-quit-focus.png"),
                           ("2026-10-06_15.29.42.png","test-title-still-live.png")]:
        copy(GAME/"screenshots"/original,OUT/name)
    checks={"face-decoder":["bash","tools/test-receiver-face.sh"],
            "face-evidence":["python3","tools/test_water_receiver_faces_audit.py"],
            "geometry-regression":["bash","tools/test-receiver-field.sh"],
            "bathymetry-regression":["bash","tools/test-physics-mod.sh"]}
    exits={}
    for name,command in checks.items():
        result=subprocess.run(["rtk","proxy",*command],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        with (OUT/(name+"-green.log")).open("xb") as stream:stream.write(result.stdout)
        exits[name]=result.returncode
        if result.returncode:raise ValueError("Affected CPU check failed: "+name)
    sources=[ROOT/"physics-mod/dev/aqualumen/physics"/name for name in
             ("BathymetryField.java","LoadedWorld.java","ReceiverField.java","ReceiverFace.java","LoadedReceiverWorld.java","LoadedReceiverFaces.java")]
    sources += [ROOT/"physics-mod/test/dev/aqualumen/physics/ReceiverFaceTest.java"]
    sources += [p for p in (ROOT/"tools/receiver-material-probe").rglob("*") if p.is_file()]
    sources += [ROOT/"tools"/name for name in ("build-receiver-material-probe.sh","test-receiver-face.sh","water_receiver_faces_audit.py",
                    "test_water_receiver_faces_audit.py","water_receiver_faces_lifecycle.py","water_receiver_faces_finish.py",
                    "water_normal_pause_event.py")]
    sources += [ROOT/"docs/RECEIVER_FIELD.md"]
    for source in sources:copy(source,OUT/"final-source"/source.relative_to(ROOT))
    checkpoint=dict(schema="aqualumen-actual-face-checkpoint-v1",fullGoalAchieved=False,productionFixImplemented=False,
        newActualMinecraftFaceReadback=True,faceRecordCount=16,uniqueCellFaces=14,
        actualTexturePixelReadback=False,actualSourceRadianceComputed=False,actualIrisSourceBinding=False,
        productionShaderSourcesUnchanged=True,nativeRendererREDsRemain=2,
        frameTimingMeasured=False,ordinaryHostJava=pid,ordinaryOwnedHandle=handle,ordinaryLockFD=lockfds[0],
        ordinarySavedFilesExactBeforeReopening=True,ordinarySaveRestored=False,ordinaryWorldAutomation=False,
        TESTClientExit=0,TESTInstrumentationRecoverablyDisabled=True,allOptInEntryPointsAbsent=controls,
        nativeGLAfterNormalRelaunch=False,normalPackSHA256=sha(GAME/"shaderpacks/Aqualumen-0.6.0.zip"),
        normalPhysicsSHA256=sha(GAME/"mods/aqualumen-physics-0.2.0.jar"),
        actualInstalledAndRebuiltProbeSHA256=sha(OUT/PROBE),publicCPUCheckExitCodes=exits,
        runtimeScreenshot=runtime,pauseScreenshot=pause,rootInspectedRuntimeAndPause=True)
    save("checkpoint.json",checkpoint)
    files=sorted(p for p in OUT.rglob("*") if p.is_file())
    with (OUT/"SHA256SUMS").open("x") as stream:
        for p in files:
            if p.is_symlink():raise ValueError("Evidence symlink rejected")
            stream.write(f"{sha(p)}  {p.relative_to(ROOT)}\n")
    print(f"Sealed {len(files)} files; actual16 faces + safe normal handoff, not water fix or goal completion")

if __name__=="__main__":main(int(sys.argv[1]),int(sys.argv[2]),sys.argv[3],sys.argv[4])
