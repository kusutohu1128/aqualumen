"""New surface join replay; reuse sealed geometry, never redo world or GPU capture."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/2026-10-06-water-receiver-surface-v2"
TEXTURE=ROOT/"reports/2026-10-06-water-receiver-texture"
GEOMETRY=ROOT/"reports/2026-10-06-water-receiver-contract-v3"
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,data):
    with (OUT/name).open("x") as stream:stream.write(data)
def copy(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open("xb") as stream:stream.write(source.read_bytes())
def unique_descriptors(faces):
    unique={}
    descriptor=lambda face:{k:v for k,v in face.items() if not k.startswith("savedPoint")}
    for face in faces:
        key=tuple(face["cell"]+face["normal"])
        if key in unique and descriptor(unique[key])!=descriptor(face):raise ValueError("Conflicting actual requested face")
        unique[key]=face
    return unique
def main():
    OUT.mkdir(exist_ok=False)
    for directory in (TEXTURE,GEOMETRY):
        subprocess.run(["rtk","proxy","sha256sum","--quiet","-c",str(directory/"SHA256SUMS")],cwd=ROOT,check=True)
    raw=json.loads((TEXTURE/"actual-texture-readback.json").read_text())
    faces=raw["observations"][0]["actualClientFaces"]
    if len(faces)!=16:raise ValueError("Actual record coverage changed")
    unique=unique_descriptors(faces)
    if len(unique)!=14:raise ValueError("Exact distinct face coverage changed")
    lines=[]
    for face in unique.values():
        axis=next(i for i,n in enumerate(face["normal"]) if n)
        values=[*face["cell"],axis,face["normal"][axis],"minecraft:sand",face["atlas"],face["sprite"],
                *face["spriteBounds"],*face["uvOrigin"],*face["uvS"],*face["uvT"],*face["vertexColor"],*face["tint"],
                str(face["shade"]).lower(),face["skyLight"],face["blockLight"],face["vanillaBrightness"],face["textureRGBA_SHA256"]]
        if len(values)!=29:raise ValueError("Saved material input shape changed")
        lines.append("\t".join(map(str,values)))
    write("actual-faces.tsv","\n".join(lines)+"\n")
    rays=[line for line in (GEOMETRY/"actual-rays.tsv").read_text().splitlines() if line.split("\t")[0].endswith("-refracted")]
    if len(rays)!=16:raise ValueError("Original actual refracted ray scope changed")
    lines=[]
    for ray,face in zip(rays,faces):
        parts=ray.split("\t")
        if list(map(int,parts[7:10]))!=face["cell"] or list(map(int,parts[12:15]))!=face["normal"]:
            raise ValueError("Original first ray and actual requested face order mismatch")
        lines.append(ray+"\t"+"\t".join(map(str,face["savedPointPixel"]+face["savedPointRGBA"])))
    write("original-ray-material-expectations.tsv","\n".join(lines)+"\n")
    java=Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/java/java-runtime-delta/bin")
    sources=[ROOT/"physics-mod/dev/aqualumen/physics"/name for name in ("ReceiverField.java","ReceiverFace.java","ReceiverTexture.java","ReceiverSurface.java")]
    sources.append(ROOT/"physics-mod/test/dev/aqualumen/physics/ReceiverSurfaceSavedReplay.java")
    reference=json.loads((TEXTURE/"independent-stock-reference.json").read_text())
    with tempfile.TemporaryDirectory(prefix="receiver-surface-replay-",dir=ROOT/"build") as classes:
        run=subprocess.run(["rtk","proxy",str(java/"javac"),"-proc:none","-d",classes,*map(str,sources)],cwd=ROOT,capture_output=True)
        write("synchronous-compile.log",run.stdout.decode()+run.stderr.decode())
        if run.returncode:raise ValueError("Fresh synchronous build failed; no old binary replay")
        replay=subprocess.run(["rtk","proxy",str(java/"java"),"-cp",classes,"dev.aqualumen.physics.ReceiverSurfaceSavedReplay",
            str(GEOMETRY/"saved-field.tsv"),str(OUT/"actual-faces.tsv"),str(OUT/"original-ray-material-expectations.tsv"),reference["assetJar"]],cwd=ROOT,capture_output=True)
        write("saved-surface-replay.log",replay.stdout.decode()+replay.stderr.decode())
        if replay.returncode:raise ValueError("Saved first-surface material replay failed")
    checks={"surface":["bash","tools/test-receiver-surface.sh"],"geometry":["bash","tools/test-receiver-field.sh"],
            "texture":["bash","tools/test-receiver-texture.sh"],"face":["bash","tools/test-receiver-face.sh"]}
    exits={}
    for name,command in checks.items():
        run=subprocess.run(["rtk","proxy",*command],cwd=ROOT,capture_output=True)
        write(name+"-green.log",run.stdout.decode()+run.stderr.decode());exits[name]=run.returncode
        if run.returncode:raise ValueError("Affected CPU check failed")
    more=[ROOT/"physics-mod/test/dev/aqualumen/physics"/name for name in ("ReceiverSurfaceTest.java","ReceiverFaceTest.java","ReceiverFieldTest.java")]
    more.extend(ROOT/"tools"/name for name in ("test-receiver-surface.sh","water_receiver_surface_replay.py"))
    for source in sources+more:copy(source,OUT/"source"/source.relative_to(ROOT))
    inputs=[GEOMETRY/"saved-field.tsv",GEOMETRY/"actual-rays.tsv",TEXTURE/"actual-texture-readback.json",TEXTURE/"actual-texture-audit.json",TEXTURE/"independent-stock-reference.json"]
    result=dict(schema="aqualumen-first-surface-CPU-replay-v1",firstRefractedRayMaterialMatches=16,uniqueActualFaceDescriptors=14,
        actualNativeImageDigestMatchedByStockDecoder=True,cameraHiddenRequestedFirstFaces=8,
        catalogFrameTokenEnforced=True,liveGeometryAtlasFrameCoherenceProven=False,liveMinecraftRun=False,GPUValidation=False,
        actualGPUFiltering=False,radianceComputed=False,sourceUploaded=False,productionVisualFixImplemented=False,fullGoalAchieved=False,
        synchronousCompileExitCode=0,replayExitCode=0,publicCPUCheckExitCodes=exits,
        inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},sources={str(p.relative_to(ROOT)):sha(p) for p in sources+more})
    write("audit.json",json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(replay.stdout.decode(),end="")
    print("New first-object material join qualified offline; real GPU/radiance/epoch integration remains")

if __name__=="__main__":main()
