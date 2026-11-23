"""Sample the named guarded Java clients while the four placed torches are present."""
from datetime import datetime,timezone
import argparse
import json
from pathlib import Path
from subprocess import check_output
from time import monotonic,sleep
from xml.etree import ElementTree as ET
from pack import HERE

density=HERE.parent/"2026-11-23-torch-density"
options=argparse.ArgumentParser()
options.add_argument("--run",action="append")
options.add_argument("--output",type=Path,default=HERE/"residency.json")
options.add_argument("--wait",type=int,default=360)
args=options.parse_args()
results={}
for name in args.run or ("gp-density-placed-hull-ordinary","gp-density-placed-hull-control"):
    root=density/name
    deadline=monotonic()+args.wait
    while monotonic()<deadline:
        logger=root/"client.log"
        if logger.exists() and "AQLAVA_READY_birch-4_END" in logger.read_text():break
        sleep(.5)
    else: raise TimeoutError(name)
    game=Path((root/"private-game.txt").read_text().strip()).resolve()
    rows=[]
    while len(rows)<12 and monotonic()<deadline and "AQLAVA_STILL_birch-4_END" not in logger.read_text():
        gpu=ET.fromstring(check_output(["nvidia-smi","-q","-x"])).find("gpu")
        for node in gpu.findall("processes/process_info"):
            pid=int(node.findtext("pid"))
            process=Path("/proc")/str(pid)
            try:
                if (process/"comm").read_text().strip()!="java":continue
                if game!= (process/"cwd").resolve() and str(game).encode() not in (process/"cmdline").read_bytes(): continue
            except FileNotFoundError:continue
            rows.append(dict(utc=datetime.now(timezone.utc).isoformat(),pid=pid,
                             javaMiB=int(node.findtext("used_memory").split()[0]),
                             gpuUsedMiB=int(gpu.findtext("fb_memory_usage/used").split()[0]),
                             utilization=int(gpu.findtext("utilization/gpu_util").split()[0])))
        sleep(.5)
    assert len(rows)>=5,name
    results[name]=rows
    args.output.write_text(json.dumps(results,indent=2)+"\n")
