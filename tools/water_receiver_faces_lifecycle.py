"""Exclusive read-only face-probe cycle in exact guarded TEST world; no world restore."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/2026-10-06-water-receiver-faces"
GAME=Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft")
JAR="aqualumen-receiver-material-probe-0.1.0-v1.jar"
HASH="9731f933b1f72cfaac94d44f0f401aaa063cd549035897feb11e9984b20739e6"
PROPERTY="aqualumen-receiver-material-probe.properties"
WORLD="b22dbccb-2970-41e6-847f-f183b1ec923d"


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
    with (OUT/name).open("x") as stream:json.dump(value,stream,indent=2,sort_keys=True)
def closed():
    if subprocess.run(["rtk","proxy","pgrep","-x","java"],stdout=subprocess.DEVNULL).returncode!=1:raise ValueError("Client must be closed")
def original(cache):return json.loads(subprocess.check_output(["rtk","proxy","python3","tools/water_legacy_branch_snapshot.py",str(cache)],cwd=ROOT))


def baseline():
    closed()
    if "All dimensions are saved" not in (GAME/"logs/latest.log").read_text():raise ValueError("Clean save not proven")
    if (GAME/"config"/PROPERTY).exists() or (GAME/"mods"/JAR).exists():raise ValueError("Unexpected pre-existing probe")
    OUT.mkdir(exist_ok=False)
    cache=Path(tempfile.mkdtemp(prefix="aqualumen-legacy-branch-host-receiver-faces-",dir="/home/kusutohu/.cache"))
    for name in ("options.txt","config/iris.properties","config/aqualumen-benchmark.properties"):
        target=cache/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(GAME/name,target)
    save("fresh-normal-baseline.json",original(cache));shutil.copy2(GAME/"logs/latest.log",OUT/"normal-clean-save-exit.log")
    print("NEW normal post-save baseline:",cache)


def install():
    closed();base=json.loads((OUT/"fresh-normal-baseline.json").read_text());cache=Path(base["backup"])
    if original(cache)!=base:raise ValueError("Ordinary state changed before TEST install")
    marker=dict(line.split("=",1) for line in (GAME/"saves/AqualumenNaturalV2/aqualumen-world.properties").read_text().splitlines())
    if marker.get("world_id")!=WORLD or marker.get("seed")!="308060" or marker.get("generator")!="minecraft:noise/overworld":raise ValueError("Guarded TEST marker mismatch")
    binary=ROOT/"build"/JAR
    if sha(binary)!=HASH:raise ValueError("Compiled probe identity mismatch")
    if (GAME/"config"/PROPERTY).exists() or (GAME/"mods"/JAR).exists():raise ValueError("No probe overwrite allowed")
    points=json.loads((ROOT/"reports/2026-10-06-water-coast-world/geometry-audit.json").read_text())["points"]
    if len(points)!=16:raise ValueError("Actual point count changed")
    request=str(uuid.uuid4())
    lines=["schema=1",f"world_id={WORLD}",f"request_id={request}",f"pack_sha256={sha(GAME/'shaderpacks/Aqualumen-0.6.0.zip')}"]
    for i,p in enumerate(points):
        hit=p["firstIntersection"]
        if hit["state"]!={"Name":"minecraft:sand"}:raise ValueError("Expected saved sand subset changed")
        lines.append(f"point.{i}="+",".join(map(str,[*hit["cell"],*hit["normal"]])))
    body="\n".join(lines)+"\n"
    with (GAME/"mods"/JAR).open("xb") as stream:stream.write(binary.read_bytes())
    with (GAME/"config"/PROPERTY).open("x") as stream:stream.write(body)
    with (OUT/"request.properties").open("x") as stream:stream.write(body)
    with (OUT/JAR).open("xb") as stream:stream.write(binary.read_bytes())
    save("install.json",dict(requestId=request,testWorldUUID=WORLD,probeSHA256=HASH,normalPhysicsUnchanged=True,worldWrites=False))
    print("Installed TEST-only face readback; normal physics unchanged; request:",request)


def launch(kind):
    closed();base=json.loads((OUT/"fresh-normal-baseline.json").read_text());cache=Path(base["backup"])
    if kind=="test":
        if sha(GAME/"mods"/JAR)!=HASH or (GAME/"config"/PROPERTY).read_bytes()!=(OUT/"request.properties").read_bytes():raise ValueError("Probe identity/request changed")
        world="AqualumenNaturalV2"
    else:
        if (GAME/"config"/PROPERTY).exists() or (GAME/"mods"/JAR).exists() or original(cache)!=base:raise ValueError("Normal state not exactly restored")
        save("normal-exact-before-reopening.json",original(cache));world="新規ワールド"
    descriptor=os.open(cache/(kind+"-launcher-private.log"),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    print(kind.upper(),"launch; authentication log private; no commands",flush=True)
    with os.fdopen(descriptor,"wb") as log:
        result=subprocess.run(["rtk","proxy","flatpak","run","--command=prismrun","org.prismlauncher.PrismLauncher","--launch","Aqualumen Lab","--world",world],cwd=ROOT,env=dict(os.environ,DISPLAY=":1"),stdout=log,stderr=subprocess.STDOUT)
    print(kind.upper(),"LAUNCHER EXIT",result.returncode,flush=True);raise SystemExit(result.returncode)


def collect():
    request=json.loads((OUT/"install.json").read_text())["requestId"]
    path=GAME/"aqualumen-receiver-material-probe"/(request+".json")
    with (OUT/"actual-face-readback.json").open("xb") as stream:stream.write(path.read_bytes())
    result=json.loads(path.read_text())
    shutil.copy2(GAME/"logs/latest.log",OUT/"test-face-runtime.log")
    if "error" in result:raise ValueError("Actual face capture failed: "+result["error"])
    if result["world_id"]!=WORLD or len(result["actualClientFaces"])!=16:raise ValueError("Actual face scope incomplete")
    print("Captured16 actual pinned vanilla faces; not shader/radiance upload")


def restore():
    closed();base=json.loads((OUT/"fresh-normal-baseline.json").read_text());cache=Path(base["backup"])
    if "All dimensions are saved" not in (GAME/"logs/latest.log").read_text():raise ValueError("Clean TEST save not proven")
    shutil.copy2(GAME/"logs/latest.log",OUT/"test-clean-save-exit.log")
    if sha(GAME/"mods"/JAR)!=HASH:raise ValueError("Probe identity changed")
    retained=cache/"disabled-probe";retained.mkdir(exist_ok=False)
    shutil.move(GAME/"mods"/JAR,retained/JAR);shutil.move(GAME/"config"/PROPERTY,retained/PROPERTY)
    for name,digest in base["configSHA256"].items():
        if sha(cache/name)!=digest:raise ValueError("Original config backup changed")
        shutil.copy2(cache/name,GAME/name)
    observed=original(cache)
    if observed!=base:raise ValueError("Ordinary saved/config/JAR bytes changed")
    save("normal-restored.json",observed);print("Probe disabled recoverably; normal41 saved/config/JAR files exact; no world restore")


if __name__=="__main__":
    import sys
    action=sys.argv[1]
    if action in ("test","normal"):launch(action)
    else:{"baseline":baseline,"install":install,"collect":collect,"restore":restore}[action]()
