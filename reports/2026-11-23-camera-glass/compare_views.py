"""Crop the same area of four original Minecraft F2 screenshots without colour edits."""
from pathlib import Path
import json
import subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
fontfile=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK JP"],text=True)
font=ImageFont.truetype(fontfile,22)
stages=(("one","赤い板を1枚"),("mix","赤と青を1枚ずつ"))
versions=(("base-room","変更前"),("pass-room","厚みから吸収を計算"))
out=Image.new("RGB",(1080,790),(245,246,245))
d=ImageDraw.Draw(out)
metrics={}
for row,(stage,title) in enumerate(stages):
    for col,(folder,version) in enumerate(versions):
        p=HERE/folder/(stage+"-ingame.png")
        with Image.open(p) as image:
            assert image.size==(1280,720)
            crop=image.convert("RGB").crop((378,226,898,566))
            rgb=np.asarray(image.convert("RGB"))
            metrics.setdefault(stage,{})[folder]={
                "lampDisplayMedian":np.median(rgb[343:375,642:660],axis=(0,1)).tolist(),
                "wallDisplayMedian":np.median(rgb[321:333,551:562],axis=(0,1)).tolist()}
        x=10+540*col;y=8+392*row
        d.text((x,y),title+"　"+version,font=font,fill=(22,28,29))
        out.paste(crop,(x,y+37))
out.save(HERE/"windows.png")
(HERE/"display.json").write_text(json.dumps(metrics,indent=2)+"\n")
