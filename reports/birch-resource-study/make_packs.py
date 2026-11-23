from pathlib import Path
import json, zipfile, io
from PIL import Image
ROOT=Path(__file__).resolve().parent
# Pixel-art stamps drawn at native resolution. Coordinates wrap at the tile edges.
palette=['#bdbab0','#c9c7bc','#d6d3c7','#aaa99f','#817f79','#514f4b']
variants={
 'A':[(2,3,'11132'),(21,6,'211'),(11,12,'211132'),(30,18,'113'),(5,24,'21113'),(23,28,'21')],
 'B':[(29,2,'123321'),(12,5,'211'),(3,9,'2133221'),(22,13,'1221'),(10,17,'2123321'),(27,20,'211'),(0,24,'12321'),(17,29,'11221')],
 'C':[(26,1,'212333221'),(6,5,'121'),(17,8,'122321'),(30,12,'12332221'),(10,15,'21221'),(22,19,'123321'),(2,21,'211'),(8,25,'12333221'),(27,28,'1221'),(0,31,'121')]
}
for name,marks in variants.items():
 im=Image.new('RGB',(32,32),palette[1])
 def dot(x,y,c): im.putpixel((x%32,y%32),tuple(bytes.fromhex(palette[c][1:])))
 for x,y,w in [(27,0,8),(11,4,5),(2,8,11),(18,10,6),(9,15,7),(26,17,9),(4,22,5),(15,26,10),(4,30,6)]:
  for k in range(w): dot(x+k,y,0)
  for k in range(1,w-1): dot(x+k,y-1,2)
 for x,y,shape in marks:
  for k,h in enumerate(map(int,shape)):
   dot(x+k,y,4 if h==1 else 5)
   if h>1: dot(x+k,y-1,3 if h==2 else 4)
   dot(x+k,y+1,2)
 im.save(ROOT/f'birch-{name}.png')
 with zipfile.ZipFile(ROOT/f'Aqualumen-Birch-{name}.zip','w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('pack.mcmeta',json.dumps({'pack':{'pack_format':34,'description':f'Aqualumen Birch {name} | 32x'}}))
  z.write(ROOT/f'birch-{name}.png','assets/minecraft/textures/block/birch_log.png')
