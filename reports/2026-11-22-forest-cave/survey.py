"""Generate the previously located dark forest on a third seed in a private vanilla survey."""
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"2026-11-21-settlement-light/tools"))
from vserver import Server, CLIENT_JAR, CLIENT_JAR_SHA1
from mcnbt import Region


def main():
    sites=here.parent/"2026-11-21-settlement-light/screen-batch1.log"
    found=next(s for s in map(json.loads,sites.read_text().splitlines()) if s["seed"]==20261123)
    x,z,_ = found["rain"]["dark_forest"]
    chunks={(cx,cz) for cx in range(x//16-4,x//16+5) for cz in range(z//16-4,z//16+5)}
    sha=hashlib.sha1(Path(CLIENT_JAR).read_bytes()).hexdigest()
    assert sha==CLIENT_JAR_SHA1 and (x,z)==(1648,1040)
    d=Path(tempfile.mkdtemp(prefix="aql-forest-cave-survey-"))
    server=Server(str(d),found["seed"],cpus="4-7")
    start=time.monotonic()
    try:
        lo,hi=min(chunks),max(chunks)
        server.cmd(f"forceload add {16*lo[0]} {16*lo[1]} {16*hi[0]+15} {16*hi[1]+15}",r"Marked|force loaded")
        while True:
            time.sleep(5)
            server.cmd("save-all flush",r"Saved the game")
            regions={}
            complete=0
            for cx,cz in chunks:
                name=d/"world/region"/f"r.{cx//32}.{cz//32}.mca"
                if not name.is_file():continue
                if name not in regions:regions[name]=Region(name)
                chunk=regions[name].chunk(cx,cz)
                complete+=int(bool(chunk) and chunk.get("Status")=="minecraft:full")
            if complete==len(chunks):break
            if time.monotonic()-start>300:raise TimeoutError("dark forest terrain generation")
    finally:
        status=server.stop()
    assert status==0
    record=dict(seed=found["seed"],biomeCentre=[x,z],vanillaJarSha1=sha,fullChunks=complete,
                world=str(d/"world"),chunkMin=lo,chunkMax=hi,seconds=round(time.monotonic()-start,1))
    (here/"generated.json").write_text(json.dumps(record,indent=2)+"\n")
    print(record)


if __name__=="__main__":
    main()
