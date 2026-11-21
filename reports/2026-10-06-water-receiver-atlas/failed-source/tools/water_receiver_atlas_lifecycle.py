"""Fresh exclusive0.1.2 actual atlas cycle using the qualified save/restore workflow."""
import json
from pathlib import Path
import uuid
import water_receiver_texture_lifecycle as base

base.OUT=base.ROOT/"reports/2026-10-06-water-receiver-atlas"
base.JAR="aqualumen-receiver-material-probe-0.1.2-atlas-v1.jar"
base.HASH="96ccb1c0c451dd8b37cb16e6c0a9a2ea2e76f7a3b8103ea66b6e271b514f8791"

def install():
    base.closed();baseline=json.loads((base.OUT/"fresh-normal-baseline.json").read_text())
    if base.original(Path(baseline["backup"]))!=baseline:raise ValueError("Fresh ordinary baseline changed")
    marker=dict(line.split("=",1) for line in (base.GAME/"saves/AqualumenNaturalV2/aqualumen-world.properties").read_text().splitlines())
    if marker.get("world_id")!=base.WORLD or marker.get("seed")!="308060" or marker.get("generator")!="minecraft:noise/overworld":raise ValueError("TEST identity mismatch")
    binary=base.ROOT/"build"/base.JAR
    if base.sha(binary)!=base.HASH or (base.GAME/"mods"/base.JAR).exists() or (base.GAME/"config"/base.PROPERTY).exists():raise ValueError("Probe identity/path rejected")
    points=json.loads((base.ROOT/"reports/2026-10-06-water-coast-world/geometry-audit.json").read_text())["points"]
    if len(points)!=16:raise ValueError("Saved16-point scope changed")
    request=str(uuid.uuid4())
    lines=["schema=3",f"world_id={base.WORLD}",f"request_id={request}",f"pack_sha256={base.sha(base.GAME/'shaderpacks/Aqualumen-0.6.0.zip')}"]
    for i,point in enumerate(points):
        hit=point["firstIntersection"]
        if hit["state"]!={"Name":"minecraft:sand"}:raise ValueError("Unsupported saved source subset")
        axis=next(i for i,n in enumerate(hit["normal"]) if n)
        local=[hit["point"][a]-hit["cell"][a] for a in ((axis+1)%3,(axis+2)%3)]
        if not all(0<=v<=1 for v in local):raise ValueError("Local face point invalid")
        lines.extend([f"point.{i}="+",".join(map(str,hit["cell"]+hit["normal"])),f"local.{i}="+",".join(map(repr,local))])
    body="\n".join(lines)+"\n"
    with (base.GAME/"mods"/base.JAR).open("xb") as stream:stream.write(binary.read_bytes())
    with (base.GAME/"config"/base.PROPERTY).open("x") as stream:stream.write(body)
    with (base.OUT/"request.properties").open("x") as stream:stream.write(body)
    base.copy(binary,base.JAR)
    base.save("install.json",dict(requestId=request,worldUUID=base.WORLD,probeSHA256=base.HASH,
            normalPhysicsUnchanged=True,worldWrites=False,shaderSourceChanged=False,GPUReadbackEnabledOnlyInTEST=True))
    print("Installed guarded actual GPU atlas observer, request:",request)

if __name__=="__main__":
    import sys
    action=sys.argv[1]
    if action in ("test","normal"):base.launch(action)
    else:{"baseline":base.baseline,"install":install,"collect":base.collect,"restore":base.restore}[action]()
