"""Read the two 8-bit display differences directly from calibrated Minecraft screenshots."""
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from measure import HERE, PREVIOUS, STAGES, CAL, STUDY_SHA, read, receipt, frame, largest_cluster

FLOOR_SHA="47a56930f2fb2206f0c3dae1a493e34509ef1b48131e5f5c725426674dcebd41"
RUN="flat-stone-lamp-r2"


def stats(mask, difference):
    values=difference[mask]
    maximum=int(values.max())
    y,x=np.unravel_index(np.where(mask,difference,0).argmax(),difference.shape)
    return dict(samples=len(values),maxCode=maximum,peakXY=[int(x),int(y)] if maximum else None,
                p99=float(np.quantile(values,.99)),aboveOne=int((values>1).sum()),aboveFour=int((values>4).sum()),
                connectedAboveFour=largest_cluster(mask & (difference>4)))


def main():
    geometry=dict(read(PREVIOUS/"wet-ownership/geometry.json"),middleCamera=[409.48,151,-405.95,143.8,18.])
    run=receipt(RUN,FLOOR_SHA,geometry)
    baseline=receipt("stored",STUDY_SHA)
    result={}
    for stage in STAGES:
        result[stage]={}
        for name in run["screenshots"][stage]:
            image=frame(RUN,run,stage,name)
            assert np.array_equal(image[2,8:264],CAL)
            assert not (image[:,:,2]==252).any(), "non-finite radiance"
            mask=image[:,:,2]==187
            assert mask.sum()>10000
            result[stage][name]={key:stats(mask,image[:,:,channel]) for channel,key in enumerate(("local","specular"))}
            if stage=="wet-cleared" and name=="ingame":
                raw=frame("stored",baseline,stage,name)
                # Both photographs use the original camera. The colored areas
                # correspond to the surveyed floor in the meter's own frame.
                marked=raw.copy()
                marked[mask & (image[:,:,0]>1)]=[246,166,39]
                marked[mask & (image[:,:,0]>4)]=[244,47,103]
                tile=Image.new("RGB",(1120,360),"#142020")
                draw=ImageDraw.Draw(tile)
                font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",15)
                for i,(picture,caption) in enumerate(((raw,"通常の空間照明　雨の丸石と二灯"),(marked,"水平な面で局所光を再計算　橙は2階調以上、赤は5階調以上"))):
                    tile.paste(Image.fromarray(picture).resize((560,315),Image.Resampling.LANCZOS),(560*i,0))
                    draw.text((560*i+8,322),caption,font=font,fill="white")
                tile.save(HERE/"flat-stone.jpg",quality=95)
        print(stage,result[stage]["ingame"])
    (HERE/"flat-stone.json").write_text(json.dumps(result,indent=2)+"\n")


if __name__=="__main__":
    main()
