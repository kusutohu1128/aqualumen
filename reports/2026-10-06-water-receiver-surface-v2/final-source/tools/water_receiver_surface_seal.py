"""Read-only regression/integrity checks and exclusive offline surface packet seal."""
import hashlib
import json
from pathlib import Path
import subprocess
from water_normal_pause_event import verify_pause_event

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/2026-10-06-water-receiver-surface-v2"
TEXTURE=ROOT/"reports/2026-10-06-water-receiver-texture"
GAME=Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft")
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def copy(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open("xb") as stream:stream.write(source.read_bytes())
def main():
    if (OUT/"SHA256SUMS").exists():raise ValueError("Sealed packet is immutable")
    result=json.loads((OUT/"audit.json").read_text())
    if result["firstRefractedRayMaterialMatches"]!=16 or result["sourceUploaded"] or result["radianceComputed"] or result["fullGoalAchieved"]:
        raise ValueError("CPU material association scope changed")
    for group in ("inputs","sources"):
        for name,digest in result[group].items():
            if sha(ROOT/name)!=digest:raise ValueError("Replay input/producer changed: "+name)
    receipt=json.loads((ROOT/"reports/2026-10-06-water-occluded-main/native-v4-receipt.json").read_text())
    for name,digest in receipt["sourceSHA256"].items():
        if sha(ROOT/name)!=digest:raise ValueError("Original water MAIN/native control changed: "+name)
    for name in ("2026-10-06-water-receiver-texture","2026-10-06-water-receiver-contract-v3","2026-10-06-water-coast-world",
                 "2026-10-06-water-occluded-main","2026-10-06-water-receiver-faces","2026-10-06-water-receiver-faces-handoff-addendum"):
        subprocess.run(["rtk","proxy","sha256sum","--quiet","-c",str(ROOT/"reports"/name/"SHA256SUMS")],cwd=ROOT,check=True)
    run=subprocess.run(["rtk","proxy","python3","tools/test_water_receiver_surface_replay.py"],cwd=ROOT,capture_output=True)
    with (OUT/"material-request-dedup-green.log").open("xb") as stream:stream.write(run.stdout+run.stderr)
    if run.returncode:raise ValueError("Duplicate material request regression failed")
    normal=json.loads((TEXTURE/"checkpoint.json").read_text());base=json.loads((TEXTURE/"fresh-normal-baseline.json").read_text())
    pid=normal["ordinaryHostJava"];proc=Path("/proc")/str(pid)
    if (proc/"comm").read_text().strip()!="java":raise ValueError("Recorded ordinary process absent")
    lock=proc/"fd"/str(normal["ordinaryLockFD"])
    if lock.readlink()!=GAME/"saves/新規ワールド/session.lock":raise ValueError("Recorded ordinary lock changed")
    if {p.name:sha(p) for p in (GAME/"mods").glob("*.jar")}!=base["activeMods"]:raise ValueError("Ordinary Mods changed")
    if any((GAME/"config"/name).exists() for name in normal["allOptInEntryPointsAbsent"]):raise ValueError("Instrumentation active")
    if sha(GAME/"shaderpacks/Aqualumen-0.6.0.zip")!=normal["normalPackSHA256"]:raise ValueError("Normal shader changed")
    verify_pause_event((GAME/"logs/latest.log").read_text(),normal["runtimeScreenshot"],normal["pauseScreenshot"])
    for source in (Path(__file__).resolve(),ROOT/"tools/test_water_receiver_surface_replay.py",ROOT/"docs/RECEIVER_FIELD.md"):
        copy(source,OUT/"final-source"/source.relative_to(ROOT))
    checkpoint=dict(fullGoalAchieved=False,productionVisualFixImplemented=False,firstSurfaceInputAssociationImplemented=True,
        actualLiveFrameAtlasCoherenceProven=False,actualGPUFiltering=False,radianceComputed=False,sourceUploaded=False,
        originalShaderSourcesUnchanged=True,nativeV4REDsRemain=2,newMinecraftRun=False,newFrameTimings=False,
        ordinaryHostJava=pid,ordinaryOwnedHandle=normal["ordinaryOwnedHandle"],ordinaryLockFD=normal["ordinaryLockFD"],
        ordinarySettingsUnchanged=True,worldCommands=False,savesRestored=False,nativeGLAfterNormalRelaunch=False,
        ordinaryRootInspectedPauseEvidence="../2026-10-06-water-receiver-texture/normal-pause.png",
        allOptInEntryPointsAbsent=normal["allOptInEntryPointsAbsent"],replayCompileAndExecutionExitCodes=[0,0],
        dedupCheckExitCode=run.returncode)
    with (OUT/"checkpoint.json").open("x") as stream:json.dump(checkpoint,stream,indent=2,sort_keys=True)
    files=sorted(p for p in OUT.rglob("*") if p.is_file())
    with (OUT/"SHA256SUMS").open("x") as stream:
        for path in files:
            if path.is_symlink():raise ValueError("Evidence symlink rejected")
            stream.write(f"{sha(path)}  {path.relative_to(ROOT)}\n")
    print(f"Sealed {len(files)} files; exact CPU first-surface input implemented, GPU/radiance/visual fix pending")

if __name__=="__main__":main()
