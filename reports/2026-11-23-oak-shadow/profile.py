"""Use the existing exact-world torch fixture and profiler after the render queue drains."""
import argparse
import fcntl
import os
from pathlib import Path
import re
import sys
import time

from pack import BASE, PACK, WORK

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
import measure_density as density

DIGESTS={"slabs":"de3225d1fd5ae469778293e8be4c974ce6f5f1060cef5fc01bfb73e92de61fe8",
         "study":"33bd554ff80961551dacff3d696e74d64976c4d107af648bacb03fae9313a2a7",
         "stock":"a5f2507b0c6cc6dd05630b4c01f9dbf3fc5a1f52ba58aa7213aed17085ab5bc9"}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("arm",choices=DIGESTS)
    ap.add_argument("label")
    ap.add_argument("--analyze",action="store_true",help="Analyze the existing capture without starting Minecraft")
    a=ap.parse_args()
    assert re.fullmatch("gp-density-oak-[a-z0-9-]+",a.label)
    pack={"stock":BASE,"study":PACK,"slabs":WORK/"Aqualumen-Solid-Slabs.zip"}[a.arm]
    assert density.guarded.sha(pack)==DIGESTS[a.arm]
    directory=HERE/a.label
    if a.analyze:
        density.analyze(directory,pack,True,min_frames=2)
        return
    raw=density.guarded.BUILD/(a.label+".csv")
    assert not directory.exists() and not raw.exists()
    fixed=dict(backend="vgl",size="2560x1440",settle="1",stages="birch-4",glcache=str(density.guarded.BUILD/"driver-cache"))
    fixed.update({"load-timeout":"1500","period-ticks":"800","compiler-mod":str(density.ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    # The stock runner acquires the same lock itself. Allow queued jobs to finish
    # before its separate early check for foreign GPU processes.
    while True:
        with open(f"/tmp/aql-render21-{os.getuid()}.lock","a+b") as gate:
            fcntl.flock(gate,fcntl.LOCK_EX)
            busy=bool(density.guarded.inspect_gpu()["foreign"])
        if busy:
            time.sleep(4)
            continue
        try:
            density.guarded.launch(pack,a.label,"on",fixed,HERE,density.TorchCounts)
        except SystemExit as exc:
            if exc.code and str(exc).startswith("GPU busy") and not directory.exists():
                time.sleep(4)
                continue
            if exc.code: raise
        break
    density.analyze(directory,pack,True,min_frames=2)


if __name__=="__main__":
    main()
