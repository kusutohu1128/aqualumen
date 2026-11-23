"""Register the normal F2 photos and locate HDR outliers in the opaque comparison."""
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from measure import (HERE, STAGES, SOURCE_SHA, STUDY_SHA, PAIR_SHA, receipt,
                     frame, panels)

font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",17)


def normal_range(images):
    stack=np.stack(images).astype("int16")
    return stack.min(axis=0),stack.max(axis=0)


def main():
    meta={name:receipt(name,checksum) for name,checksum in
          (("forward",SOURCE_SHA),("stored",STUDY_SHA),("paired",PAIR_SHA))}
    table={}
    canvas=Image.new("RGB",(1120,720),"#16201f")
    draw=ImageDraw.Draw(canvas)
    for stage in STAGES:
        left=[frame("forward",meta["forward"],stage,tag) for tag in ("ingame","x11-a","x11-b")]
        right=[frame("stored",meta["stored"],stage,tag) for tag in ("ingame","x11-a","x11-b")]
        valid,owner,old,new,screen=panels(frame("paired",meta["paired"],stage,"ingame"))
        wet=valid & ((owner==4)|(owner==5))
        a,b=normal_range([im[1::2,1::2] for im in left])
        c,d=normal_range([im[1::2,1::2] for im in right])
        gap=np.maximum(0,np.maximum(a-d,c-b)).max(axis=2)
        base=abs(left[0][1::2,1::2].astype("int16")-right[0][1::2,1::2]).max(axis=2)
        stable=((b-a).max(axis=2)<=1)&((d-c).max(axis=2)<=1)&wet
        table[stage]={"wetProjectedSamples":int(wet.sum()),"wetStableInBoth":int(stable.sum()),
                      "f2DeltaP99":float(np.quantile(base[wet],.99)),
                      "rangeGapP99":float(np.quantile(gap[wet],.99)),"rangeGapMax":int(gap[wet].max()),
                      "stableGapP99":float(np.quantile(gap[stable],.99)) if stable.any() else None,
                      "stableGapMax":int(gap[stable].max()) if stable.any() else None,
                      "stableGapOver2":int((gap[stable]>2).sum()) if stable.any() else None}
        if stage!="wet-leaf-cow":continue
        for i,(im,caption) in enumerate(((left[0],"前方描画　雨の夜、暖色と青のランタン"),(right[0],"最前面で照明を計算　同じ視点・同じ配置"))):
            canvas.paste(Image.fromarray(im).resize((560,315),Image.Resampling.LANCZOS),(i*560,0))
            draw.text((10+i*560,320),caption,fill="white",font=font)
        # Localize the rare large linear differences on the real floor.
        scene=right[0][1::2,1::2]
        marker=scene.copy()
        hot=(old > 32768+1024*np.log2(.01))&wet
        marker[hot]=[255,32,112]
        y,x=np.unravel_index(np.where(wet,old,0).argmax(),wet.shape)
        X=max(0,min(int(x)-140,800-280));Y=max(0,min(int(y)-77,450-157))
        for i,(img,label) in enumerate(((scene,"濡れた床の拡大"),(marker,"赤　表示前の光量差が0.01を超えた点"))):
            crop=Image.fromarray(img[Y:Y+157,X:X+280]).resize((560,314),Image.Resampling.NEAREST)
            canvas.paste(crop,(i*560,362))
            draw.text((i*560+10,683),label,fill="white",font=font)
    (HERE/"normal-images.json").write_text(json.dumps(table,indent=2)+"\n")
    canvas.save(HERE/"wet-floor.jpg",quality=95)
    print(table)


if __name__=="__main__":
    main()
