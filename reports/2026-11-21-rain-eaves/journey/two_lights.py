"""Build the regular-play two-light comparison, keeping the common original exposure in every frame."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from torch_pixels import regions,measure

def build(path):
    rec=json.loads((path/"complete.json").read_text())
    assert rec["cleanExit"] and rec["treeMatrix"] and not rec["benchmarkMod"] and rec["torchCellAtEnd"]=="minecraft:wall_torch[facing=west]"
    states=json.loads((path/"light-states.json").read_text())
    by_name={s["state"]:s for s in states}
    assert len(by_name)==7 and len({tuple(s["angle"]) for s in states})==1 and len({tuple(s["xyz"]) for s in states})==1
    selected=[("both-off","両方消灯"),("warm-only","幹の松明だけ"),("soul-only","手の魂のランタンだけ"),("both","両方点灯")]
    w,h,bar=620,349,35
    i=Image.new("RGB",(w*2,(bar+h)*2),"#172126")
    draw=ImageDraw.Draw(i)
    font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",19)
    for k,(name,label) in enumerate(selected):
        x=k%2*w;y=k//2*(h+bar)
        draw.text((x+8,y+4),label,font=font,fill="#ebeeeb")
        im=Image.open(path/(name+".jpg"))
        i.paste(im.resize((w,h),Image.Resampling.LANCZOS),(x,y+bar))
    i.save(path/"two-lights.jpg",quality=94,subsampling=0)
    result={r:{s:measure(path/(s+".jpg"),rect) for s in by_name} for r,rect in regions.items()}
    bark=result["oakBarkBesideFlame"]
    def rgb(k):return np.array(bark[k]["medianRGB8"],dtype=np.float64)
    contributedRed=(rgb("both")-rgb("soul-only"))[0]
    contributedBlue=(rgb("both")-rgb("warm-only"))[2]
    checks={"mount_warms_bark":rgb("warm-only")[0]>rgb("both-off")[0]+10,
            "held_soul_lights_bark_blue":rgb("soul-only")[2]>rgb("both-off")[2]+10,
            "mount_keeps_red_when_both_on":bool(contributedRed>8),
            "soul_keeps_blue_when_both_on":bool(contributedBlue>8)}
    doc={"method":"Saved ordinary-play sRGB8 frames. No per-frame colour normalization. Checks compare median display channels of the same bark beside the flame. Background, ground and repeat actions are included.","checks":{k:bool(v) for k,v in checks.items()},"states":by_name,"regions":result}
    (path/"two-lights.json").write_text(json.dumps(doc,indent=2)+"\n")
    print(checks)
    return all(checks.values())

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("run",type=Path)
    raise SystemExit(not build(parser.parse_args().run))
