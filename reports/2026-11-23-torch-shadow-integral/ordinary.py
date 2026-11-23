"""Compare the normal game pixel at the offending light path, with its surrounding terrain."""
import json
from pathlib import Path
import re
import sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-23-placed-penumbra"))
from score import check_record,unpack,face_from_geometry,worldgrid,FOREST_ANCHOR


def luma_difference(values):
    assert len(values)>0
    return dict(n=int(len(values)),meanAbsDisplayLuma=float(values.mean()),
                medianAbsDisplayLuma=float(np.median(values)),p95AbsDisplayLuma=float(np.quantile(values,.95)),
                lumaOver1=int((values>1.).sum()),lumaOver3=int((values>3.).sum()))


if __name__=="__main__":
    mode=tuple(sys.argv[1:])
    prefixes={(): "", ("--night",): "night-", ("--night-settled",): "settled-night-",
              ("--geometry",): "settled-night-"}
    prefix=prefixes[mode]
    night=bool(prefix)
    cone=mode==("--geometry",)
    modes=("ordinary-contours","ordinary-geometry" if cone else "ordinary-motion24")
    resultName="geometry" if cone else "motion"
    record=json.loads((HERE/"birch-transitions.json").read_text())["worstByPoseAndLamp"][0]
    x,y=record["screen"]
    stats={};images={}
    warmup={}
    grid=worldgrid()
    for stage in ("left","centre"):
        pair=[]
        for pack in modes:
            folder=HERE/(prefix+pack)
            assert json.loads((folder/"geometry.json").read_text())["time"]==(18000 if night else 9800)
            if prefix=="settled-night-" and stage=="left":
                log=(folder/"client.log").read_text()
                warm=log.index("AQLAVA_BEGIN_warm-first_END")
                left=log.index("AQLAVA_READY_left_END",warm)
                ends=re.findall(r"AQ_RENDER_FRAME_END (\d+) (\d+)",log[warm:left])
                ms=int(ends[-1][0])-int(ends[0][0])
                frames=int(ends[-1][1])-int(ends[0][1])
                assert ms>=45_000 and frames>=150
                warmup[pack]=dict(milliseconds=ms,renderedFrames=frames)
            f=folder/(stage+"-ingame.png")
            digest=check_record(folder,f)
            with Image.open(f) as photo:
                im=photo.convert("RGB");a=np.asarray(im)
            assert a.shape==(720,1280,3)
            pair.append(a.astype(float))
            images[stage,pack]=im
        region=(slice(y-12,y+13),slice(x-12,x+13))
        delta=pair[1]-pair[0];luma=delta@np.array([.2126,.7152,.0722])
        xEye=208.98 if stage=="left" else 209.
        meters=[]
        for folder in ("birch-two-caps","birch-joint" if cone else "birch-motion24"):
            f=HERE/folder/(stage+"-ingame.png")
            check_record(f.parent,f)
            meters.append(unpack(f,2))
        (av,p,af),(bv,q,bf)=meters
        face=face_from_geometry(p,np.array([xEye,65.62,355.5]))
        n=np.stack([(face==2*j+2).astype(float)-(face==2*j+1) for j in range(3)],axis=2)
        cell=np.floor(p-.005*n).astype(int)-FOREST_ANCHOR
        solid=grid[tuple(np.moveaxis(np.clip(cell,0,63),-1,0))]==1
        registered=solid&(face!=0)&((af==0)|(af==face))&((bf==0)|(bf==face))&(np.max(abs(p-q),axis=2)<.001)
        valid=(av[:,:,:,2]>=64)&(bv[:,:,:,2]>=64)&(((av[:,:,:,2]|bv[:,:,:,2])&12)==0)
        meaningful=abs(bv[:,:,:,1].astype(int)-av[:,:,:,1].astype(int))>=26
        samples=registered&(valid&meaningful).any(axis=2)
        activeA=av[:,:,:,2]>=64
        activeB=bv[:,:,:,2]>=64
        same=(registered & activeA.any(axis=2) & (activeA==activeB).all(axis=2)
              & ((~activeA) | (valid & (av[:,:,:,1]==bv[:,:,:,1]))).all(axis=2))
        dy=abs(luma[:-5,::8])
        stats[stage]=dict(largeVisibilityChanges=luma_difference(dy[samples]),unchangedVisibility=luma_difference(dy[same]),
                          prior=pair[0][y,x].astype(int).tolist(),trial=pair[1][y,x].astype(int).tolist(),
                          luma=float(luma[y,x]),cropMedianAbs=float(np.median(abs(luma[region]))),
                          cropMaxAbs=float(abs(luma[region]).max()),cropSamples=int(luma[region].size))
    output=dict(pixel=[x,y],frames=stats)
    if warmup:output["warmup"]=warmup
    (HERE/(prefix+"ordinary-"+resultName+".json")).write_text(json.dumps(output,indent=2)+"\n")
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",16)
    canvas=Image.new("RGB",(858,552),(25,28,30))
    draw=ImageDraw.Draw(canvas)
    overview=images["left","ordinary-contours"].resize((480,270),Image.Resampling.LANCZOS)
    canvas.paste(overview,(12,18))
    cx=12+x*480/1280;cy=18+y*270/720
    draw.rectangle((cx-6,cy-6,cx+6,cy+6),outline=(255,215,78),width=2)
    draw.text((14,305),"Birch forest | 4 torches | "+("midnight" if night else "daylight"),font=font,fill="white")
    draw.text((14,334),"Gold box: measured grass surface",font=font,fill="white")
    for col,stage in enumerate(("left","centre")):
        sx=506+col*170
        draw.text((sx,14),"x = "+("208.98" if stage=="left" else "209.00"),font=font,fill="white")
        for row,pack in enumerate(modes):
            sy=51+row*228
            trialLabel="Disk blocker search" if cone else "24 samples"
            draw.text((sx,sy),"3 samples" if row==0 else trialLabel,font=font,fill="white")
            tile=images[stage,pack].crop((x-20,y-20,x+21,y+21)).resize((164,164),Image.Resampling.NEAREST)
            canvas.paste(tile,(sx,sy+28))
            draw.rectangle((sx+79,sy+107,sx+84,sy+112),outline=(255,215,78))
    imageName="grass-geometry.png" if cone else "grass-display.png"
    canvas.crop((0,0,858,499)).save(HERE/(prefix+imageName))
