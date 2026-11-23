"""Remove only the two window-specific sampler reads and profile the pane-free room."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile
from statistics import mean
import json
from window_room import HERE, ROOT, PACKS, guarded, Room, analyze, gpu
from profile_data import collect_window, read_rows
from beam_pack import once

LABEL="gp-window-uniform-air"
def build():
    origin=ROOT/"dist/Aqualumen-Window-Cells.zip"
    assert guarded.sha(origin)==PACKS["cells"][1]
    buffer=BytesIO()
    with ZipFile(origin) as src,ZipFile(buffer,"w") as out:
        for meta in src.infolist():
            data=src.read(meta)
            if meta.filename=="shaders/lib/window_disk.glsl":
                s=once(data.decode(),"int record=int(texelFetch(aqualumenLightField,address,0).r);","int record=1+max(0,worldTime);")
                s=once(s,"int shape=int(texelFetch(aqualumenLightField,address+ivec2(0,6144),0).r);","int shape=worldTime&255;")
                data=s.encode()
            out.writestr(meta,data)
    path=ROOT/"build/pane-beam/Aqualumen-Window-Uniform-Air.zip"
    data=buffer.getvalue()
    if path.exists():assert path.read_bytes()==data
    else:
        with path.open("xb") as f:f.write(data)
    return path

def compare(pack):
    groups={"base":("gp-window-control-profile",ROOT/"dist/Aqualumen-Sunlit-Panes.zip"),
            "cells":("gp-window-cells-profile",ROOT/"dist/Aqualumen-Window-Cells.zip"),"uniform":(LABEL,pack)}
    samples={};records={}
    for key,(label,path) in groups.items():
        folder=HERE/label
        s=json.loads((folder/"summary.json").read_text())
        assert s["packSha"]==guarded.sha(path) and "3080 Ti" in s["renderer"]["renderer"]
        timing=gpu.extract(folder,"air",None,pack_path=path,condition="air",min_frames=50)
        log=(folder/"client.log").read_text()
        ids=gpu.window_ids(log,"air",timing["intervalsUs"])
        with (guarded.BUILD/(label+".csv")).open() as f: frames=read_rows(f)
        samples[key]=collect_window(frames,ids)
        records[key]=s["packSha"]
    count=min(map(len,samples.values()))
    metrics={name:{k:mean(row["inclusive"][k] for row in rows[:count])/1e6 for k in ("frame","quad/deferred","stage/shadowcomp")}
             for name,rows in samples.items()}
    result=dict(identicalFrameCount=count,renderer=s["renderer"]["renderer"],sourcePacks=records,milliseconds=metrics)
    (HERE/"uniform-lookup.json").write_text(json.dumps(result,indent=2)+"\n")
    print(result)

if __name__=="__main__":
    p=build()
    assert not (HERE/LABEL).exists()
    fixed=dict(backend="vgl",size="2560x1440",settle="1",stages="air",glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"700","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    try:
        guarded.launch(p,LABEL,"on",fixed,HERE,Room)
    except SystemExit as exc:
        if exc.code:raise
    analyze(HERE/LABEL,p,True,min_frames=50)
    compare(p)
