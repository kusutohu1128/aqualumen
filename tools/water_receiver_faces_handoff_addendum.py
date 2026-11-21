"""Readonly corrected ordinary-pause packet; never rewrite the original seal."""
import hashlib
import json
from pathlib import Path
import subprocess
from water_normal_pause_event import verify_pause_event

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/"reports/2026-10-06-water-receiver-faces"
OUT=ROOT/"reports/2026-10-06-water-receiver-faces-handoff-addendum"
GAME=Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft")

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(p,name):
    with (OUT/name).open("xb") as stream:stream.write(p.read_bytes())

def main():
    if (OUT/"SHA256SUMS").exists():raise ValueError("Addendum already sealed")
    subprocess.run(["rtk","proxy","sha256sum","--quiet","-c",str(OLD/"SHA256SUMS")],cwd=ROOT,check=True)
    baseline=json.loads((OLD/"fresh-normal-baseline.json").read_text())
    if baseline!=json.loads((OLD/"normal-restored.json").read_text()) or baseline!=json.loads((OLD/"normal-exact-before-reopening.json").read_text()):
        raise ValueError("Before-reopening exactness not proven")
    mods={p.name:sha(p) for p in (GAME/"mods").glob("*.jar")}
    if mods!=baseline["activeMods"]:raise ValueError("Normal three Mods changed")
    controls=baseline["instrumentationEntryPointsAbsent"]+["aqualumen-receiver-material-probe.properties"]
    if any((GAME/"config"/name).exists() for name in controls):raise ValueError("TEST opt-in present")
    pack=GAME/"shaderpacks/Aqualumen-0.6.0.zip"
    if sha(pack)!="6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73" or "shaderPack=Aqualumen-0.6.0.zip" not in (GAME/"config/iris.properties").read_text():
        raise ValueError("Normal pack changed")
    proc=Path("/proc/3335948")
    if (proc/"comm").read_text().strip()!="java" or (proc/"fd/154").readlink()!=GAME/"saves/新規ワールド/session.lock":
        raise ValueError("Same actual normal Java/ordinary lock not live")
    log=(GAME/"logs/latest.log").read_text()
    scope=verify_pause_event(log,"2026-10-06_15.35.48.png","2026-10-06_15.36.17.png")
    if "aqualumen_receiver_material_probe" in log or "Using shaderpack: Aqualumen-0.6.0.zip" not in log or "0.2.0 contact bridge initialized" not in log:
        raise ValueError("Normal runtime identity failed")
    copy(GAME/"logs/latest.log","corrected-normal-runtime.log")
    for stamp,name in [("15.35.08","intermediate-inventory-not-pause.png"),("15.35.48","corrected-normal-runtime.png"),("15.36.17","corrected-normal-pause.png")]:
        copy(GAME/"screenshots"/("2026-10-06_"+stamp+".png"),name)
    result=subprocess.run(["rtk","proxy","python3","tools/test_water_normal_pause_event.py"],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    with (OUT/"pause-event-regression-green.log").open("xb") as stream:stream.write(result.stdout)
    if result.returncode:raise ValueError("Pause chronology regression failed")
    for name in ("water_normal_pause_event.py","test_water_normal_pause_event.py","water_receiver_faces_finish.py","water_receiver_faces_handoff_addendum.py"):
        copy(ROOT/"tools"/name,name)
    checkpoint=dict(schema="aqualumen-actual-face-handoff-correction-v1",originalPacketSealSHA256=sha(OLD/"SHA256SUMS"),
        originalFinalPauseClaimValid=False,actual16FaceEvidenceStillValid=True,ordinarySavedExactBeforeReopeningStillValid=True,
        correctedNormalRuntimeAndGameMenuRootInspected=True,orderedFreshPause=scope,ordinaryHostJava=3335948,ordinaryOwnedHandle=92351,
        ordinaryLockFD=154,activeModsSHA256=mods,normalPackSHA256=sha(pack),allTESTOptInsAbsent=controls,
        ordinaryWorldCommands=False,ordinarySaveRestored=False,nativeGLAfterNormalRelaunch=False,newFrameTiming=False,
        fullGoalAchieved=False,productionWaterFixImplemented=False)
    with (OUT/"checkpoint.json").open("x") as stream:json.dump(checkpoint,stream,indent=2,sort_keys=True)
    files=sorted(p for p in OUT.rglob("*") if p.is_file())
    with (OUT/"SHA256SUMS").open("x") as stream:
        for p in files:
            if p.is_symlink():raise ValueError("Addendum symlink rejected")
            stream.write(f"{sha(p)}  {p.relative_to(ROOT)}\n")
    print(f"Sealed {len(files)} corrected handoff files; old pause rejected, fresh actual normal menu qualified")

if __name__=="__main__":main()
