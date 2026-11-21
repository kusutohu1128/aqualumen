"""Rebuild the opt-in forest fixtures from the archived benchmark source."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

here=Path(__file__).resolve().parent
root=here.parents[2]
base=root/"reports/2026-11-20-local-light/forest-tools/jar-src"
prism=Path(os.environ.get("AQUALUMEN_PRISM_ROOT",Path.home()/".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher"))
java=prism/"java/java-runtime-delta/bin"
loader=prism/"libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
mixin=prism/"libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=["floor","floor-read","two-lamps"])
    args=p.parse_args()
    lamps=args.mode=="two-lamps"
    target=root/"build/ground-return"/("lamps" if lamps else "fixture")
    target.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target) as temp:
        work=Path(temp)
        src=work/"src"
        classes=work/"classes"
        shutil.copytree(base,src)
        classes.mkdir()
        bench=src/"dev/aqualumen/bench"
        patches=["two-lamps"] if lamps else ["floor"]
        if args.mode=="floor-read":
            patches.append("read-field")
        for patch in patches:
            subprocess.run(["patch","-p0","--fuzz=0","-i",str(here/(patch+".patch"))],cwd=bench,check=True)
        if args.mode!="floor":
            shutil.copy2(here/"GroundFieldSnapshot.java",bench)
        subprocess.run([java/"javac","-proc:none","-cp",os.pathsep.join(map(str,(loader,mixin))),
                        "-d",classes,*sorted(bench.glob("*.java"))],check=True)
        for resource in src.glob("*.json"):
            shutil.copy2(resource,classes)
        stem="lamps" if lamps else args.mode
        archive=work/("aqualumen-benchmark-"+stem+".jar")
        subprocess.run([java/"jar","--create","--file",archive,"-C",classes,"."],check=True)
        output=target/archive.name
        os.replace(archive,output)
        print(output)
