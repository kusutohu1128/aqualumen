"""Extract ten seconds of consecutive real Minecraft render-return intervals per scene."""
from pathlib import Path
from hashlib import sha256
import json
import math
import re

here=Path(__file__).resolve().parent
packet=here.parent
root=packet.parents[1]
labels={"both-west":"night, one cow, two lanterns","day-white":"noon, one cow, open roof","day-herd":"noon, nine cows, open roof"}
def extract(folder,stage,version,*,pack_path=None,condition=None):
    run=packet/folder
    r=json.loads((run/"complete.json").read_text())
    assert r["originalWorldAndConfigUnchanged"] and stage in r["screenshots"] and "RTX 3080 Ti" in r["gl"]["renderer"]
    assert r["shaderpackLogged"] and r["size"]==[2560,1440]
    pack = Path(pack_path) if pack_path is not None else root/"dist"/f"Aqualumen-1.9.0-preview.{version}.zip"
    assert r["packSha256"]==sha256(pack.read_bytes()).hexdigest()
    assert r["screenshots"][stage]["ingame"]==sha256((run/f"{stage}-ingame.png").read_bytes()).hexdigest()
    # In the first P6 run only the two single-cow stages passed, before the next scene drifted.
    assert r["complete"] or (folder=="timings-p6" and stage in ("both-west","day-white") and "client exited early" in r["failure"])
    log=(run/"client.log").read_text()
    assert "AQ_RENDER_PROBE_FAILED" not in log and "Changing view distance to 12" in log
    start=log.index("[Server] AQLAVA_READY_"+stage+"_END")
    stop=log.index("[Server] AQLAVA_STILL_"+stage+"_END",start)
    window=log[start:stop]
    assert "AQLAVA_BEGIN_" not in window and "AQLAVA_DRIFT_" not in window and "AQLAVA_FAIL_" not in window
    image_line=window.index(".pngとして保存しました")
    batches=re.findall(r"AQ_RENDER_INTERVALS_US (\d+) ([\d ]+)",window[image_line:])
    # Batches report at one-second intervals; discard the first three complete
    # messages after the screenshot, including the batch that straddled its I/O.
    timestamps=[];delta=[]
    for end,values in batches[3:]:
        timestamps.append(int(end))
        delta.extend(map(int,values.split()))
    assert all(920<=b-a<=1600 for a,b in zip(timestamps,timestamps[1:]))
    used=[];total=0
    for x in delta:
        used.append(x);total+=x
        if total>=10_000_000:break
    assert 10_000_000<=total<10_200_000 and min(used)>0 and len(used)>100
    sorted_ms=[t*.001 for t in sorted(used)]
    return dict(run=folder,scene=stage,condition=condition or labels[stage],captureHash=r["screenshots"][stage]["ingame"],frames=len(used),
                seconds=round(total/1e6,5),meanFps=round(len(used)*1e6/total,2),p99Ms=sorted_ms[math.ceil(.99*len(used))-1],
                intervalsUs=used)

if __name__=="__main__":
    results={}
    for version in (5,6):
        results[str(version)]={}
        for stage in labels:
            folder=f"timings-p{version}" if version==5 or stage!="day-herd" else "herd-p6"
            results[str(version)][stage]=extract(folder,stage,version)
    data=dict(renderer="NVIDIA GeForce RTX 3080 Ti",size=[2560,1440],renderChunks=12,transport="VirtualGL EGL on private Xvfb, vsync off, 120 fps cap",p99="nearest-rank; consecutive intervals between returns from MinecraftClient.render",results=results)
    (packet/"frame-times.json").write_text(json.dumps(data,indent=2)+"\n")
    for version,rows in results.items():
        for k,r in rows.items():
            print(version,k,r["frames"],r["meanFps"],round(r["p99Ms"],2))
