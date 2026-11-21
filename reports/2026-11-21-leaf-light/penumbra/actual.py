"""Compare the changed wall pixels against a separate 1,024-ray finite-disk prediction."""
from pathlib import Path
import json,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont

here=Path(__file__).resolve().parent
projected=here.parent/'projected'
variant=sys.argv[1]
samples=np.load(here/'oracle-roi.npz',allow_pickle=False)
models=list(samples['models'])
idx=models.index('shaderG')
x0,y0,x1,y1=map(int,samples['roi'])
three=samples['tap3'][idx].astype(float)
dense=samples['dense1024'][idx].astype(float)
change=dense-three
def channel(tag,role):
    rgb=np.asarray(Image.open(projected/tag/(role+'.png')).convert('RGB'))
    return rgb[y0:y1,x0:x1,1].astype(float)
before=channel('accepted','foliage')
after=channel(variant,'foliage')
usable=samples['valid'].astype(bool)&(channel('accepted','open')-channel('accepted','dark')>32)
def observations(mask):
    delta=(after-before)[mask]
    predicted=change[mask]
    return dict(pixels=int(mask.sum()),meanGreenChange=round(float(delta.mean()),3),
                medianGreenChange=float(np.median(delta)),correctSign=float(np.mean(delta*predicted>0)),
                expectedMeanTransmissionChange=round(float(predicted.mean()),5))
def fit(frame,tag,mask):
    off=channel(tag,'dark')
    norm=(frame-off)/np.maximum(channel(tag,'open')-off,1.)
    return {k:round(float(np.corrcoef(norm[mask],v[mask])[0,1]),5) for k,v in [('dense1024',dense),('threeRays',three)]}
report=dict(reference='oracle-roi.npz, shaderG, fixed leaf and mint-free warm torch geometry',
            before='accepted',after=variant,roi=[x0,y0,x1,y1],usablePixels=int(usable.sum()),
            predictedDarker=observations(usable&(change<-.06)),predictedBrighter=observations(usable&(change>.06)),
            correlationToDisplayGreen=dict(before=fit(before,'accepted',usable),after=fit(after,variant,usable)),
            note='A display-channel difference is not a linear transmittance. The selected pixel groups and the direction of change were predicted without the new screenshot.')
(here/(variant+'-wall.json')).write_text(json.dumps(report,indent=2)+'\n')
cols=[('1.7.0',projected/'before'),('葉を3方向から計算',projected/'accepted'),('面積を持つ松明',projected/variant)]
sheet=Image.new('RGB',(1230,565),'#191a18');draw=ImageDraw.Draw(sheet)
font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
large=ImageFont.truetype(font,26);small=ImageFont.truetype(font,20)
draw.text((12,4),'松明と壁の間の葉が作る影',font=large,fill='#eeeae0')
for i,(title,directory) in enumerate(cols):
    src=Image.open(directory/'foliage.png').convert('RGB');left=8+i*410
    sheet.paste(src.resize((400,225),Image.Resampling.LANCZOS),(left,46))
    draw.text((left,276),title,font=small,fill='#eeeae0')
    # This is the unobscured upper-left silhouette measured by the oracle.
    crop=src.crop((536,270,700,410)).resize((278,238),Image.Resampling.NEAREST)
    sheet.paste(crop,(left,315))
sheet.save(here/(variant+'-wall.jpg'),quality=95,subsampling=0)
print(report)
