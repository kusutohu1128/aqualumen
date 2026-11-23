"""Inspect the actual wall and cow when the same ray calculation changes render passes."""
import json
import sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from visible_pack import HERE,SOURCE_SHA,STUDY_SHA
PENUMBRA=HERE.parent/"2026-11-23-torch-penumbra"
sys.path.insert(0,str(PENUMBRA))
from room_results import capture, hand_intervals, runs
from motion_results import RGB_Y, COW_WALL, COW_CONTROL, region, wall_samples, crossing
from moving import A,B


def main():
    folders=(PENUMBRA/"penumbra-normal-joint", HERE/"frontmost-room")
    images=[capture(f,k) for f,k in zip(folders,(SOURCE_SHA,STUDY_SHA))]
    assert (folders[0]/"geometry.json").read_bytes()==(folders[1]/"geometry.json").read_bytes()
    edges=json.loads((PENUMBRA.parent/"2026-11-23-torch-umbra/wall-edge.json").read_text())
    report={"hands":{},"cow":{}}
    canvas=Image.new("RGB",(960,510),"#19221f")
    font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",16)
    draw=ImageDraw.Draw(canvas)
    for side_i,(side,pose) in enumerate((("left",A),("right",B))):
        stages=(f"hand-{side}-clear",f"hand-{side}-oak")
        pts=wall_samples(pose)
        pairs=[]
        for imgs in images:
            clear,oak=[imgs[s]@RGB_Y for s in stages]
            loss=clear-oak
            steps=[]
            for g in runs(edges[side]):
                xy=np.array([row["pixel"] for row in g])
                y=loss[xy[:,1],xy[:,0]]
                steps.append(float(abs(np.diff(y)).max()))
            pairs.append({"maxSteps":steps,"litWallLossMedian":float(np.median(loss[pts["lit"]])),
                          "shadowWallLossMedian":float(np.median(loss[pts["shadow"]]))})
        all_pts=tuple(np.concatenate([pts[k][i] for k in ("lit","shadow")]) for i in (0,1))
        diff=abs(images[0][stages[1]].astype(int)-images[1][stages[1]].astype(int)).max(axis=2)[all_pts]
        report["hands"][side]={"forward":pairs[0],"deferred":pairs[1],"registeredPixels":len(diff),
                                "p99RGB":float(np.quantile(diff,.99)),"maxRGB":int(diff.max())}
        g=min(runs(edges[side]),key=lambda rows:min(abs(p["worldX"]-pose) for p in rows))
        cx,cy=np.round(np.mean([row["pixel"] for row in g],axis=0)).astype(int)
        for i,imgs in enumerate(images):
            left=int(np.clip(cx-120,0,1040));top=int(np.clip(cy-52,0,616))
            rect=(left,top,left+240,top+104)
            crop=Image.fromarray(imgs[stages[1]]).crop(rect).resize((480,208),Image.Resampling.NEAREST)
            canvas.paste(crop,(i*480,side_i*255))
            draw.text((i*480+10,side_i*255+215),("前方描画" if i==0 else "最前面で計算")+("　柱の左側" if side=="left" else "　柱の右側"),font=font,fill="white")
    for folder,img,label in zip(folders,images,("forward","deferred")):
        report["cow"][label]={stage:{"wall":region(img[stage],COW_WALL).round(2).tolist(),
                                      "control":region(img[stage],COW_CONTROL).round(2).tolist()}
                              for stage in ("both-empty","both-west","both-east","both-restored")}
        report["cow"][label]["travel"]=json.loads((folder/"trajectory.json").read_text())["displacementM"]
        report["cow"][label]["chroma"]=crossing(folder)
    report["shortWindows"]={label:hand_intervals(f) for label,f in zip(("forward","deferred"),folders)}
    (HERE/"room-quality.json").write_text(json.dumps(report,indent=2)+"\n")
    canvas.save(HERE/"room-edges.png")
    print(report["hands"])


if __name__=="__main__":
    main()
