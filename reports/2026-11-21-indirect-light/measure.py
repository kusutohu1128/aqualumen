"""Measure the same white-wall patches in ordinary and isolated indirect output."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import fixture as scene

here = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("ordinary", type=Path)
parser.add_argument("diagnostic", type=Path)
parser.add_argument("out", type=Path)
args = parser.parse_args()
args.out.mkdir(exist_ok=False)
records = {}
for mode, source in (("ordinary", args.ordinary), ("indirect", args.diagnostic)):
    complete = json.loads((source / "complete.json").read_text())
    assert "NVIDIA" in str(complete) and not complete.get("shaderFallback", False)
    measurements = {}
    for name in scene.ROLE_NAMES:
        path = source / (name + ".png")
        if not path.exists() or name.startswith("wide-"):
            continue
        rgb = np.asarray(Image.open(path).convert("RGB"), dtype=float)
        assert rgb.shape == (scene.HEIGHT, scene.WIDTH, 3)
        values = []
        for patch in scene.samples(scene.role(name)):
            x0, y0, x1, y1 = patch["patch"]
            raw = rgb[y0:y1, x0:x1]
            # Apply the inverse observation transfer before averaging.
            linear = ((raw / 255) ** 2 / 4).mean(axis=(0, 1))
            values.append(dict(world=patch["world"], rect=patch["patch"],
                               rgb8=raw.mean(axis=(0, 1)).round(3).tolist(),
                               **({"indirectLinear": linear.round(8).tolist()} if mode == "indirect" else {})))
        measurements[name] = values
    records[mode] = dict(pack=complete.get("pack"), sha256=complete.get("sha256"), patches=measurements)

def rgb(mode, state, field):
    return np.array([p[field] for p in records[mode]["patches"][state]])
def patch_rgb(name):
    return rgb("indirect", name, "indirectLinear")

on, grey, black, off, first, second = [patch_rgb(s) for s in ("red","neutral","black","off","first-block","second-block")]
ratio = lambda x: (x.sum(axis=1) / np.maximum(on.sum(axis=1),1e-12))
checks = dict(
    redSignal=(on[:,0]>0.0004).all(),
    neutralLowerRed=(grey[:,0] < 0.8*on[:,0]).all(),
    neutralHigherGreen=(grey[:,1] > on[:,1]).all(),
    blackResidual=ratio(black).round(5).tolist(),
    sourceOff=off.max()==0,
    firstLegResidual=ratio(first).round(5).tolist(),
    secondLegResidual=ratio(second).round(5).tolist(),
    movedDifference=(patch_rgb("moved")-on).round(7).tolist(),
    repeatDifference=(patch_rgb("red-repeat")-on).round(7).tolist(),
    normalRedVsNeutral=(rgb("ordinary","red","rgb8")-rgb("ordinary","neutral","rgb8")).round(2).tolist(),
)
records["checks"]={k:(bool(v) if isinstance(v,np.bool_) else v) for k,v in checks.items()}
(args.out/"wall.json").write_text(json.dumps(records,ensure_ascii=False,indent=2)+"\n")

font = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
heading,small=ImageFont.truetype(font,30),ImageFont.truetype(font,20)
states=[("red","赤いコンクリート"),("neutral","磨かれた深層岩"),("off","ランタンを撤去"),("first-block","ランタンと赤壁の間を塞ぐ"),("second-block","赤壁と白壁の間を塞ぐ"),("soul","魂のランタン")]
def fit(folder, name, size):
    with Image.open(folder/(name+".png")) as im: return im.convert("RGB").resize(size,Image.Resampling.LANCZOS)
def plate():
    w,h=1220,1018
    im=Image.new("RGB",(w,h),"#171c22");d=ImageDraw.Draw(im)
    d.text((18,10),"角を回って届くランタンの光",font=heading,fill="white")
    for i,(name,caption) in enumerate([("wide-red","赤い壁と白い壁の配置"),("wide-neutral","反射面を深層岩に交換")]):
        im.paste(fit(args.ordinary,name,(592,333)),(12+i*604,92))
        d.text((14+i*604,55),caption,font=small,fill="white")
    d.text((15,435),"同じ白壁の通常表示（上）と、一回反射の成分を強調した診断表示（下）",font=small,fill="white")
    for i,(name,caption) in enumerate(states):
        x=12+(i%3)*402;y=477+(i//3)*264
        d.text((x,y),caption,font=small,fill="#e6e8ec")
        for j,folder in enumerate((args.ordinary,args.diagnostic)):
            with Image.open(folder/(name+".png")) as src:
                region=src.crop((0,190,1280,535)).resize((390,105),Image.Resampling.LANCZOS)
                im.paste(region,(x,y+34+j*109))
    im.save(args.out/"comparison.jpg",quality=92)
plate()
print(json.dumps(records["checks"],ensure_ascii=False,indent=2))
assert checks["redSignal"] and checks["neutralLowerRed"] and checks["neutralHigherGreen"] and checks["sourceOff"]
# Real black concrete has nonzero reflectance; the two physical shutters need
# to suppress at least 90% at every receiver, not yield an ideal mathematical zero.
assert max(checks["blackResidual"]+checks["firstLegResidual"]+checks["secondLegResidual"]) < 0.10
assert np.all(np.abs(patch_rgb("moved")-on) < 0.001) and np.all(np.abs(patch_rgb("red-repeat")-on) < 0.001)
displayDelta=np.array(checks["normalRedVsNeutral"])
assert (displayDelta[:,0]>5).all() and (displayDelta[:,1]<-3).all()
