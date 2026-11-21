"""Exclusive actual-texel packet and verified ordinary handoff; no GL or world writes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from water_normal_pause_event import verify_pause_event
from water_receiver_texture_audit import audit

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/2026-10-06-water-receiver-texture"
GAME=Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft")
PROBE="aqualumen-receiver-material-probe-0.1.1-texture-v1.jar"
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def copy(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open("xb") as stream:stream.write(source.read_bytes())
def main(pid,handle,runtime,pause):
    if (OUT/"SHA256SUMS").exists():raise ValueError("Never modify a sealed packet")
    for name in (runtime,pause):
        if Path(name).name!=name or not name.startswith("2026-10-06_"):raise ValueError("Exact screenshot name required")
    base=json.loads((OUT/"fresh-normal-baseline.json").read_text())
    if any(json.loads((OUT/name).read_text())!=base for name in ("normal-restored.json","normal-exact-before-reopening.json")):
        raise ValueError("Saved/config/mod bytes were not exact before reopening")
    if {p.name:sha(p) for p in (GAME/"mods").glob("*.jar")}!=base["activeMods"]:raise ValueError("Ordinary Mods changed")
    controls=base["instrumentationEntryPointsAbsent"]+["aqualumen-receiver-material-probe.properties"]
    if any((GAME/"config"/name).exists() for name in controls):raise ValueError("TEST entrypoint active")
    if any(p.name.startswith("aqualumen-receiver-material-probe-") for p in (GAME/"mods").glob("*.jar")):raise ValueError("Probe active")
    if sha(GAME/"shaderpacks/Aqualumen-0.6.0.zip")!="6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73":raise ValueError("Normal shader changed")
    if "shaderPack=Aqualumen-0.6.0.zip" not in (GAME/"config/iris.properties").read_text():raise ValueError("Normal shader not selected")
    proc=Path("/proc")/str(pid)
    if (proc/"comm").read_text().strip()!="java":raise ValueError("Actual ordinary Java absent")
    locks=[int(p.name) for p in (proc/"fd").iterdir() if p.readlink()==GAME/"saves/新規ワールド/session.lock"]
    if len(locks)!=1:raise ValueError("Actual ordinary lock not held")
    reference=json.loads((OUT/"independent-stock-reference.json").read_text())
    if reference["uniqueSynchronousCompileExitCode"]!=0 or reference["decoderExitCode"]!=0:raise ValueError("Independent decoder not executed")
    if reference["sourceSHA256"]!=sha(ROOT/"tools/ReceiverTextureAssetReference.java"):raise ValueError("Decoder source changed")
    raw=OUT/"actual-texture-readback.json";geometry=ROOT/"reports/2026-10-06-water-coast-world/geometry-audit.json"
    result=audit(json.loads(raw.read_text()),json.loads(geometry.read_text()),(OUT/"request.properties").read_bytes(),reference)
    recorded=json.loads((OUT/"actual-texture-audit.json").read_text())
    if any(recorded.get(k)!=v for k,v in result.items()):raise ValueError("Actual texture audit drift")
    for name,digest in recorded["inputSHA256"].items():
        if sha(ROOT/name)!=digest:raise ValueError("Frozen input changed")
    receipt=json.loads((ROOT/"reports/2026-10-06-water-occluded-main/native-v4-receipt.json").read_text())
    for name,digest in receipt["sourceSHA256"].items():
        if sha(ROOT/name)!=digest:raise ValueError("Retained original-MAIN source changed: "+name)
    if sha(OUT/PROBE)!="a3387c9ced746600b5649af895850d00611f5f7e27303aa9a10491dc3a7f749c":raise ValueError("Captured producer identity changed")
    if (OUT/PROBE).read_bytes()!=(ROOT/"build"/PROBE).read_bytes() or (OUT/PROBE).read_bytes()!=(ROOT/"build/aqualumen-receiver-material-probe-0.1.1-texture-rebuild-v2.jar").read_bytes():
        raise ValueError("Deterministic source build differs")
    log=(GAME/"logs/latest.log").read_text()
    chronology=verify_pause_event(log,runtime,pause)
    if ("OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti" not in log or "Using shaderpack: Aqualumen-0.6.0.zip" not in log
            or "0.2.0 contact bridge initialized" not in log or "aqualumen_receiver_material_probe" in log or "OpenGL debug message" in log):
        raise ValueError("Ordinary NVIDIA/pack/physics evidence missing")
    copy(GAME/"logs/latest.log",OUT/"normal-final-runtime.log")
    for original,name in ((runtime,"normal-runtime.png"),(pause,"normal-pause.png"),
            ("2026-10-06_15.51.15.png","test-runtime.png"),("2026-10-06_15.51.51.png","test-save-quit-focus.png"),
            ("2026-10-06_15.53.09.png","test-title-quit-focus.png")):
        copy(GAME/"screenshots"/original,OUT/name)
    checks={"texture-decoder":["bash","tools/test-receiver-texture.sh"],
        "texture-evidence":["python3","tools/test_water_receiver_texture_audit.py"],
        "face-regression":["bash","tools/test-receiver-face.sh"],
        "geometry-regression":["bash","tools/test-receiver-field.sh"],
        "bathymetry-regression":["bash","tools/test-physics-mod.sh"],
        "pause-chronology":["python3","tools/test_water_normal_pause_event.py"]}
    exits={}
    for name,command in checks.items():
        run=subprocess.run(["rtk","proxy",*command],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        with (OUT/(name+"-green.log")).open("xb") as stream:stream.write(run.stdout)
        exits[name]=run.returncode
        if run.returncode:raise ValueError("CPU regression failed: "+name)
    sources=[ROOT/"physics-mod/dev/aqualumen/physics"/name for name in
        ("ReceiverField.java","ReceiverFace.java","ReceiverTexture.java","LoadedReceiverWorld.java","LoadedReceiverFaces.java",
         "LoadedReceiverTexture.java","LoadedWorld.java","BathymetryField.java")]
    sources.extend(p for p in (ROOT/"tools/receiver-material-probe").rglob("*") if p.is_file())
    sources.extend(ROOT/"physics-mod/test/dev/aqualumen/physics"/name for name in ("ReceiverFaceTest.java","ReceiverTextureTest.java"))
    sources.extend(ROOT/"tools"/name for name in ("build-receiver-material-probe.sh","test-receiver-texture.sh",
        "ReceiverTextureAssetReference.java","water_receiver_texture_reference.py","water_receiver_texture_audit.py",
        "test_water_receiver_texture_audit.py","water_receiver_texture_lifecycle.py","water_receiver_texture_finish.py",
        "water_normal_pause_event.py","test_water_normal_pause_event.py"))
    sources.append(ROOT/"docs/RECEIVER_FIELD.md")
    for source in sources:copy(source,OUT/"final-source"/source.relative_to(ROOT))
    checkpoint=dict(schema="aqualumen-actual-texel-checkpoint-v1",fullGoalAchieved=False,
        actualCPUTextureReadback=True,faceObservations=48,sparsePixelChecks=240,
        radianceComputed=False,GPUAtlasPixelReadback=False,sourceUploaded=False,productionVisualFixImplemented=False,
        productionShaderSourcesUnchanged=True,nativeRendererREDsRemain=2,frameTimingMeasured=False,
        ordinaryHostJava=pid,ordinaryOwnedHandle=handle,ordinaryLockFD=locks[0],
        ordinarySavedFilesExactBeforeReopening=True,ordinarySaveRestored=False,ordinaryWorldAutomation=False,
        TESTInstrumentationRecoverablyDisabled=True,allOptInEntryPointsAbsent=controls,nativeGLAfterNormalRelaunch=False,
        normalPackSHA256=sha(GAME/"shaderpacks/Aqualumen-0.6.0.zip"),normalPhysicsSHA256=sha(GAME/"mods/aqualumen-physics-0.2.0.jar"),
        installedAndRebuiltProbeSHA256=sha(OUT/PROBE),publicCPUCheckExitCodes=exits,
        runtimeScreenshot=runtime,pauseScreenshot=pause,rootInspectedRuntimeAndPause=True,pauseEventChronology=chronology,
        openALDeviceUnavailable="Failed to open OpenAL device" in log)
    with (OUT/"checkpoint.json").open("x") as stream:json.dump(checkpoint,stream,indent=2,sort_keys=True)
    files=sorted(p for p in OUT.rglob("*") if p.is_file())
    with (OUT/"SHA256SUMS").open("x") as stream:
        for path in files:
            if path.is_symlink():raise ValueError("Evidence symlink rejected")
            stream.write(f"{sha(path)}  {path.relative_to(ROOT)}\n")
    print(f"Sealed {len(files)} files: actual48/240 CPU texels and ordinary handoff, not radiance or water fix")

if __name__=="__main__":main(int(sys.argv[1]),int(sys.argv[2]),sys.argv[3],sys.argv[4])
