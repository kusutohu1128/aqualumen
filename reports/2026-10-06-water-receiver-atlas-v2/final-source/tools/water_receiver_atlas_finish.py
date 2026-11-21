"""Verify ordinary handoff and exclusively freeze qualified GPU pixels and failed attempt."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from water_normal_pause_event import verify_pause_event
from water_receiver_atlas_audit import audit
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/2026-10-06-water-receiver-atlas-v2"
FAILED=ROOT/"reports/2026-10-06-water-receiver-atlas"
GAME=Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft")
JAR="aqualumen-receiver-material-probe-0.1.2-atlas-v3.jar"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open("xb") as stream:stream.write(source.read_bytes())
def seal(directory):
    paths=sorted(p for p in directory.rglob("*") if p.is_file())
    with (directory/"SHA256SUMS").open("x") as stream:
        for p in paths:
            if p.is_symlink():raise ValueError("Evidence symlink rejected")
            stream.write(f"{sha(p)}  {p.relative_to(ROOT)}\n")
    return len(paths)
def main(pid,handle,runtime,pause):
    if (OUT/"SHA256SUMS").exists() or (FAILED/"SHA256SUMS").exists():raise ValueError("Never overwrite existing seals")
    for name in (runtime,pause):
        if Path(name).name!=name or not name.startswith("2026-10-06_"):raise ValueError("Exact inspected screenshot name required")
    baseline=json.loads((OUT/"fresh-normal-baseline.json").read_text())
    if any(json.loads((OUT/name).read_text())!=baseline for name in ("normal-restored.json","normal-exact-before-reopening.json")):
        raise ValueError("Ordinary saved/config/Mod bytes not exact before reopening")
    controls=baseline["instrumentationEntryPointsAbsent"]+["aqualumen-receiver-material-probe.properties"]
    if any((GAME/"config"/name).exists() for name in controls):raise ValueError("TEST entrypoint active")
    if {p.name:sha(p) for p in (GAME/"mods").glob("*.jar")}!=baseline["activeMods"]:raise ValueError("Normal Mods changed")
    if sha(GAME/"shaderpacks/Aqualumen-0.6.0.zip")!="6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73":raise ValueError("Normal pack changed")
    if "shaderPack=Aqualumen-0.6.0.zip" not in (GAME/"config/iris.properties").read_text():raise ValueError("Normal pack selection changed")
    proc=Path("/proc")/str(pid)
    if (proc/"comm").read_text().strip()!="java":raise ValueError("Normal Java not live")
    locks=[int(p.name) for p in (proc/"fd").iterdir() if p.readlink()==GAME/"saves/新規ワールド/session.lock"]
    if len(locks)!=1:raise ValueError("Ordinary world lock absent")
    log=(GAME/"logs/latest.log").read_text();chronology=verify_pause_event(log,runtime,pause)
    if ("OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti" not in log or "Using shaderpack: Aqualumen-0.6.0.zip" not in log
            or "0.2.0 contact bridge initialized" not in log or "aqualumen_receiver_material_probe" in log or "OpenGL debug message" in log):
        raise ValueError("Normal NVIDIA/Iris/physics evidence incomplete")
    paths=[OUT/"actual-texture-readback.json",ROOT/"reports/2026-10-06-water-coast-world/geometry-audit.json",
           OUT/"request.properties",OUT/"independent-stock-reference.json"]
    result=audit(json.loads(paths[0].read_text()),json.loads(paths[1].read_text()),paths[2].read_bytes(),json.loads(paths[3].read_text()))
    recorded=json.loads((OUT/"actual-atlas-audit.json").read_text())
    if any(recorded.get(k)!=v for k,v in result.items()):raise ValueError("GPU record audit drift")
    for name,digest in recorded["inputSHA256"].items():
        if sha(ROOT/name)!=digest:raise ValueError("Qualified input changed")
    receipt=json.loads((ROOT/"reports/2026-10-06-water-occluded-main/native-v4-receipt.json").read_text())
    for name,digest in receipt["sourceSHA256"].items():
        if sha(ROOT/name)!=digest:raise ValueError("Original water/native source changed: "+name)
    if sha(OUT/JAR)!="908feae33c6d20c5d395eadb7856ce5dfffbc20c8af24beb87d64e519dc2ce12":raise ValueError("Captured producer identity changed")
    if (OUT/JAR).read_bytes()!=(ROOT/"build"/JAR).read_bytes() or (OUT/JAR).read_bytes()!=(ROOT/"build/aqualumen-receiver-material-probe-0.1.2-atlas-v3-rebuild-v4.jar").read_bytes():
        raise ValueError("Captured producer differs from deterministic rebuild")
    copy(GAME/"logs/latest.log",OUT/"normal-final-runtime.log")
    for original,name in ((runtime,"normal-runtime.png"),(pause,"normal-pause.png"),
            ("2026-10-06_16.15.47.png","test-runtime.png"),("2026-10-06_16.16.43.png","test-save-quit-focus.png"),
            ("2026-10-06_16.18.03.png","test-title-quit-focus.png")):
        copy(GAME/"screenshots"/original,OUT/name)
    for original,name in (("2026-10-06_16.13.26.png","rejected-test-runtime.png"),("2026-10-06_16.14.00.png","test-save-quit-focus.png"),
            ("2026-10-06_16.14.41.png","test-title-quit-focus.png")):
        copy(GAME/"screenshots"/original,FAILED/name)
    checks={"atlas-decoder":["bash","tools/test-receiver-atlas.sh"],"GPU-evidence":["python3","tools/test_water_receiver_atlas_audit.py"],
        "surface-regression":["bash","tools/test-receiver-surface.sh"],"texture-regression":["bash","tools/test-receiver-texture.sh"],
        "geometry-regression":["bash","tools/test-receiver-field.sh"],"pause-chronology":["python3","tools/test_water_normal_pause_event.py"]}
    exits={}
    for name,command in checks.items():
        run=subprocess.run(["rtk","proxy",*command],cwd=ROOT,capture_output=True)
        with (OUT/(name+"-green.log")).open("xb") as stream:stream.write(run.stdout+run.stderr)
        exits[name]=run.returncode
        if run.returncode:raise ValueError("Affected CPU regression failed: "+name)
    sources=[ROOT/"physics-mod/dev/aqualumen/physics"/name for name in ("ReceiverAtlas.java","ReceiverTexture.java","ReceiverFace.java",
        "ReceiverField.java","ReceiverSurface.java","LoadedReceiverFaces.java","LoadedReceiverTexture.java","LoadedReceiverWorld.java",
        "LoadedWorld.java","BathymetryField.java")]
    sources.extend(p for p in (ROOT/"tools/receiver-material-probe").rglob("*") if p.is_file())
    sources.extend(ROOT/"physics-mod/test/dev/aqualumen/physics"/name for name in ("ReceiverAtlasTest.java","ReceiverTextureTest.java","ReceiverFaceTest.java"))
    sources.extend(ROOT/"tools"/name for name in ("build-receiver-material-probe.sh","test-receiver-atlas.sh","water_receiver_atlas_lifecycle.py",
        "water_receiver_atlas_retry_lifecycle.py","water_receiver_texture_lifecycle.py","water_receiver_atlas_audit.py",
        "test_water_receiver_atlas_audit.py","water_receiver_atlas_reference.py","water_receiver_texture_reference.py",
        "ReceiverTextureAssetReference.java","water_receiver_texture_audit.py","water_normal_pause_event.py","water_receiver_atlas_finish.py"))
    for source in sources:copy(source,OUT/"final-source"/source.relative_to(ROOT))
    checkpoint=dict(fullGoalAchieved=False,actualGPUAtlasPixelsQualified=True,actualGPUWholeSpriteMatches=48,actualGPUPointChecks=48,
        filteredTextureFetchProven=False,actualTerrainSamplerBindingProven=False,atlasReloadCoherenceProven=False,
        sourceUploaded=False,radianceComputed=False,productionVisualFixImplemented=False,originalShaderSourcesUnchanged=True,
        nativeV4REDsRemain=2,frameTimingMeasured=False,TESTClientExit=0,failedTESTClientExit=0,
        ordinaryHostJava=pid,ordinaryOwnedHandle=handle,ordinaryLockFD=locks[0],ordinarySavedFilesExactBeforeReopening=True,
        ordinarySaveRestored=False,ordinaryWorldAutomation=False,allOptInEntryPointsAbsent=controls,
        normalPackSHA256=sha(GAME/"shaderpacks/Aqualumen-0.6.0.zip"),normalPhysicsSHA256=sha(GAME/"mods/aqualumen-physics-0.2.0.jar"),
        runtimeScreenshot=runtime,pauseScreenshot=pause,rootInspectedRuntimeAndPause=True,pauseEventChronology=chronology,
        nativeGLAfterNormalRelaunch=False,publicCPUCheckExitCodes=exits,openALDeviceUnavailable="Failed to open OpenAL device" in log)
    with (OUT/"checkpoint.json").open("x") as stream:json.dump(checkpoint,stream,indent=2,sort_keys=True)
    print("Sealed qualified",seal(OUT),"and rejected",seal(FAILED),"files; GPU pixels qualified, water-source rendering still pending")
if __name__=="__main__":main(int(sys.argv[1]),int(sys.argv[2]),sys.argv[3],sys.argv[4])
