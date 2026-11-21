from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
r=Path(__file__).resolve().parent
def read(role,scene):
 d=r/role/'capture'
 with (d/(scene+'.json')).open() as f:state=json.load(f)
 assert state['shader_active'] and not state['shader_fallback'] and state['camera_follows_local_player'] and state['window_focused']
 if scene.startswith('underwater-up'):
  assert state['underwater_up']['camera_submersion_type']=='WATER'
 return Image.open(d/(scene+'.png')).convert('RGB'),state
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
result={}
for scene,baseline in [('underwater-up-deep','pinned'),('underwater-up-tilt','control-extra')]:
 a,sa=read(baseline,scene);b,sb=read('candidate',scene);ref,sr=read('reference',scene)
 assert a.size==b.size==(960,540) and ref.size==(1920,1080)
 assert all(np.max(np.abs(np.array(t['actual_camera_position'])-sa['actual_camera_position']))<1e-4 and t['actual_camera_rotation']==sa['actual_camera_rotation'] for t in (sb,sr))
 # Display-space reconstruction reference. Decode the packed gamma-2.2 display values before averaging.
 lin=(np.asarray(ref)/255.)**2.2
 target=lin.reshape(540,2,960,2,3).mean(axis=(1,3))**(1/2.2)*255
 a0=np.asarray(a).astype(float);b0=np.asarray(b).astype(float)
 h,w=target.shape[:2];yy,xx=np.mgrid[:h,:w];rad=np.hypot(xx+0.5-w/2,yy+0.5-h/2)/w
 mask=(rad>.39)&(rad<.50) if scene.endswith('deep') else np.ones((h,w),dtype=bool)
 def err(pixels):
  e=np.abs(pixels-target)[mask]
  return dict(meanAbsRGB=float(e.mean()),p95AbsRGB=float(np.quantile(e,.95)),rmsRGB=float(np.sqrt(np.mean(e**2))))
 result[scene]={'pixels':int(mask.sum()),'baseline':err(a0),'candidate':err(b0),'condition':'fixed underwater view; normalized screen radius 0.39..0.50' if scene.endswith('deep') else 'whole image'}
 if scene.endswith('deep'):
  refim=Image.fromarray(np.uint8(np.clip(target+.5,0,255)))
  # Full images above their matching 2x detail crops, no contrast adjustments.
  board=Image.new('RGB',(1440,450),'#172126');draw=ImageDraw.Draw(board)
  for i,(im,label) in enumerate([(a,'1.0.0'),(b,'1.0.1'),(refim,'Higher-sample reference')]):
   x=i*480;board.paste(im.resize((480,270),Image.Resampling.LANCZOS),(x,26))
   crop=im.crop((0,277,240,350));board.paste(crop.resize((480,146),Image.Resampling.NEAREST),(x,302))
   draw.text((x+8,2),label,font=font,fill='white')
  board.save(r/'comparison.jpg',quality=95)
print(json.dumps(result,indent=2))
(r/'quality.json').write_text(json.dumps(result,indent=2)+'\n')
