"""Compare registered F2 pixels on the wall; no lighting-model output is substituted for RGB."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pack import HERE, CHECKSUM
PREV=HERE.parent/"2026-11-23-torch-umbra"
sys.path.insert(0,str(PREV))
from motion_results import RGB_Y, STAGES, crossing, wall_samples
from moving import A, B
from summarize import window_ids


def read(folder, name):
    return json.loads((folder/name).read_text())


def capture(folder, expected):
    r=read(folder,"complete.json")
    assert r["complete"] and not r["failure"] and r["originalWorldAndConfigUnchanged"]
    assert r["sourcePackShaNow"]==r["packSha256"]==expected and r["stages"]==STAGES
    assert "RTX 3080 Ti" in r["gl"]["renderer"] and r["size"]==[1280,720]
    pre=read(folder,"preflight.json")
    assert pre["labBefore"]==pre["labAfter"] and not pre["foreignObservations"]
    assert list(map(int,re.findall(r'\[Server\] AQ_HAND_STEP_(\d+)',(folder/"client.log").read_text())))==list(range(1,25))
    images={}
    for name in STAGES:
        file=folder/(name+"-ingame.png")
        assert hashlib.sha256(file.read_bytes()).hexdigest()==r["screenshots"][name]["ingame"]
        with Image.open(file) as frame:
            images[name]=np.asarray(frame.convert("RGB"))
    return images


def runs(row):
    groups=[[]]
    for point in row["samples"]:
        if groups[-1] and point["worldX"]-groups[-1][-1]["worldX"]>.011:
            groups.append([])
        groups[-1].append(point)
    return [g for g in groups if len(g)>5]


def hand_intervals(folder):
    """Two complete CPU observer batches after a three-batch post-F2 settling period."""
    log=(folder/"client.log").read_text()
    observer=read(folder,"observer.json")
    assert "gpuProfilerSha256" not in observer
    stats={}
    for stage in ("hand-left-clear","hand-left-oak","hand-right-oak","hand-right-clear"):
        ready="[Server] AQLAVA_READY_"+stage+"_END"
        assert log.count(ready)==1
        window=log.split(ready)[1].split("[Server] AQLAVA_STILL_"+stage+"_END")[0]
        after_photo=window.split(".pngとして保存しました")[1]
        batches=re.findall(r"AQ_RENDER_INTERVALS_US \d+ ([\d ]+)",after_photo)[3:5]
        assert len(batches)==2, (stage,"short observer window")
        values=[int(us) for batch in batches for us in batch.split()]
        ids=window_ids(log,stage,values)
        stats[stage]={"frames":len(ids),"firstFrame":ids[0],"lastFrame":ids[-1],
                      "seconds":sum(values)/1e6,"meanIntervalMs":float(np.mean(values))/1000}
    return stats


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("label")
    ap.add_argument("checksum")
    args=ap.parse_args()
    folders=[PREV/"moving-umbra-r2",HERE/args.label]
    assert read(folders[0],"geometry.json")==read(folders[1],"geometry.json")
    groups=read(PREV,"wall-edge.json")
    sources=[capture(f,p) for f,p in zip(folders,(CHECKSUM,args.checksum))]
    report={"reference":CHECKSUM,"candidate":args.checksum,"stages":STAGES,"edges":{},"cow":[]}
    canvas=Image.new("RGB",(1040,542),"#18221f")
    draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",17)
    for side_idx,(side,pose) in enumerate([("left",A),("right",B)]):
        side_rows=[]
        regions=wall_samples(pose)
        for group in runs(groups[side]):
            pixels=np.array([q["pixel"] for q in group])
            disk=np.array([q["disk"] for q in group])
            record={"worldX":[q["worldX"] for q in group],"pixels":pixels.tolist(),"disk":disk.tolist()}
            for label,images in zip(["preview12","study"],sources):
                oak=images[f"hand-{side}-oak"]@RGB_Y
                clear=images[f"hand-{side}-clear"]@RGB_Y
                difference=clear-oak
                y=difference[pixels[:,1],pixels[:,0]]
                record[label]={"shadowLoss":np.round(y,3).tolist(),"largestAdjacentStep":float(np.max(abs(np.diff(y)))),
                               "shadowMedian":float(np.median(difference[regions["shadow"]])),
                               "litMedian":float(np.median(difference[regions["lit"]]))}
            side_rows.append(record)
        report["edges"][side]=side_rows
        group=min(runs(groups[side]),key=lambda g:min(abs(p["worldX"]-pose) for p in g))
        xy=np.array([r["pixel"] for r in group])
        cx,cy=np.round(xy.mean(axis=0)).astype(int)
        for j,images in enumerate(sources):
            left=int(np.clip(cx-120,0,1040)); top=int(np.clip(cy-52,0,616))
            crop=Image.fromarray(images[f"hand-{side}-oak"]).crop((left,top,left+240,top+104))
            x,y=j*520,side_idx*271
            canvas.paste(crop.resize((520,225),Image.Resampling.NEAREST),(x,y))
            draw.text((x+10,y+233),("プレビュー12" if j==0 else "試作")+"　柱の"+("左側" if side_idx==0 else "右側")+"から",font=font,fill="white")
    for folder in folders:
        path=read(folder,"trajectory.json")
        report["cow"].append({"travel":path["displacementM"],**crossing(folder)})
    prefix="joint-" if "joint" in args.label else ""
    if prefix:
        report["shortHandFrameIntervals"]={name:hand_intervals(folder) for name,folder in zip(("preview12","study"),folders)}
    (HERE/(prefix+"room.json")).write_text(json.dumps(report,indent=2)+"\n")
    canvas.save(HERE/(prefix+"wall-comparison.png"))
    print({k:[(round(g["preview12"]["largestAdjacentStep"],2),round(g["study"]["largestAdjacentStep"],2)) for g in v] for k,v in report["edges"].items()})


if __name__=="__main__":
    main()
