"""Decode the fixed GPU patches and compare the normal displayed ceiling in the same room."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

here=Path(__file__).resolve().parent
stages=["white","red","grey","entry","middle","exit","off","reopened"]
labels={"white":"白い壁 2 枚","red":"1 枚目を赤に","grey":"2 枚目を灰色に","entry":"灯りの出口を塞ぐ","middle":"壁と壁の間を塞ぐ","exit":"天井の手前を塞ぐ","off":"ランタンを外す","reopened":"ふたたび白い壁 2 枚"}
order=["directExit","first","second"]
def role(run,stage):
    result=json.loads((here/run/"complete.json").read_text())
    assert result["complete"] and result["originalWorldAndConfigUnchanged"] and "RTX 3080 Ti" in result["gl"]["renderer"]
    data={}
    for tag in ("ingame","x11-a","x11-b"):
        path=here/run/f"{stage}-{tag}.png"
        assert hashlib.sha256(path.read_bytes()).hexdigest()==result["screenshots"][stage][tag]
        img=np.asarray(Image.open(path).convert("RGB"))
        h,w,_=img.shape
        if run in ("ordinary","baseline"):
            data[tag]=img[h//2-10:h//2+11,w//2-10:w//2+11].mean((0,1)).round(3).tolist()
        else:
            data[tag]={}
            for oi,key in enumerate(order):
                y=round(h*(.95-oi*.10))
                values=[]
                for col in range(3):
                    x=round(w*((col+.5)/3))
                    block=img[y-4:y+5,x-4:x+5]
                    assert np.all(block==block[4,4])
                    values.append(block[4,4].tolist())
                data[tag][key]=values
            if run=="side-meter":
                for key,fraction in (("wallBIncident",.65),("ceilingSupport",.55)):
                    data[tag][key]=[img[round(h*fraction),round(w*(col+.5)/3)].tolist() for col in range(3)]
    return data

def main():
    result={stage:{"normal":role("ordinary",stage),"orders":role("meter",stage)} for stage in stages}
    out={"normalROI":"21x21 at the screen centre; mean display RGB; exit shutter lies in front of the original ceiling",
         "encoding":"Each hardware RGB byte q encodes linear radiance as (q/255)^2/64. Zero is below the readout precision.",
         "ceilingSamples":"local X,Y,Z = (6.25,4,3.25), (6.75,4,3.75), (7.25,4,4.25); all samples retain the original plane even when covered.",
         "stages":result}
    out["priorPreview"]={name:role("baseline",name) for name in ("white","red","grey","off")}
    out["sideScreen"]={name:role("side-meter",name) for name in ("white","screen")}
    out["sideScreenEncoding"]="Wall B is encoded as sqrt(16*linear). Ceiling support contains first and second coverage in R and G, unscaled."
    for capture in ("ingame", "x11-a", "x11-b"):
        prior = out["priorPreview"]
        assert prior["white"][capture] == prior["red"][capture] == prior["grey"][capture]
        assert prior["off"][capture] == result["off"]["normal"][capture]
        meters = {name: item["orders"][capture] for name, item in result.items()}
        assert all(m["directExit"][1] == [0, 0, 0] for m in meters.values())
        assert meters["white"]["second"] == meters["reopened"]["second"]
        assert meters["off"]["second"] == meters["entry"]["second"] == [[0, 0, 0]] * 3
        bright, red, grey = (meters[name]["second"][1] for name in ("white", "red", "grey"))
        assert bright[0] > red[0] > grey[0] and bright[1] > grey[1] > red[1]
        before, after = (out["sideScreen"][s][capture] for s in ("white", "screen"))
        assert before["wallBIncident"] == after["wallBIncident"]
        assert before["ceilingSupport"] == after["ceilingSupport"] == [[255, 255, 0]] * 3
        assert before["first"] == after["first"]
        red_fractions = [(new[0] / old[0])**2 for old, new in zip(before["second"], after["second"])]
        assert red_fractions[0] > .8 and max(red_fractions[1:]) < .01
    (here/"measurements.json").write_text(json.dumps(out,indent=2)+"\n")
    for stage,values in result.items():
        meters=values["orders"]["ingame"]
        print(stage,values["normal"]["ingame"],{k:v[1] for k,v in meters.items()})
    jp="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    font=ImageFont.truetype(jp,23)
    panels=Image.new("RGB",(4*352,2*276),(23,23,23));d=ImageDraw.Draw(panels)
    for i,stage in enumerate(stages):
        x=(i%4)*352;y=(i//4)*276
        photo=Image.open(here/"ordinary"/(stage+"-ingame.png")).convert("RGB").resize((352,198),Image.Resampling.LANCZOS)
        panels.paste(photo,(x,y))
        d.text((x+10,y+201),labels[stage],font=font,fill="white")
        meter=result[stage]["orders"]["ingame"]["second"][1]
        d.text((x+10,y+237),"二回反射  "+", ".join(map(str,meter)),font=ImageFont.truetype(jp,18),fill=(207,219,219))
    panels.save(here/"ceiling.jpg",quality=93)

if __name__=="__main__":
    main()
