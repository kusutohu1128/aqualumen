from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import json,numpy as np
p=Path(__file__).resolve().parent
proof=json.loads((p/'comparison.json').read_text())
fit=np.load(p/'mask-fit.npz')
erode=lambda m:np.asarray(Image.fromarray(m.astype('uint8')*255).filter(ImageFilter.MinFilter(3)))>0
ore=erode(fit['ore']);rock=erode(fit['rock'])
Y,X=np.indices(ore.shape)
deltas={}
for stage in ('left','right'):
 imgs=[np.asarray(Image.open(p/proof[v]/f'{stage}-ingame.png').convert('RGB'),dtype=float) for v in ['control','faceted']]
 dy=(imgs[1]-imgs[0]) @ np.array([.2126,.7152,.0722])
 adjusted=np.zeros_like(dy)
 for bx,by in zip([404,405,405,406,407,407,408],[153,153,152,152,152,151,151]):
  tile=((np.floor(406.5+(X+.5-640)/fit['scale'])==bx)&(np.floor(fit['eye']-(Y+.5-360)/fit['scale'])==by))
  adjusted[tile]=dy[tile]-np.median(dy[tile&rock])
 val=adjusted[ore];deltas[stage]=adjusted
 proof[stage]['oreLumaCorrected']={'samples':int(val.size),'p01_10_50_90_95_99_max':np.percentile(val,[1,10,50,90,95,99,100]).round(2).tolist(),'above3':float((val>3).mean()),'belowMinus3':float((val< -3).mean()),'surroundingRockRawMedian':np.median(dy[rock]).round(3).item()}
# Show largest true positive over control (no enhancement), with fixed crop across both positions.
diff=np.where(ore,np.abs(deltas['right']-deltas['left']),0)
scored=[]
for y in range(225,480,8):
 for x in range(370,861,8):
  scored.append((float(np.mean(diff[y:y+112,x:x+160])),x,y))
_,x,y=max(scored)
canvas=Image.new('RGB',(980,778),'#1b1d1e');draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',22)
for row,v in enumerate(['control','faceted']):
 for col,stage in enumerate(['left','right']):
  im=Image.open(p/proof[v]/f'{stage}-ingame.png')
  canvas.paste(im.crop((x,y,x+160,y+112)).resize((480,336),Image.Resampling.NEAREST),(6+488*col,43+386*row))
  draw.text((8+488*col,4+386*row),('対照' if v=='control' else '粒の反射')+'　'+('左から点灯' if stage=='left' else '右から点灯'),font=font,fill='white')
canvas.save(p/'gold-grains-crop.png')
proof['crop']=[x,y,x+160,y+112];proof['samePixelStageDifference']={'p90':float(np.percentile(diff[ore],90)),'above3':float(np.mean(diff[ore]>3))}
(p/'comparison-signed.json').write_text(json.dumps(proof,indent=2))
print(json.dumps(proof))
