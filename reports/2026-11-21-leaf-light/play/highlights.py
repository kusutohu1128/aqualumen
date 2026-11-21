"""Cut short passages from the ordinary play recording using its F3 timestamps."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

def ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *map(str, args)], check=True)

def draw_cut(movie, t, length, title, folder, number):
    caption = folder / f"label-{number}.txt"
    caption.write_text(title)
    clip = folder / f"clip-{number}.mp4"
    vf = f"scale=1280:-2,drawtext=fontfile={font}:textfile={caption}:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=7:x=18:y=h-th-18"
    ff("-ss", f"{t:.3f}", "-i", movie, "-t", length, "-vf", vf, "-an", "-c:v", "libx264",
       "-threads", 2, "-preset", "fast", "-crf", 19, "-pix_fmt", "yuv420p", clip)
    return clip

font = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
run = Path(sys.argv[1]).resolve()
if len(sys.argv) > 2 and sys.argv[2] == "--whole-journey":
    completed=json.loads((run/"complete.json").read_text())
    assert completed["segments"]==["release-roundtrip","slope-return"] and not completed["uninterrupted"]
    first, second = (run.parent/s for s in completed["segments"])
    third = run.parent/"reopen-and-relight"
    reload=json.loads((third/"complete.json").read_text())
    assert reload["revisit"]["sourceRun"]==run.name and reload["revisit"]["previousSaveUnchanged"]
    poses=json.loads((second/"positions.json").read_text())
    moments=[(p["t"],p["label"]) for p in poses if p["label"] in ("return-oak","water-surface")]
    chosen=[]
    for source in (first, third):
        for shot in json.loads((source/"highlights.json").read_text()):
            if source==third and shot["caption"]=="岸から水面を見渡す": continue
            chosen.append((source,shot["start"],shot["seconds"],shot["caption"]))
    chosen[5:5]=[(second,max(t for t,n in moments if n=="return-oak")+.9,3.5,"途中保存から歩いて同じ木に戻る"),
                  (second,max(t for t,n in moments if n=="water-surface")+.7,1.8,"森の岸から水面を見る")]
    with tempfile.TemporaryDirectory(dir=run) as d:
        tmp=Path(d)
        clips=[draw_cut(s/"journey.mkv",t,l,c,tmp,i) for i,(s,t,l,c) in enumerate(chosen)]
        playlist=tmp/"parts.txt"
        playlist.write_text("".join(f"file '{c.name}'\n" for c in clips))
        ff("-f","concat","-safe",1,"-i",playlist,"-c","copy","-movflags","+faststart",run/"woodland-journey.mp4")
    (run/"highlights.json").write_text(json.dumps([dict(original=s.name,seconds=t,duration=l,caption=c) for s,t,l,c in chosen],indent=2,ensure_ascii=False)+"\n")
    raise SystemExit
summary = json.loads((run / ("complete.json" if (run / "complete.json").exists() else "saved-segment.json")).read_text())
assert summary["cleanExit"] and not summary["logErrors"] and summary["video"]
poses = json.loads((run / "positions.json").read_text())
if "revisit" in summary:
    phases = [("reopened", "保存後、同じ木に戻る"), ("both-off", "魂の松明も回収"), ("restored", "魂の松明を置き直す")]
else:
    phases = [("warm", "木の北に松明"), ("both", "南に魂の松明を追加"), ("soul-only", "北の松明を回収")]
stills = Image.new("RGB", (1440, 320), "#1a211f")
draw = ImageDraw.Draw(stills)
face = ImageFont.truetype(font, 22)
cuts = []
for index, (name, caption) in enumerate(phases):
    images = summary["results"][name]["images"]
    im = Image.open(run / images[len(images) // 2]).convert("RGB").resize((480, 270), Image.Resampling.LANCZOS)
    stills.paste(im, (index * 480, 0))
    draw.text((index * 480 + 12, 279), caption, fill="#f0f0ed", font=face)
    # After this event the first-person camera leaves F3 and remains still for three photos.
    t = summary["results"][name]["obs"]["t"] + .9
    cuts.append((t, 4.0, caption))
stills.save(run / "woodland-lights.jpg", quality=94, subsampling=0)
if "caveObs" in summary["results"]:
    for token, caption, length in [("to-cave-", "斜面を登って洞穴へ", 1.0),
                                   ("home-", "洞穴から斜面を下る", 2.4)]:
        group = [r for r in poses if r["label"].startswith(token)]
        if token == "home-":
            pos = next(r for r in group if r["label"]=="home-2")
            t = pos["t"] - .6
        else:
            t = group[-1]["t"] + .65
        cuts.append((t, length, caption))
if "water-surface" in summary["results"]:
    last = [r for r in poses if r["label"].startswith("water-surface")][-1]
    cuts.append((last["t"] + .7, 1.6, "岸から水面を見渡す"))

with tempfile.TemporaryDirectory(dir=run) as d:
    tmp = Path(d)
    names = []
    for i, (t, length, title) in enumerate(cuts):
        clip=draw_cut(run/"journey.mkv",t,length,title,tmp,i)
        names.append(clip.name)
    listfile = tmp / "cuts.txt"
    listfile.write_text("".join(f"file '{name}'\n" for name in names))
    ff("-f", "concat", "-safe", 1, "-i", listfile, "-c", "copy", "-movflags", "+faststart", run/"woodland-walk.mp4")
(run/"highlights.json").write_text(json.dumps([dict(start=t, seconds=length, caption=caption) for t,length,caption in cuts],
                                              ensure_ascii=False, indent=2)+"\n")
