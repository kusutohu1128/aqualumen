from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
p=Path(__file__).resolve().parent
font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
def getrun(variants):
 for v in variants.split('/'):
  for rec in sorted(p.glob('water-'+v+'-*/complete.json'),key=lambda a:a.stat().st_mtime,reverse=True):
   if json.loads(rec.read_text()).get('complete'):return rec.parent
 return None
rows=[(getrun(k),title) for k,title in [('combined/candidate','試作を適用'),('debug','天井が受けた水面反射を強調'),('baseline','比較用　preview.10')]]
rows=[r for r in rows if r[0]]
assert rows
screen=Image.new('RGB',(1200,50+len(rows)*268),'#151a1c');d=ImageDraw.Draw(screen)
for j,t in enumerate(['天窓・水あり','天窓を閉じる','水を石に替える']):
 d.text((10+j*400,6),t,font=ImageFont.truetype(font,26),fill='#efeadd')
for i,(folder,title) in enumerate(rows):
 y=52+268*i
 d.text((12,y),title,font=ImageFont.truetype(font,20),fill='#bdd5d3')
 for j,s in enumerate(['open','closed','dry']):
  with Image.open(folder/(s+'-ingame.png')) as f:
   assert f.size==(1280,720)
   screen.paste(f.convert('RGB').resize((398,224),Image.Resampling.LANCZOS),(400*j+1,y+31))
screen.save(p/'water-minecraft-comparison.jpg',quality=94,subsampling=0)
