"""Compare the verified lamp-only diagnostic rows and ordinary photographs of the reloaded house."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

here = Path(__file__).resolve().parent
report = here.parent
sys.path.insert(0, str(report))
from receiver_measure import patch_values

def load(p):
    return json.loads(p.read_text())

def image_for(root, sample):
    path = root/sample["file"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sample["sha256"]
    return Image.open(path).convert("RGB")

plan = load(report/"receiver-readback/plan.json")["roles"][0]["samples"]
patches = {s["name"]:s["patch"] for s in plan}
work = here/"settled"
settled = load(work/"complete.json")
assert settled["sourceUnchanged"] and settled["privateOptInRemoved"]
checks = []
for row in settled["samples"]:
    cells = [tuple(map(int,t.split("/"))) for t in row["clientCells"].split(" ",1)[1].strip(",").split(",")]
    sky = [s for s,b in cells]
    saved = load(here/"saved-cells.json")["runs"]["receiver-readback"]["samples"]
    assert sky == [c["sky"] for c in saved]
    with image_for(work,row) as image:
        observed = patch_values(np.array(image,dtype=float),patches["soul"])
    checks.append(dict(state=row["state"],mesh=observed,clientBlock=[b for s,b in cells]))
assert all(v["mesh"]["sky"]==checks[0]["mesh"]["sky"] for v in checks)
assert len(checks)==4 and checks[0]["clientBlock"]!=checks[1]["clientBlock"]
(here/"settled-results.json").write_text(json.dumps(dict(savedSkyMatchesClientAll36Cells=True,roles=checks),indent=2)+"\n")

ordinary = here/"ordinary"
finish = here/"ordinary-finish"
if not (finish/"complete.json").is_file():
    sys.exit(0)
records = [(ordinary,load(ordinary/"partial.json")), (finish,load(finish/"complete.json"))]
assert len({r["sourceWorldDigest"] for _,r in records})==1
shots = {}
values = {}
for folder,record in records:
    assert record["normalModsOnly"] and record["sha256"]==load(report/"normal-smoke.json")["packSHA"]
    for row in record["samples"]:
        state=row["state"]
        if state in shots:
            assert state=="open-warm" and folder==finish
            state="open-warm-reload"
        shots[state]=folder/row["file"]
        with image_for(folder,row) as image:
            values[state] = {}
            for name,rect in patches.items():
                rgb=np.asarray(image.crop(tuple(rect)),dtype=float)
                display=rgb/255
                linear=np.where(display<=0.04045,display/12.92,((display+.055)/1.055)**2.4)
                values[state][name]=dict(rgb8=rgb.mean(axis=(0,1)).tolist(),
                    linearY=float((linear@np.array([.2126,.7152,.0722])).mean()))
def change(a,b,name):
    return values[a][name]["linearY"]-values[b][name]["linearY"]
effects = {patch:{
    "warmOpen":change("open-warm","off-open",patch),"warmClosed":change("closed-warm","off-closed",patch),
    "soulOpen":change("open-soul","off-open",patch),"soulClosed":change("closed-soul","off-closed",patch),
    "bothOpenVsJustSoul":change("open-both","open-soul",patch),
    "bothClosedVsJustSoul":change("closed-both","closed-soul",patch),
    "openRepeat":change("open-repeat","open-warm-reload",patch),
    "reloadControl":change("open-warm-reload","open-warm",patch)} for patch in patches}
(here/"ordinary-results.json").write_text(json.dumps(dict(sha256=record["sha256"],patches=patches,readings=values,effects=effects,
    unit="Per-pixel sRGB EOTF on photographed RGB8, then Rec.709 luminance and patch mean."),indent=2)+"\n")
labels = [("off-open","二灯を消した部屋"),("open-warm","奥のランタンだけを点灯"),
          ("closed-both","二灯を点けて、ダークオークの扉を閉める"),("open-both","同じ二灯で、扉を開ける")]
canvas=Image.new("RGB",(1280,804),"#191d20")
draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",21)
for i,(key,label) in enumerate(labels):
    x=(i%2)*640; y=(i//2)*402
    with Image.open(shots[key]) as im:
        canvas.paste(im.convert("RGB").resize((640,360),Image.Resampling.LANCZOS),(x,y))
    draw.text((x+13,y+363),label,font=font,fill="white")
canvas.save(here/"ordinary-house.jpg",quality=94)
print(json.dumps(effects,indent=2))
