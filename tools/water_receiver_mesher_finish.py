"""CPU-only actual-input provenance and safe ordinary handoff; exclusive seal."""
import json
from pathlib import Path
import subprocess
import sys
from water_receiver_mesher_audit import ROOT, OUT, audit, sha
from water_receiver_sun_finish import copy
from water_receiver_texture_lifecycle import GAME
from water_normal_pause_event import verify_pause_event


def main(pid, handle, runtime, pause):
    if (OUT / "SHA256SUMS").exists():
        raise ValueError("Never overwrite sealed evidence")
    for name in (runtime, pause):
        if Path(name).name != name or not name.startswith("2026-10-06_"):
            raise ValueError("Exact root-inspected screenshot names required")
    baseline = json.loads((OUT / "fresh-normal-baseline.json").read_text())
    for name in ("normal-restored.json", "normal-exact-before-reopening.json"):
        if json.loads((OUT / name).read_text()) != baseline:
            raise ValueError("Ordinary state not exact before reopening")
    controls = baseline["instrumentationEntryPointsAbsent"] + ["aqualumen-receiver-material-probe.properties", "aqualumen-receiver-mesher-probe.properties"]
    if any((GAME / "config" / name).exists() for name in controls):
        raise ValueError("TEST opt-in not disabled")
    if {p.name: sha(p) for p in (GAME / "mods").glob("*.jar")} != baseline["activeMods"]:
        raise ValueError("Ordinary3 Mods changed")
    pack = sha(GAME / "shaderpacks/Aqualumen-0.6.0.zip")
    if pack != "6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73" or "shaderPack=Aqualumen-0.6.0.zip" not in (GAME / "config/iris.properties").read_text():
        raise ValueError("Ordinary selected pack changed")
    proc = Path("/proc") / str(pid)
    if (proc / "comm").read_text().strip() != "java":
        raise ValueError("Actual normal Java not live")
    locks = [int(p.name) for p in (proc / "fd").iterdir() if p.readlink() == GAME / "saves/新規ワールド/session.lock"]
    if len(locks) != 1:
        raise ValueError("Actual ordinary ownership not proved")
    log = (GAME / "logs/latest.log").read_text()
    chronology = verify_pause_event(log, runtime, pause)
    if ("OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti" not in log
            or "Using shaderpack: Aqualumen-0.6.0.zip" not in log
            or "0.2.0 contact bridge initialized" not in log
            or "aqualumen_receiver_mesher_probe" in log or "OpenGL debug message" in log):
        raise ValueError("Actual normal NVIDIA/Iris/physics activation not proved")
    if json.loads((OUT / "independent-mesher-audit.json").read_text()) != audit():
        raise ValueError("Saved independent actual mesh audit changed")
    build = json.loads((OUT / "build-receipt.json").read_text())
    for name, digest in build["sourceSHA256"].items():
        if name != "tools/water_receiver_mesher_lifecycle.py" and sha(ROOT / name) != digest:
            raise ValueError("Actual compiled observer source changed")
    install = json.loads((OUT / "install.json").read_text())
    if sha(ROOT / "tools/water_receiver_mesher_lifecycle.py") != install["installationLifecycleSHA256"]:
        raise ValueError("Executed lifecycle changed")
    increments = {}
    for label in ("scope-red1", "scope-green1", "scope-final", "audit-red1", "audit-green1", "audit-final"):
        receipt = json.loads((OUT / label / "receipt.json").read_text())
        expected = 1 if "red" in label else 0
        if receipt["exitCode"] != expected:
            raise ValueError("Expected genuine increment result changed")
        for name, digest in receipt["sourceSHA256"].items():
            if sha(OUT / label / "source" / name) != digest:
                raise ValueError("Frozen CPU increment changed")
        if label in ("scope-final", "audit-final"):
            for name, digest in receipt["sourceSHA256"].items():
                if sha(ROOT / name) != digest:
                    raise ValueError("Final public CPU source changed")
        increments[label] = receipt["exitCode"]
    # Retain previous completed native shader qualification; never replay GL here.
    native = ROOT / "reports/2026-10-06-water-receiver-sun/native-v1/receipt.json"
    for name, digest in json.loads(native.read_text())["sourceSHA256"].items():
        if name.startswith("shaders/") and sha(ROOT / name) != digest:
            raise ValueError("Production GLSL changed after retained native qualification")
    exits = {}
    for name, command in {
            "public-mesher-audit": ["python3", "tools/test_water_receiver_mesher_audit.py"],
            "mesher-scope": ["bash", "tools/test-receiver-mesher-scope.sh"],
            "receiver-vertex-retained": ["bash", "tools/test-receiver-vertex.sh"],
            "pause-chronology": ["python3", "tools/test_water_normal_pause_event.py"]}.items():
        result = subprocess.run(["rtk", "proxy", *command], cwd=ROOT, capture_output=True)
        with (OUT / (name + "-green.log")).open("xb") as stream:
            stream.write(result.stdout + result.stderr)
        exits[name] = result.returncode
        if result.returncode:
            raise ValueError("Final CPU check failed: " + name)
    copy(GAME / "logs/latest.log", OUT / "normal-final-runtime.log")
    for original, name in ((runtime, "normal-runtime.png"), (pause, "normal-pause.png"),
            ("2026-10-06_17.04.08.png", "normal-save-quit-focus.png"), ("2026-10-06_17.05.36.png", "normal-title-quit-focus.png"),
            ("2026-10-06_17.07.35.png", "test-runtime.png"), ("2026-10-06_17.08.14.png", "test-save-quit-focus.png"),
            ("2026-10-06_17.10.11.png", "test-title-quit-focus.png")):
        copy(GAME / "screenshots" / original, OUT / name)
    sources = [ROOT / "docs/RECEIVER_FIELD.md", ROOT / "docs/REALISM_GOAL.md",
               ROOT / "physics-mod/dev/aqualumen/physics/ReceiverVertex.java",
               ROOT / "tools/test-receiver-mesher-scope.sh", ROOT / "tools/test_water_receiver_mesher_audit.py",
               ROOT / "tools/build-receiver-mesher-probe.sh", ROOT / "tools/water_receiver_sun_finish.py",
               ROOT / "tools/water_receiver_texture_lifecycle.py", ROOT / "tools/water_legacy_branch_snapshot.py",
               ROOT / "tools/water_normal_pause_event.py", ROOT / "tools/water_receiver_sun_audit.py",
               *sorted((ROOT / "tools").glob("water_receiver_mesher*.py")),
               *sorted((ROOT / "tools/receiver-mesher-probe").rglob("*"))]
    for source in dict.fromkeys(sources):
        if source.is_file():
            copy(source, OUT / "final-source" / source.relative_to(ROOT))
    checkpoint = dict(fullGoalAchieved=False, actualMinecraftMesherEncoderValidated=True,
        actualFaceCount=14, actualVertexCount=56, actualInitializedWordCount=280,
        shadedSourceRadiance=False, realSourceUploaded=False, dynamicIrisSourceBinding=False,
        liveGeometryResourceEpochProven=False, productionNaturalVisualFixAccepted=False,
        newMinecraftFrameTimings=False, nativeGLExecutedThisCycle=False, nativeGLAfterNormalRelaunch=False,
        ordinaryWorldAutomation=False, ordinarySaveRestored=False, ordinarySavedFilesExactBeforeReopening=True,
        previousOrdinaryOwnedHandle=51490, previousOrdinaryExit=0, testOwnedHandle=44144, testHostJava=3440419, testExit=0,
        normalPackSHA256=pack, normalPhysicsSHA256=sha(GAME / "mods/aqualumen-physics-0.2.0.jar"),
        ordinaryHostJava=pid, ordinaryOwnedHandle=handle, ordinaryLockFD=locks[0],
        allOptInEntryPointsAbsent=controls, runtimeScreenshot=runtime, pauseScreenshot=pause,
        rootInspectedRuntimeAndPause=True, rootInspectedTestView=True, actualTestVisualWaterStillCyanAndSerrated=True,
        pauseEventChronology=chronology, publicCPUCheckExitCodes=exits, incrementExitCodes=increments,
        openALDeviceUnavailable="Failed to open OpenAL device" in log)
    with (OUT / "checkpoint.json").open("x") as stream:
        json.dump(checkpoint, stream, indent=2, sort_keys=True)
    paths = sorted(p for p in OUT.rglob("*") if p.is_file())
    with (OUT / "SHA256SUMS").open("x") as stream:
        for path in paths:
            if path.is_symlink():
                raise ValueError("Evidence symlink rejected")
            stream.write(f"{sha(path)}  {path.relative_to(ROOT)}\n")
    print("Sealed", len(paths), "files; actual mesh input qualified, ordinary paused; full realism goal active")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4])
