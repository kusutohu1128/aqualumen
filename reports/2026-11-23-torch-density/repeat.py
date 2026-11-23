"""Reverse the private GPU comparison, then measure practical frame intervals."""
from pathlib import Path
import json
import subprocess
import sys
from compare_stages import HERE, EXPECTED, compare, PAIRS
from pack import PACK

def launch(label,candidate,scenes,cpu=False):
    args=[sys.executable,HERE/"measure_density.py",label,"--stages",",".join(scenes)]
    if candidate: args+=["--pack",PACK,"--sha",EXPECTED[1]]
    if cpu: args+=["--cpu-only"]
    subprocess.run(args,check=True)

if __name__=="__main__":
    reverse=["sand-4","birch-4","birch-1","birch-0"]
    launch("gp-density-tiles-b",True,reverse)
    launch("gp-density-p8-b",False,reverse)
    subprocess.run([sys.executable,HERE/"compare_stages.py"],check=True)
    result=compare(PAIRS)
    for scene in ("birch-1","birch-4"):
        if any(pair["stages"]["frame"]["delta"]>=0 for pair in result[scene]):
            raise SystemExit("Whole-frame gain did not repeat; leave the candidate staged.")
    # Collect intervals without the timestamp profiler in both run orders.
    for side,sort,packs in (("a",["birch-1","birch-4"],(False,True)),("b",["birch-4","birch-1"],(True,False))):
        for candidate in packs:
            name="tiles" if candidate else "p8"
            launch(f"gp-density-frames-{name}-{side}",candidate,sort,True)
