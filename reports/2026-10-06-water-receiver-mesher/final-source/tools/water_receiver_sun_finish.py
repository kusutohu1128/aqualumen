"""CPU-only world-Sun/input provenance and ordinary handoff; never runs native GL."""
import json
from pathlib import Path
import subprocess
import sys

from water_normal_pause_event import verify_pause_event
from water_receiver_sun_audit import ROOT, OUT, audit, sha
from water_receiver_texture_lifecycle import GAME


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(source.read_bytes())


def main(pid, handle, runtime, pause):
    if (OUT / "SHA256SUMS").exists():
        raise ValueError("Never overwrite a sealed packet")
    for name in (runtime, pause):
        if Path(name).name != name or not name.startswith("2026-10-06_"):
            raise ValueError("Exact root-inspected screenshot names required")
    base = json.loads((OUT / "fresh-normal-baseline.json").read_text())
    if json.loads((OUT / "normal-exact-before-reopening.json").read_text()) != base:
        raise ValueError("Ordinary post-save state not exact before reopening")
    if len(base["ordinarySavedFilesSHA256"]) != 41:
        raise ValueError("Ordinary baseline scope changed")
    controls = base["instrumentationEntryPointsAbsent"] + ["aqualumen-receiver-material-probe.properties"]
    if any((GAME / "config" / name).exists() for name in controls):
        raise ValueError("TEST opt-in remains enabled")
    if {p.name: sha(p) for p in (GAME / "mods").glob("*.jar")} != base["activeMods"]:
        raise ValueError("Ordinary Mods changed")
    pack = sha(GAME / "shaderpacks/Aqualumen-0.6.0.zip")
    if pack != "6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73":
        raise ValueError("Ordinary pack changed")
    if "shaderPack=Aqualumen-0.6.0.zip" not in (GAME / "config/iris.properties").read_text():
        raise ValueError("Ordinary pack selection changed")
    proc = Path("/proc") / str(pid)
    if (proc / "comm").read_text().strip() != "java":
        raise ValueError("Ordinary Java not live")
    locks = [int(p.name) for p in (proc / "fd").iterdir()
             if p.readlink() == GAME / "saves/新規ワールド/session.lock"]
    if len(locks) != 1:
        raise ValueError("Ordinary-world ownership not proved")
    log = (GAME / "logs/latest.log").read_text()
    chronology = verify_pause_event(log, runtime, pause)
    if ("OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti" not in log
            or "Using shaderpack: Aqualumen-0.6.0.zip" not in log
            or "0.2.0 contact bridge initialized" not in log
            or "aqualumen_receiver_material_probe" in log or "OpenGL debug message" in log):
        raise ValueError("Fresh ordinary NVIDIA/Iris/physics activation not proved")
    if json.loads((OUT / "independent-world-sun-audit.json").read_text()) != audit():
        raise ValueError("Saved independent Sun audit changed")
    receipt = json.loads((OUT / "native-v1/receipt.json").read_text())
    for name, digest in receipt["sourceSHA256"].items():
        if sha(ROOT / name) != digest:
            raise ValueError("Qualified native shader/source changed: " + name)
    sodium = sha(GAME / "mods/sodium-fabric-0.6.9+mc1.21.1.jar")
    red_messages = ["Separate-AO actual input quad must be captured", "Nonfinite AO must remain unready",
                    "Unsupported light component bits cannot be silently discarded", "A nonfinite mesher coordinate"]
    increments = {}
    for index, message in enumerate(red_messages, 1):
        for phase in ("red", "green"):
            label = f"vertex-{phase}{index}"
            saved = json.loads((OUT / label / "receipt.json").read_text())
            expected = 1 if phase == "red" else 0
            if saved["exitCode"] != expected or saved["actualPinnedSodiumJarSHA256"] != sodium:
                raise ValueError("Actual CPU increment/library identity changed: " + label)
            for name, digest in saved["sourceSHA256"].items():
                if sha(OUT / label / "source" / name) != digest:
                    raise ValueError("Frozen CPU increment source changed")
            testlog = (OUT / label / "test.log").read_text()
            if phase == "red" and ("AssertionError: " + message not in testlog):
                raise ValueError("RED was not the declared behavior failure")
            if phase == "green" and "AssertionError" in testlog:
                raise ValueError("GREEN contains behavior failure")
            increments[label] = saved["exitCode"]
    final = json.loads((OUT / "vertex-green4/receipt.json").read_text())
    for name, digest in final["sourceSHA256"].items():
        if sha(ROOT / name) != digest:
            raise ValueError("Final vertex source changed: " + name)
    boundary = json.loads((OUT / "vertex-boundary/boundary.json").read_text())
    if boundary["sodiumJarSHA256"] != sodium or boundary["irisJarSHA256"] != sha(GAME / "mods/iris-fabric-1.8.8+mc1.21.1.jar"):
        raise ValueError("Pinned inspected boundary JARs changed")
    exits = {}
    for name, command in {
            "public-sun-audit": ["python3", "tools/test_water_receiver_sun_audit.py"],
            "receiver-vertex-final": ["bash", "tools/test-receiver-vertex.sh"],
            "pause-chronology": ["python3", "tools/test_water_normal_pause_event.py"]}.items():
        result = subprocess.run(["rtk", "proxy", *command], cwd=ROOT, capture_output=True)
        with (OUT / (name + "-green.log")).open("xb") as stream:
            stream.write(result.stdout + result.stderr)
        exits[name] = result.returncode
        if result.returncode:
            raise ValueError("Final CPU check failed: " + name)
    copy(GAME / "logs/latest.log", OUT / "normal-final-runtime.log")
    for source, name in ((runtime, "normal-runtime.png"), (pause, "normal-pause.png"),
                         ("2026-10-06_16.43.20.png", "normal-save-quit-focus.png"),
                         ("2026-10-06_16.44.21.png", "normal-title-quit-focus.png")):
        copy(GAME / "screenshots" / source, OUT / name)
    files = [ROOT / "README.md", ROOT / "docs/RECEIVER_FIELD.md", ROOT / "docs/REALISM_GOAL.md",
             ROOT / "physics-mod/dev/aqualumen/physics/ReceiverVertex.java",
             ROOT / "physics-mod/test/dev/aqualumen/physics/ReceiverVertexTest.java",
             ROOT / "tools/test-receiver-vertex.sh", ROOT / "tools/water_normal_pause_event.py",
             ROOT / "tools/water_receiver_texture_lifecycle.py", ROOT / "tools/water_legacy_branch_snapshot.py",
             ROOT / "tools/water_receiver_main_audit.py", ROOT / "tools/water_occluded_receiver_audit.py",
             ROOT / "tools/test_water_receiver_sun_audit.py", ROOT / "tools/water_receiver_vertex_record.py",
             ROOT / "tools/water_receiver_vertex_boundary.py", *sorted((ROOT / "tools").glob("water_receiver_sun*.py"))]
    for source in dict.fromkeys(files):
        copy(source, OUT / "final-source" / source.relative_to(ROOT))
    checkpoint = dict(fullGoalAchieved=False, nonzeroWorldSourceSunValidatedForFlatSyntheticFixture=True,
        originalProductionShaderUnchanged=True, cpuPinnedVertexInputPrepared=True,
        actualMinecraftMesherCapture=False, liveMinecraftSourceProducer=False,
        realMaterialSourceUploaded=False, productionNaturalVisualFixAccepted=False,
        newMinecraftFrameTimings=False, normalPackSHA256=pack,
        normalPhysicsSHA256=sha(GAME / "mods/aqualumen-physics-0.2.0.jar"),
        ordinarySavedFilesExactBeforeReopening=True, ordinarySaveRestored=False,
        ordinaryWorldAutomation=False, previousOrdinaryOwnedHandle=44488, previousOrdinaryExit=0,
        ordinaryHostJava=pid, ordinaryOwnedHandle=handle, ordinaryLockFD=locks[0],
        allOptInEntryPointsAbsent=controls, nativeGLAfterNormalRelaunch=False,
        runtimeScreenshot=runtime, pauseScreenshot=pause, rootInspectedRuntimeAndPause=True,
        pauseEventChronology=chronology, publicCPUCheckExitCodes=exits,
        vertexIncrementExitCodes=increments, openALDeviceUnavailable="Failed to open OpenAL device" in log)
    with (OUT / "checkpoint.json").open("x") as stream:
        json.dump(checkpoint, stream, indent=2, sort_keys=True)
    paths = sorted(p for p in OUT.rglob("*") if p.is_file())
    with (OUT / "SHA256SUMS").open("x") as stream:
        for path in paths:
            if path.is_symlink():
                raise ValueError("Evidence symlink rejected")
            stream.write(f"{sha(path)}  {path.relative_to(ROOT)}\n")
    print("Sealed", len(paths), "files; flat synthetic Sun/input qualified; ordinary paused; full goal active")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4])
