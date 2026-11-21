"""Exclusive guarded warmed CPU-sprite probe cycle; preserve all ordinary saves."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/2026-10-06-water-receiver-texture"
GAME=Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft")
JAR="aqualumen-receiver-material-probe-0.1.1-texture-v1.jar"
HASH="a3387c9ced746600b5649af895850d00611f5f7e27303aa9a10491dc3a7f749c"
PROPERTY="aqualumen-receiver-material-probe.properties"
WORLD="b22dbccb-2970-41e6-847f-f183b1ec923d"

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
    with (OUT/name).open("x") as stream:json.dump(value,stream,indent=2,sort_keys=True)
def copy(p,name):
    with (OUT/name).open("xb") as stream:stream.write(p.read_bytes())
def closed():
    if subprocess.run(["rtk","proxy","pgrep","-x","java"],stdout=subprocess.DEVNULL).returncode!=1:raise ValueError("Actual client must be closed")
def original(cache):return json.loads(subprocess.check_output(["rtk","proxy","python3","tools/water_legacy_branch_snapshot.py",str(cache)],cwd=ROOT))

def baseline():
    closed()
    if "All dimensions are saved" not in (GAME/"logs/latest.log").read_text():raise ValueError("Clean normal save not proven")
    if (GAME/"config"/PROPERTY).exists() or any(p.name.startswith("aqualumen-receiver-material-probe-") for p in (GAME/"mods").glob("*.jar")):
        raise ValueError("Unexpected pre-existing receiver probe")
    OUT.mkdir(exist_ok=False)
    cache=Path(tempfile.mkdtemp(prefix="aqualumen-legacy-branch-host-receiver-texture-",dir="/home/kusutohu/.cache"))
    for name in ("options.txt","config/iris.properties","config/aqualumen-benchmark.properties"):
        target=cache/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(GAME/name,target)
    save("fresh-normal-baseline.json",original(cache));copy(GAME/"logs/latest.log","normal-clean-save-exit.log")
    print("NEW normal post-save baseline:",cache)

def install():
    closed();base=json.loads((OUT/"fresh-normal-baseline.json").read_text());cache=Path(base["backup"])
    if original(cache)!=base:raise ValueError("Ordinary state changed before install")
    marker=dict(line.split("=",1) for line in (GAME/"saves/AqualumenNaturalV2/aqualumen-world.properties").read_text().splitlines())
    if marker.get("world_id")!=WORLD or marker.get("seed")!="308060" or marker.get("generator")!="minecraft:noise/overworld":raise ValueError("TEST marker mismatch")
    binary=ROOT/"build"/JAR
    if sha(binary)!=HASH:raise ValueError("Actual compiled artifact identity mismatch")
    if (GAME/"config"/PROPERTY).exists() or (GAME/"mods"/JAR).exists():raise ValueError("No probe overwrite")
    points=json.loads((ROOT/"reports/2026-10-06-water-coast-world/geometry-audit.json").read_text())["points"]
    if len(points)!=16:raise ValueError("Saved point count changed")
    request=str(uuid.uuid4())
    lines=["schema=2",f"world_id={WORLD}",f"request_id={request}",f"pack_sha256={sha(GAME/'shaderpacks/Aqualumen-0.6.0.zip')}"]
    for i,p in enumerate(points):
        hit=p["firstIntersection"]
        if hit["state"]!={"Name":"minecraft:sand"}:raise ValueError("Requested sand subset changed")
        lines.append(f"point.{i}="+",".join(map(str,hit["cell"]+hit["normal"])))
        axis=next(a for a,n in enumerate(hit["normal"]) if n)
        local=[hit["point"][a]-hit["cell"][a] for a in ((axis+1)%3,(axis+2)%3)]
        if not all(0<=v<=1 for v in local):raise ValueError("Saved local point outside face")
        lines.append(f"local.{i}="+",".join(map(repr,local)))
    body="\n".join(lines)+"\n"
    with (GAME/"mods"/JAR).open("xb") as stream:stream.write(binary.read_bytes())
    with (GAME/"config"/PROPERTY).open("x") as stream:stream.write(body)
    with (OUT/"request.properties").open("x") as stream:stream.write(body)
    copy(binary,JAR)
    save("install.json",dict(requestId=request,worldUUID=WORLD,probeSHA256=HASH,normalPhysicsUnchanged=True,worldWrites=False,shaderSourceChanged=False))
    print("Installed TEST-only0.1.1 actual sprite probe, request:",request)

def launch(kind):
    closed();base=json.loads((OUT/"fresh-normal-baseline.json").read_text());cache=Path(base["backup"])
    if kind=="test":
        if sha(GAME/"mods"/JAR)!=HASH or (GAME/"config"/PROPERTY).read_bytes()!=(OUT/"request.properties").read_bytes():raise ValueError("Probe request/artifact changed")
        world="AqualumenNaturalV2"
    else:
        if (GAME/"config"/PROPERTY).exists() or (GAME/"mods"/JAR).exists() or original(cache)!=base:raise ValueError("Normal state not exactly restored")
        save("normal-exact-before-reopening.json",original(cache));world="新規ワールド"
    descriptor=os.open(cache/(kind+"-launcher-private.log"),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    print(kind.upper(),"launch; authentication log private; no world commands",flush=True)
    with os.fdopen(descriptor,"wb") as log:
        result=subprocess.run(["rtk","proxy","flatpak","run","--command=prismrun","org.prismlauncher.PrismLauncher","--launch","Aqualumen Lab","--world",world],cwd=ROOT,env=dict(os.environ,DISPLAY=":1"),stdout=log,stderr=subprocess.STDOUT)
    print(kind.upper(),"LAUNCHER EXIT",result.returncode,flush=True);raise SystemExit(result.returncode)

def collect():
    request=json.loads((OUT/"install.json").read_text())["requestId"]
    path=GAME/"aqualumen-receiver-material-probe"/(request+".json")
    copy(path,"actual-texture-readback.json");copy(GAME/"logs/latest.log","test-texture-runtime.log")
    data=json.loads(path.read_text())
    if "error" in data:raise ValueError("Actual texture capture failed: "+data["error"])
    if data["world_id"]!=WORLD or len(data["observations"])!=3 or any(len(o["actualClientFaces"])!=16 for o in data["observations"]):raise ValueError("Incomplete warmed scope")
    print("Captured3 warmed actual16-face/texel observations; not GPU texture binding or radiance")

def restore():
    closed();base=json.loads((OUT/"fresh-normal-baseline.json").read_text());cache=Path(base["backup"])
    if "All dimensions are saved" not in (GAME/"logs/latest.log").read_text():raise ValueError("Clean TEST save not proven")
    copy(GAME/"logs/latest.log","test-clean-save-exit.log")
    if sha(GAME/"mods"/JAR)!=HASH:raise ValueError("Probe identity changed")
    retained=cache/"disabled-probe";retained.mkdir(exist_ok=False)
    shutil.move(GAME/"mods"/JAR,retained/JAR);shutil.move(GAME/"config"/PROPERTY,retained/PROPERTY)
    for name,digest in base["configSHA256"].items():
        if sha(cache/name)!=digest:raise ValueError("Original backup changed")
        shutil.copy2(cache/name,GAME/name)
    observed=original(cache)
    if observed!=base:raise ValueError("Ordinary saved/config/JAR bytes changed")
    save("normal-restored.json",observed);print("Probe disabled recoverably; normal41 saved/config/JAR files exact; no save restore")

if __name__=="__main__":
    import sys
    action=sys.argv[1]
    if action in ("test","normal"):launch(action)
    else:{"baseline":baseline,"install":install,"collect":collect,"restore":restore}[action]()
