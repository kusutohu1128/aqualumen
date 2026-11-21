"""Readonly ordinary-handoff checks and exclusive occluded-MAIN evidence seal."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/2026-10-06-water-occluded-main"
GAME=Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft")


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if (OUT/"SHA256SUMS").exists(): raise ValueError("Evidence seal must never be replaced")
    baseline=json.loads((OUT/"fresh-normal-baseline.json").read_text())
    restored=json.loads((OUT/"normal-unchanged-before-reopening.json").read_text())
    if baseline!=restored: raise ValueError("Ordinary state differed before reopening")
    if {p.name:sha(p) for p in (GAME/"mods").glob("*.jar")}!=baseline["activeMods"]: raise ValueError("Ordinary Mod changed")
    if any((GAME/"config"/name).exists() for name in baseline["instrumentationEntryPointsAbsent"]): raise ValueError("TEST entrypoint present")
    pack=GAME/"shaderpacks/Aqualumen-0.6.0.zip"
    if sha(pack)!="6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73": raise ValueError("Ordinary pack changed")
    if "shaderPack=Aqualumen-0.6.0.zip" not in (GAME/"config/iris.properties").read_text(): raise ValueError("Ordinary Iris selection changed")
    process=Path("/proc/3317128")
    if (process/"comm").read_text().strip()!="java" or (process/"fd/154").readlink()!=GAME/"saves/新規ワールド/session.lock":
        raise ValueError("New ordinary process/lock not live")
    audit=json.loads((OUT/"independent-audit.json").read_text())
    if audit["qualifiedRendererRedCount"]!=2 or audit["fullGoalAchieved"]: raise ValueError("Qualified RED scope changed")
    source=json.loads((OUT/"native-v4-receipt.json").read_text())["sourceSHA256"]
    for name,digest in source.items():
        if sha(ROOT/name)!=digest: raise ValueError("Production/test source changed after v4")
    for stamp,name in [("15.11.27","normal-runtime.png"),("15.11.33","normal-pause.png")]:
        with (OUT/name).open("xb") as stream: stream.write((GAME/"screenshots"/f"2026-10-06_{stamp}.png").read_bytes())
    checkpoint=dict(fullGoalAchieved=False,productionFixImplemented=False,qualifiedNativeRedCount=2,
                    ordinaryHostJava=3317128,ordinaryLockFD=154,ordinaryLiveOwnedHandle=41749,
                    ordinarySavedFilesExactBeforeReopening=True,ordinarySaveRestored=False,
                    ordinaryWorldAutomation=False,TESTInstalled=False,allOptInEntryPointsAbsent=True,
                    nativeGLAfterNormalRelaunch=False,newMinecraftFrameTiming=False,
                    normalPackSHA256=sha(pack),normalPhysicsSHA256=sha(GAME/"mods/aqualumen-physics-0.2.0.jar"),
                    runtimeScreenshot="normal-runtime.png",pauseScreenshot="normal-pause.png")
    with (OUT/"checkpoint.json").open("x") as stream: json.dump(checkpoint,stream,indent=2,sort_keys=True)
    for path in [Path(__file__).resolve(),ROOT/"tools/water_occluded_receiver_audit.py"]:
        destination=OUT/"final-tool-source"/path.name;destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open("xb") as stream: stream.write(path.read_bytes())
    files=sorted(path for path in OUT.rglob("*") if path.is_file())
    with (OUT/"SHA256SUMS").open("x") as stream:
        for path in files:
            if path.is_symlink(): raise ValueError("Evidence symlink rejected")
            stream.write(f"{sha(path)}  {path.relative_to(ROOT)}\n")
    print(f"Sealed {len(files)} files; two qualified REDs and safe normal handoff, not goal completion.")


if __name__=="__main__": main()
