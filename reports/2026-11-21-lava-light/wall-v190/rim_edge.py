"""Check the floor-lip transition on white concrete using matching real game captures."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from compare import verify_f2_windows


def measure(session):
    receipt = json.loads((session / "complete.json").read_text())
    assert receipt["complete"] and receipt["originalWorldAndConfigUnchanged"]
    verify_f2_windows(receipt, (session / "client.log").read_text(), session)
    path = session / "lava1-open-ingame.png"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt["screenshots"]["lava1-open"]["ingame"]
    frame = Image.open(path).convert("RGB")
    g = json.loads((session / "geometry.json").read_text())
    eye = np.array(g["eye"])
    aim = np.array(g["target"]) - eye
    aim /= np.linalg.norm(aim)
    right = np.cross(aim, [0, 1, 0])
    right /= np.linalg.norm(right)
    up = np.cross(right, aim)
    width, height = frame.size
    x, y = np.meshgrid(np.arange(width), np.arange(height))
    f = 2 * np.tan(np.radians(35)) / height
    ray = aim + ((x + .5 - width / 2) * f)[..., None] * right + ((height / 2 - y - .5) * f)[..., None] * up
    wall = eye + ray * ((g["wallZ"] - eye[2]) / np.maximum(.001, ray[..., 2]))[..., None]
    # One quarter of the source is .25 metres inside the basin lip. The old
    # visibility switches a whole stratum on when that ray just clears the lip.
    source_y = 172 + 55/62
    transition_y = source_y + (173 - source_y) * (366 - 361.75) / .25
    mask = (wall[..., 0] > 205.15) & (wall[..., 0] < 206.12) & (np.abs(wall[..., 1] - transition_y) < .10)
    mask = mask[1:] & mask[:-1]
    red = np.array(frame, dtype="i2")[..., 0]
    diff = np.abs(np.diff(red, axis=0))
    peaks = np.max(np.where(mask,diff,0),axis=0)[np.any(mask,axis=0)]
    assert len(peaks) > 60
    yy, xx = np.where(mask)
    patch = frame.crop((int(xx.min()), int(yy.min()-14), int(xx.max()+1), int(yy.max()+15)))
    return dict(renderer=receipt["gl"]["renderer"], pack=receipt["packSha256"], framebuffer=frame.size,
                worldX=[205.15,206.12], wallY=transition_y, columns=len(peaks), medianRedStep=float(np.median(peaks)),
                p95RedStep=float(np.percentile(peaks,95)), largestRedStep=int(peaks.max())), patch


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("before",type=Path);p.add_argument("after",type=Path);p.add_argument("output",type=Path)
    args=p.parse_args()
    old,a=measure(args.before);new,b=measure(args.after)
    assert old["renderer"] == new["renderer"] and old["framebuffer"] == new["framebuffer"]
    assert a.size==b.size
    args.output.mkdir()
    with (args.output/"lip.json").open("x") as f:
        json.dump({"before":old,"after":new},f,indent=2);f.write("\n")
    font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",21)
    w,h=a.width*3,a.height*3
    sheet=Image.new("RGB",(2*w,h+42),"#161a19")
    draw=ImageDraw.Draw(sheet)
    for i,(im,label) in enumerate([(a,"修正前"),(b,"修正後")]):
        sheet.paste(im.resize((w,h),Image.Resampling.NEAREST),(w*i,0))
        draw.text((w*i+12,h+4),label,font=font,fill="white")
    sheet.save(args.output/"lip.jpg",quality=96)
    print(old["p95RedStep"],new["p95RedStep"])

if __name__=="__main__":
    main()
