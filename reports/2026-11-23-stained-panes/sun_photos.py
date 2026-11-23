"""Use the same marked patch of floor in four unmodified game screenshots."""
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from score import HERE,reader
meter=HERE/"pane/air-ingame.png"
reader.check_record(meter.parent,meter)
_,positions,_=reader.unpack(meter,1)
target=np.array([408.6,151.,-409.25])
error=np.linalg.norm(positions-target,axis=2)
y,column=np.unravel_index(np.argmin(error),error.shape)
assert error[y,column]<.06
cols,rows=2,2
w,h=600,338
canvas=Image.new("RGB",(cols*w,rows*(h+31)),"#181a1b")
font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",16)
draw=ImageDraw.Draw(canvas)
for i,(folder,stage,title) in enumerate([
    ("sun-window","red","Torch-only version  /  red window"),
    ("sun-filtered","red","Filtered sunlight  /  red window"),
    ("sun-window","blue","Torch-only version  /  blue window"),
    ("sun-filtered","blue","Filtered sunlight  /  blue window")]):
    source=HERE/folder/(stage+"-ingame.png");reader.check_record(source.parent,source)
    frame=Image.open(source).convert("RGB")
    ox,oy=i%2*w,i//2*(h+31)
    canvas.paste(frame.resize((w,h),Image.Resampling.LANCZOS),(ox,oy))
    px=int(ox+w*(column*8+.5)/frame.width);py=int(oy+h*(y+.5)/frame.height)
    draw.ellipse((px-7,py-7,px+7,py+7),outline="#343434",width=2)
    draw.ellipse((px-9,py-9,px+9,py+9),outline="white",width=1)
    draw.text((ox+10,oy+h+5),title,font=font,fill="white")
canvas.save(HERE/"sunlight.jpg",quality=95)
