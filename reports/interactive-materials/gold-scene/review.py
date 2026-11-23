import json,glob,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
p=Path(__file__).resolve().parent
proof={}
def valid(prefix):
 for f in sorted(p.glob(prefix+'-*/complete.json')):
  result=json.loads(f.read_text())
  if result.get('complete'):
   pre=json.loads((f.parent/'preflight.json').read_text())
   assert pre['labAfter']==pre['labBefore'] and not pre['foreignObservations']
   return f.parent
 raise ValueError(prefix)
size=(640,360); s=Image.new('RGB',(1316,850),'#191c1d');d=ImageDraw.Draw(s)
f=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',23)
d.text((12,10),'金鉱石　同じカメラ・同じ色テクスチャ・1本の松明',font=f,fill='white')
arrays={}
for row,(kind,title) in enumerate([('control','平面対照'),('faceted','粒ごとに反射')]):
 dr=valid(kind); proof[kind]=dr.name
 assert 'Aqualumen-Gold-' in (dr/'client.log').read_text()
 for col,(stage,side) in enumerate([('left','左の松明'),('right','右の松明')]):
  a=Image.open(dr/f'{stage}-ingame.png').convert('RGB')
  arrays[kind,stage]=np.asarray(a)
  x=12+col*652;y=55+row*395
  d.text((x,y),f'{title}   /   {side}',font=f,fill='#e9e5db')
  s.paste(a.resize(size,Image.Resampling.LANCZOS),(x,y+34))
s.save(p/'gold-in-game.jpg',quality=95,subsampling=0)
for stage in ['left','right']:
 d=np.abs(arrays['faceted',stage].astype(int)-arrays['control',stage].astype(int))
 proof[stage]={'pixelsRGBMoreThan8':int((d.max(axis=2)>8).sum()),'maximumRGBDifference':int(d.max())}
(p/'comparison.json').write_text(json.dumps(proof,indent=2))
print(proof)
