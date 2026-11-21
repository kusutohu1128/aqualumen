"""Assemble native screenshots and frame-time observations from completed Lab runs."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent
font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 24)
read = lambda path: json.loads(path.read_text())

def save(name, value):
    (root/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+"\n")

def photo(draw, image, source, col, row, label):
    x, y = col*530, row*343
    draw.text((x+8,y+1), label, font=font, fill="white")
    with Image.open(source) as shot:
        small=shot.convert("RGB").resize((524,295),Image.Resampling.LANCZOS)
        image.paste(small,(x+3,y+40))

def forest():
    panel=Image.new("RGB",(1590,686),"#171c22")
    draw=ImageDraw.Draw(panel)
    timings,colors={},{}
    digest=read(root/"package.json")["sha256"]
    regions={"birch":[815,745,900,815],"distant grass":[1700,1040,1770,1090]}
    scenes=[("ground-noon","午後・消灯"),("ground-evening","午後・松明"),("ground-low-sun","午後・魂の松明"),
            ("air-shadow-backlit","夜・消灯"),("air-sunlit-front","夜・松明"),("air-backlit-open","夜・魂の松明")]
    for folder,rows in [("birch-final",scenes),("perf-final",[(n,n) for n in ["ocean-rain","underwater-shore-view","ground-evening"]])]:
        run=root/folder/"capture"
        assert read(run/"complete.json")["status"]=="complete"
        for i,(n,label) in enumerate(rows):
            j=read(run/(n+".json"))
            assert j["pack_sha256"]==digest and j["shader_active"] and not j["shader_fallback"]
            assert j["framebuffer_resolution"]==[2560,1440] and j["window_focused"] and j["camera_follows_local_player"]
            key=folder+"/"+n
            timings[key]={k:j[k] for k in ("mean_fps","p99_ms","max_ms","frames","sample_seconds_actual","actual_camera_position")}
            if folder=="birch-final":
                shot=run/(n+".png")
                photo(draw,panel,shot,i%3,i//3,label)
                with Image.open(shot) as im:
                    rgb=np.asarray(im.convert("RGB"))
                colors[label]={k:rgb[y:h,x:w].mean(axis=(0,1)).round(2).tolist() for k,(x,y,w,h) in regions.items()}
    panel.save(root/"birch-final.jpg",quality=93)
    save("frame-times.json",dict(packSha256=digest,resolution=[2560,1440],renderer=read(run/"run.json")["gl_renderer"],
                                renderChunks=12,normalMinecraftFrameIntervals=True,scenes=timings))
    save("birch-final.json",dict(mode="display RGB8 from the same fixed rectangular regions",regions=regions,colors=colors))

def reference():
    names=["red","neutral","off"]
    panel=Image.new("RGB",(1590,686),"#171c22");draw=ImageDraw.Draw(panel)
    summary={}
    for i,(folder,title) in enumerate([("light-final","Aqualumen 1.5.0"),("photon-colored","Photon 1.1")]):
        r=read(root/folder/"complete.json")
        assert not r["shaderFallback"] and r["width"]==1280
        for k,name in enumerate(names):
            photo(draw,panel,root/folder/(name+".png"),k,i,title+" / "+["赤壁","深層岩","消灯"][k])
        summary[title]=dict(archiveSha256=r["sha256"],options=r.get("referenceOptions",{}),
                            center={n:r["images"][n]["patches"][1]["meanSRGB8"] for n in names})
    panel.save(root/"photon-comparison.jpg",quality=92);save("photon-comparison.json",summary)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("section",choices=["forest","reference"]);args=parser.parse_args()
    forest() if args.section=="forest" else reference()
