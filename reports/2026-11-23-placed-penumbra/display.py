"""Read actual ordinary F2s at the registered white wall shadow edge."""
import sys
from PIL import Image,ImageDraw,ImageFont
import numpy as np
import json
from score import HERE,WORK,WEIGHTS,check_record

def photo(folder):
    path=folder/"trunk-ingame.png"
    check_record(folder,path)
    return Image.open(path).convert("RGB")

def compare(folder):
    old=photo(HERE.parent/"2026-11-23-torch-open-volume/grove-cell")
    new=photo(folder)
    # The left penumbra belongs to the same smooth back wall throughout
    # these scanlines. Select its extent independently using the CPU reference.
    ref=np.load(WORK/"trunk-wall-reference.npy")
    rows=[]
    for y in range(150,365):
        x=np.where((ref[y]>.005)&(ref[y]<.995)&(np.arange(ref.shape[1])*8<725))[0]
        if not x.size or x[0]==0 or x[-1]+1>=ref.shape[1]: continue
        if ref[y,x[0]-1]<0. or ref[y,x[-1]+1]<0.: continue
        rows.append((y,8*int(x[0])-8,8*int(x[-1])+9))
    assert len(rows)>150
    def steps(im):
        rgb=np.array(im)
        y=rgb@WEIGHTS
        peaks=[abs(np.diff(y[r,a:b])).max() for r,a,b in rows]
        allSteps=np.concatenate([abs(np.diff(y[r,a:b])) for r,a,b in rows])
        return dict(rows=len(peaks),meanMaximumAdjacentLumaStep=float(np.mean(peaks)),p95Maximum=float(np.quantile(peaks,.95)),
                    worst=float(max(peaks)),edgesOverThreeLevels=int(np.count_nonzero(allSteps>3.)))
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",20)
    tile=(530,298)
    sheet=Image.new("RGB",(tile[0]*2,544),(19,22,24))
    draw=ImageDraw.Draw(sheet)
    for i,(im,label) in enumerate([(old,"Previous three-ray shadows"),(new,"Revised placed-torch shadows")]):
        x=i*tile[0]
        draw.text((x+12,6),label,font=font,fill="white")
        sheet.paste(im.resize(tile,Image.Resampling.LANCZOS),(x,34))
        crop=(601,150,699,185)
        sheet.paste(im.crop(crop).resize((490,175),Image.Resampling.NEAREST),(x+20,353))
        rr=tuple((v*tile[0]//im.width+x if j%2==0 else v*tile[1]//im.height+34) for j,v in enumerate(crop))
        draw.rectangle(rr,outline=(133,242,232),width=1)
    sheet.save(HERE/(folder.name+"-wall.png"))
    return dict(old=steps(old),trial=steps(new),wallRegion=dict(y=[150,364],xMaximum=725,source="independent reference"))
if __name__=="__main__":
    folder=HERE/sys.argv[1]
    (HERE/(folder.name+"-display.json")).write_text(json.dumps(compare(folder),indent=2)+"\n")
