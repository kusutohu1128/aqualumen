"""Cut short, unobstructed passages from the continuous ordinary-play recording."""
import argparse
from bisect import bisect_right
from pathlib import Path
import json
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

def ff(*args):
    subprocess.run(["ffmpeg","-v","error","-nostdin","-y",*map(str,args)],check=True)

def make(run):
    summary=json.loads((run/"complete.json").read_text())
    assert summary["cleanExit"] and summary["seconds"]>=1200
    movie=run/"ordinary-walk.mkv"
    poses=json.loads((run/"positions.json").read_text())
    times=[s["seconds"] for s in poses]
    events=[json.loads(line) for line in (run/"hud-events.jsonl").read_text().splitlines()]
    periods=[]
    for pre,post in zip(events,events[1:]):
        if pre["visible"] or not post["visible"]:continue
        a=pre["seconds"]+.85
        b=post["seconds"]-.40
        if b-a<2.9:continue
        idx=max(0,bisect_right(times,a)-1)
        periods.append((a,b,poses[idx]["label"]))
    assert periods
    labels={"tunnel":"坑道へ","bank":"池へ","oak":"木のある道へ","patio":"軒先へ","tree-interaction":"松明のある木へ"}
    requested=((.035,"tunnel"),(.14,"bank"),(.29,"oak"),(.43,"patio"),(.59,"tunnel"),(.79,"bank"),(.95,"patio"))
    chosen=[]
    for fraction,preferred in requested:
        target=summary["seconds"]*fraction
        # The destination label comes directly from the recorded waypoint request.
        usable=[v for v in periods if v[2]==preferred and v not in chosen and abs(.5*(v[0]+v[1])-target)<120]
        if not usable:
            usable=[v for v in periods if v[2] in labels and v not in chosen]
        best=min(usable,key=lambda v:abs(.5*(v[0]+v[1])-target))
        chosen.append(best)
    chosen.sort()
    receipt=[]
    font="/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"
    with tempfile.TemporaryDirectory(dir=run) as temp:
        scratch=Path(temp)
        segments=[]
        for idx,(a,b,label) in enumerate(chosen):
            length=min(4.8,b-a)
            source_t=(a+b-length)*.5
            segment=scratch/f"clip{idx}.mp4"
            title=f"出発から {int(source_t)//60}分{int(source_t)%60:02d}秒　{labels[label]}"
            caption=scratch/f"caption{idx}.txt"
            caption.write_text(title)
            overlay=f"drawtext=fontfile={font}:textfile={caption}:fontsize=17:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=7:x=14:y=13"
            ff("-ss",f"{source_t:.3f}","-i",movie,"-t",f"{length:.3f}","-vf",overlay,"-an","-c:v","libx264",
               "-threads","2","-preset","fast","-crf","18","-pix_fmt","yuv420p",segment)
            segments.append(segment)
            receipt.append({"startSeconds":source_t,"durationSeconds":length,"waypoint":label})
        cuts=scratch/"clips.txt"
        cuts.write_text("".join(f"file '{f.name}'\n" for f in segments))
        ff("-f","concat","-safe","1","-i",cuts,"-c","copy","-movflags","+faststart",run/"walk-highlights.mp4")
    (run/"highlights.json").write_text(json.dumps(receipt,indent=2)+"\n")
    actions=summary["actions"]
    phases=[a["phase"] for a in actions if a["action"]=="mine and replace mounted torch" and a["before"]==a["restored"] and a["before"]!=a["removed"]]
    if phases:
        w,h,bar=500,281,34
        proof=Image.new("RGB",(w*3,(h+bar)*len(phases)),"#192322")
        draw=ImageDraw.Draw(proof)
        face=ImageFont.truetype(font,18)
        for j,phase in enumerate(phases):
            for i,(state,name) in enumerate((("on","最初の松明"),("off","取り外した後"),("restored","付け直した後"))):
                im=Image.open(run/f"{phase}-oak-torch-{state}.jpg")
                y=j*(h+bar); x=i*w
                proof.paste(im.resize((w,h),Image.Resampling.LANCZOS),(x,y+bar))
                draw.text((x+7,y+4),("雨の夕方" if phase=="rain" else "晴れた日中")+"　"+name,fill="#edf1ef",font=face)
        proof.save(run/"oak-torch.jpg",quality=94,subsampling=0)

if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run",type=Path)
    make(ap.parse_args().run)
