"""CPU-only final provenance/ordinary-handoff check and exclusive evidence seal."""
import json
from pathlib import Path
import subprocess
import sys
from water_normal_pause_event import verify_pause_event
from water_receiver_main_audit import OUT, ROOT, audit, sha
from water_receiver_unready_audit import audit as unready_audit
from water_receiver_absent_audit import audit as absent_audit
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
            raise ValueError("Exact independently inspected screenshot names required")
    base = json.loads((OUT / "fresh-normal-baseline.json").read_text())
    if json.loads((OUT / "normal-exact-before-reopening.json").read_text()) != base:
        raise ValueError("Ordinary post-save state was not exact before reopening")
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
    audits = [("independent-audit-v3.json", audit(revision="v3")),
              ("unready-independent-audit.json", unready_audit()),
              ("absent-independent-audit.json", absent_audit())]
    for name, result in audits:
        if json.loads((OUT / name).read_text()) != result:
            raise ValueError("Independent saved audit changed: " + name)
    receipt = json.loads((OUT / "native-v3-receipt.json").read_text())
    for name, digest in receipt["sourceSHA256"].items():
        if sha(ROOT / name) != digest:
            raise ValueError("Final native shader/source changed: " + name)
    retained = OUT / "retained-regressions"
    reg = json.loads((retained / "receipt.json").read_text())
    if (len(reg["runs"]) != 3 or any(r["exitCode"] != 0 or not r["actualNvidiaRenderer"] for r in reg["runs"])
            or not reg["sourceUnchangedDuringRun"]
            or sha(retained / "source/build/glcheck") != reg["nativeBinarySHA256"]):
        raise ValueError("Actual retained native gates not qualified")
    for name, digest in reg["sourceSHA256"].items():
        if sha(retained / "source" / name) != digest or sha(ROOT / name) != digest:
            raise ValueError("Native regression source provenance changed")
    checks = {"public-main-audit": ["python3", "tools/test_water_receiver_main_audit.py"],
              "pause-chronology": ["python3", "tools/test_water_normal_pause_event.py"]}
    exits = {}
    for name, command in checks.items():
        actual = subprocess.run(["rtk", "proxy", *command], cwd=ROOT, capture_output=True)
        with (OUT / (name + "-green.log")).open("xb") as stream:
            stream.write(actual.stdout + actual.stderr)
        exits[name] = actual.returncode
        if actual.returncode:
            raise ValueError("CPU audit failed: " + name)
    copy(GAME / "logs/latest.log", OUT / "normal-final-runtime.log")
    for source, name in ((runtime, "normal-runtime.png"), (pause, "normal-pause.png"),
                         ("2026-10-06_16.28.12.png", "normal-save-quit-focus.png"),
                         ("2026-10-06_16.28.41.png", "normal-title-quit-focus.png")):
        copy(GAME / "screenshots" / source, OUT / name)
    files = [ROOT / "README.md", ROOT / "docs/RECEIVER_FIELD.md", ROOT / "docs/REALISM_GOAL.md",
             ROOT / "shaders/gbuffers_water.fsh", ROOT / "shaders/lib/water_receiver.glsl",
             *sorted((ROOT / "tools").glob("water_receiver_*main*.py")),
             *sorted((ROOT / "tools").glob("water_receiver_unready*.py")),
             ROOT / "tools/water_receiver_absent_audit.py", ROOT / "tools/water_receiver_regression_run.py",
             ROOT / "tools/test_water_receiver_main_audit.py", ROOT / "tools/water_normal_pause_event.py",
             ROOT / "tools/water_receiver_texture_lifecycle.py", ROOT / "tools/water_legacy_branch_snapshot.py",
             ROOT / "tools/water_occluded_receiver_run.py", ROOT / "tools/water_occluded_receiver_audit.py"]
    for source in dict.fromkeys(files):
        copy(source, OUT / "final-source" / source.relative_to(ROOT))
    checkpoint = dict(fullGoalAchieved=False, syntheticFirstSourceNativeCorrected=True,
        syntheticUnreadyFirstSourceGuardCorrected=True, originalWholeInputsPreserved=True,
        liveMinecraftSourceProducer=False, realMaterialSourceUploaded=False,
        nonzeroWorldSourceSunValidated=False, productionNaturalVisualFixAccepted=False,
        newMinecraftFrameTimings=False, normalPackSHA256=pack,
        normalPhysicsSHA256=sha(GAME / "mods/aqualumen-physics-0.2.0.jar"),
        ordinarySavedFilesExactBeforeReopening=True, ordinarySaveRestored=False,
        ordinaryWorldAutomation=False, previousOrdinaryOwnedHandle=79690, previousOrdinaryExit=0,
        ordinaryHostJava=pid, ordinaryOwnedHandle=handle, ordinaryLockFD=locks[0],
        allOptInEntryPointsAbsent=controls, nativeGLAfterNormalRelaunch=False,
        runtimeScreenshot=runtime, pauseScreenshot=pause, rootInspectedRuntimeAndPause=True,
        pauseEventChronology=chronology, publicCPUCheckExitCodes=exits,
        openALDeviceUnavailable="Failed to open OpenAL device" in log)
    with (OUT / "checkpoint.json").open("x") as stream:
        json.dump(checkpoint, stream, indent=2, sort_keys=True)
    paths = sorted(p for p in OUT.rglob("*") if p.is_file())
    with (OUT / "SHA256SUMS").open("x") as stream:
        for path in paths:
            if path.is_symlink():
                raise ValueError("Evidence symlink rejected")
            stream.write(f"{sha(path)}  {path.relative_to(ROOT)}\n")
    print("Sealed", len(paths), "files; synthetic MAIN corrected, ordinary restored; full goal remains active")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4])
