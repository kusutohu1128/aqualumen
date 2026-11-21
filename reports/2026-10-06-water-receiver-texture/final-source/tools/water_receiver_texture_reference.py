"""Compile unique synchronous independent ImageIO oracle and retain sparse reference."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/2026-10-06-water-receiver-texture"
PRISM=Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher")
JAVA=PRISM/"java/java-runtime-delta/bin"

def main():
    raw=json.loads((OUT/"actual-texture-readback.json").read_text())
    coords=set()
    for observation in raw["observations"]:
        for face in observation["actualClientFaces"]:
            coords.add(tuple(face["savedPointPixel"]))
            coords.update(tuple(sample["pixel"]) for sample in face["grid"])
    classes=Path(tempfile.mkdtemp(prefix="receiver-texture-imageio-",dir=ROOT/"build"))
    build=subprocess.run(["rtk","proxy",str(JAVA/"javac"),"-d",str(classes),str(ROOT/"tools/ReceiverTextureAssetReference.java")],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    with (OUT/"imageio-compiler.log").open("xb") as stream:stream.write(build.stdout)
    if build.returncode:raise ValueError("Independent image decoder compile failed")
    jar=PRISM/"libraries/com/mojang/minecraft/1.21.1/minecraft-1.21.1-client.jar"
    command=["rtk","proxy",str(JAVA/"java"),"-Djava.awt.headless=true","-cp",str(classes),"ReceiverTextureAssetReference",str(jar),*(f"{x}:{y}" for x,y in sorted(coords))]
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    with (OUT/"imageio-reference-stderr.log").open("xb") as stream:stream.write(result.stderr)
    if result.returncode:raise ValueError("Independent stock PNG decoding failed")
    reference=json.loads(result.stdout)
    reference["sourceSHA256"]=hashlib.sha256((ROOT/"tools/ReceiverTextureAssetReference.java").read_bytes()).hexdigest()
    reference["compiledClassSHA256"]=hashlib.sha256((classes/"ReceiverTextureAssetReference.class").read_bytes()).hexdigest()
    reference["uniqueSynchronousCompileExitCode"]=build.returncode
    reference["decoderExitCode"]=result.returncode
    reference["assetJar"]=str(jar)
    with (OUT/"independent-stock-reference.json").open("x") as stream:json.dump(reference,stream,indent=2,sort_keys=True)
    print(f"Independent stock PNG16x16 RGBA hash {reference['rgbaSHA256']}; {len(coords)} sparse pixels; no asset copied")

if __name__=="__main__":main()
