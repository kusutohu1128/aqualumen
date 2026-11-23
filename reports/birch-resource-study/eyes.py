from PIL import Image, ImageDraw
from pathlib import Path
import io,json,zipfile
p=Path(__file__).resolve().parent
ink=['#c5c1b3','#d4d0c0','#e0d9c4','#a9a798','#7b7870','#494947','#67594d']
def raw(im):
 b=io.BytesIO();im.save(b,'PNG');return b.getvalue()
models=[]
with zipfile.ZipFile(p/'Aqualumen-Birch-D.zip','w',zipfile.ZIP_DEFLATED) as z:
 def put(k,obj):z.writestr(k,json.dumps(obj))
 put('pack.mcmeta',{'pack':{'pack_format':34,'description':'Birch D / Watching Woods / 32x'}})
 for axis,rot in [('y',{}),('x',{'x':90,'y':90}),('z',{'x':90})]:
  models.append((f'axis={axis}',[{'model':f'minecraft:block/aql_eye_{i}', 'weight':w,**rot} for i,w in enumerate((4,3,2))]))
 put('assets/minecraft/blockstates/birch_log.json',{'variants':dict(models)})
 for i in range(3):
  im=Image.new('RGB',(32,32),ink[0]); d=ImageDraw.Draw(im)
  def line(points,c):d.line(points,fill=ink[c])
  for x,y,l in [(0,2,6),(12,5,9),(25,1,6),(1,12,5),(16,18,6),(26,21,5),(2,26,11),(20,30,7)]:
   y=(y+i*4)%32
   line([(x,y),(x+l,y)],3);line([(x+2,(y+1)%32),(x+l,(y+1)%32)],1)
  if i==0: # Curling paper: shadow below the lifted lip, pale edge above.
   d.polygon([(2,17),(9,16),(14,13),(11,17),(7,19),(4,19)],fill=ink[3])
   line([(2,17),(9,16),(14,13)],2);line([(5,19),(8,18),(11,17)],4)
  else:
   x,y=(8,12) if i==1 else (19,22)
   line([(x-7,y+1),(x-4,y),(x-1,y-3),(x+2,y-3),(x+5,y-1),(x+8,y-1)],3)
   line([(x-6,y+1),(x-3,y),(x-1,y-2),(x+2,y-2),(x+4,y),(x+7,y)],5)
   line([(x-3,y+1),(x,y+2),(x+3,y+1),(x+5,y)],4)
   d.rectangle((x,y-1,x+1,y),fill=ink[6]);d.point((x,y-1),fill=ink[2])
   line([(x-4,y+2),(x,y+3),(x+3,y+2)],2)
  im.save(p/f'eye-{i}.png');z.writestr(f'assets/minecraft/textures/block/aql_eye_{i}.png',raw(im))
  put(f'assets/minecraft/models/block/aql_eye_{i}.json',{'parent':'minecraft:block/cube_column','textures':{'end':'minecraft:block/birch_log_top','side':f'minecraft:block/aql_eye_{i}'}})
