"""Show the actual three corresponding patches for the largest measured deviation."""
import json
import sys
import cv2
from PIL import Image,ImageDraw,ImageFont
from room import HERE
from motion import WOOD


def main(run):
    data=json.loads((HERE/(run+"-motion.json")).read_text())["largest"]
    cap=cv2.VideoCapture(str(WOOD/run/"under-stone.mkv"))
    target=set(data["frameIDs"])
    frames={}
    for ordinal in range(max(target)+1):
        ok,bgr=cap.read()
        assert ok
        if ordinal in target:
            frames[ordinal]=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB))
    cap.release()
    canvas=Image.new("RGB",(1080,434),"#142020")
    draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",16)
    for i,(frame,pt,val) in enumerate(zip(data["frameIDs"],data["pointsHalfSize"],data["stepsLuma"])):
        im=frames[frame]
        x,y=(round(2*c) for c in pt)
        full=im.resize((360,203),Image.Resampling.LANCZOS)
        d=ImageDraw.Draw(full)
        d.rectangle(((x-60)*360/1600,(y-30)*203/900,(x+60)*360/1600,(y+30)*203/900),outline="#ff6090",width=2)
        canvas.paste(full,(360*i,0))
        crop=im.crop((x-60,y-30,x+60,y+30)).resize((360,180),Image.Resampling.NEAREST)
        canvas.paste(crop,(360*i,205))
        draw.text((360*i+6,391),f"収録コマ {frame}　追跡点の明るさ {val:.1f}",fill="white",font=font)
    canvas.save(HERE/(run+"-tracked.jpg"),quality=94)


if __name__=="__main__":
    main(sys.argv[1])
