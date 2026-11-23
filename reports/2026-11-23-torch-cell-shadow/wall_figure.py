"""Show the measured visibility of the torch on the same rear wall after each edit."""
from pathlib import Path
import sys

import numpy as np
from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-23-placed-penumbra"))
from score import check_record,unpack

def main():
    paper=Image.new("RGB",(1168,415),"#fcfcfa")
    pen=ImageDraw.Draw(paper)
    font="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    title,normal,small=[ImageFont.truetype(font,n) for n in (25,18,15)]
    pen.text((18,7),"松明から奥の壁に届く光",fill="#1b2832",font=title)
    pen.text((18,48),"同じ視点・同じ松明で、手前の白樺の幹だけを編集",fill="#263744",font=normal)
    for index,(stage,label) in enumerate((("cut-step","幹が立っている"),("trunk-cut","幹を撤去"),("replanted","同じ位置に植え直す"))):
        path=HERE/"grove"/(stage+"-ingame.png")
        check_record(path.parent,path)
        lights,p,_=unpack(path,1)
        vis,flag=lights[:,:,0,1],lights[:,:,0,2]
        x,y,z=np.moveaxis(p,-1,0)
        wall=(abs(z+412)<.006)&(y>151)&(y<155)&(x>404)&(x<410)&(flag>=64)
        surface=np.empty((*x.shape,3),dtype=np.uint8)
        surface[:]=[98,119,135]
        surface[wall]=vis[wall,None]
        # One receiver sample every eight horizontal screen pixels. Scale both
        # axes by the same screen-space factor, without interpolating visibility.
        crop=Image.fromarray(surface[80:444,62:118]).resize((378,307),Image.Resampling.NEAREST)
        left=10+index*386
        paper.paste(crop,(left,82))
        pen.text((left,388),label,fill="#182931",font=small)
    pen.text((520,21),"白　光がすべて届く　　　黒　完全な影　　　青灰　計測した壁の外",font=small,fill="#263744")
    paper.save(HERE/"wall.png")
if __name__=="__main__":
    main()
