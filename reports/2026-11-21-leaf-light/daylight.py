"""Measure fixed ground and bark patches during the same daylight torch placement."""
from pathlib import Path
import json,sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

here=Path(__file__).resolve().parent
crop_names=("ground-noon","ground-evening","ground-low-sun")
verified=sys.argv[1] if len(sys.argv)>1 else "timing-accepted"
output="daylight" if verified=="timing-accepted" else verified+"-daylight"
bundles=("timing-before",verified,"reference-photon")
areas={"litBirchBark":[775,760,818,811], "grassBesideLamp":[1118,1172,1176,1224],
       "backgroundOak":[1282,595,1325,636]}
result={}
for directory in bundles:
    capture=here/directory/'capture'
    if not capture.exists(): continue
    entries={}
    for role in crop_names:
        data=json.loads((capture/(role+'.json')).read_text())
        rgbs=np.asarray(Image.open(capture/(role+'.png')).convert('RGB'))/255.
        f=data['opaque_fixture']
        assert list(rgbs.shape)==[1440,2560,3] and data['shader_active'] and not data['shader_fallback'] and data['camera_eye_match']
        measurements={}
        for key,(x0,y0,x1,y1) in areas.items():
            x=rgbs[y0:y1,x0:x1,:]
            light=np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
            measurements[key]=dict(meanDisplayRGB=(x.mean(axis=(0,1))*255).round(2).tolist(),
                meanLinearizedDisplayLuma=round(float((light@[.2126,.7152,.0722]).mean()),6))
        entries[f['variant']]=dict(dayTime=f['actual_server_world_time'],eye=data['actual_eye_position'],
            frames=data['frames'],meanFps=data['mean_fps'],p99Milliseconds=data['p99_ms'],
            sampleSeconds=data['recorded_seconds'],patches=measurements)
    result[directory]=entries
assert verified in result
(here/(output+'.json')).write_text(json.dumps(dict(pixelRectsXYXY=areas,scenes=result,
    note='Mean of decoded display pixels on the same physical patches; weather, tone mapping and small texture details remain in the image.'),indent=2)+'\n')
labels=("消灯","松明","魂の松明")
canvas=Image.new('RGB',(1440,351),'#191a18');pen=ImageDraw.Draw(canvas)
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',24)
pen.text((12,3),'昼の白樺の木陰で、松明の色を替える',font=font,fill='white')
for i,(role,label) in enumerate(zip(crop_names,labels)):
    photo=Image.open(here/verified/'capture'/(role+'.png')).convert('RGB').resize((470,264),Image.Resampling.LANCZOS)
    x=6+i*480
    canvas.paste(photo,(x,44))
    pen.text((x,310),label,font=font,fill='white')
canvas.save(here/(output+'.jpg'),quality=94,subsampling=0)
