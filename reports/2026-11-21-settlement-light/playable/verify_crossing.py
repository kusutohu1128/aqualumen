"""Compare the vanilla F3 biome at the two ends of the same ordinary, rainy save."""
import json,string,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
here=Path(__file__).resolve().parent
root=here.parents[2]
sys.path.insert(0,str(root/'reports/2026-11-21-rain-eaves/journey'))
import hud
r=here/'village-to-plains'
read=lambda p: json.loads(p.read_text())
before=read(here/'enter-by-porch/complete.json')
after=read(r/'complete.json')
assert after['cleanExit'] and not after['logErrors'] and after['revisit']['previousSaveUnchanged']
assert before['packSha256']==after['packSha256'] and after['savedPlayer']['playerGameType']==after['savedLevel']['allowCommands']==0
assert after['walkMetres']>before['walkMetres']+100
seen={}
for key in ('villageF3','plainsF3'):
    o=after['results'][key]
    canvas=np.asarray(Image.open(r/o['f3Image']).convert('RGB'))
    biome=hud.row_text(canvas,'Biome: ',string.ascii_lowercase+':_ ')
    assert biome and biome.startswith('minecraft:'),o
    seen[key]=dict(biome=biome,position=o['xyz'],F3=o['f3Image'])
assert seen['villageF3']['biome']=='minecraft:snowy_plains' and seen['plainsF3']['biome']=='minecraft:plains',seen
st=before['savedLevel'];ed=after['savedLevel'];dt=ed['Time']-st['Time']
# The vanilla counter decreases one tick per tick while the same storm is active.
same_storm=bool(st['raining']==ed['raining']==1 and st['rainTime']-ed['rainTime']==dt)
doc=dict(seed=20261139,waypointsReached=after['results']['waypointsReached'],biomes=seen,sameStorm=same_storm,
         worldTicks=dt,initialRainTime=st['rainTime'],finalRainTime=ed['rainTime'],elapsedSeconds=after['seconds'],
         walkedMetres=after['revisit']['walkedAfterReloadMetres'],normalPlayer=True,pack=after['packSha256'],
         note='Biome read from the actual Minecraft F3 images. The initial weather for this save was set in the starter level.dat; the trip used the ordinary weather cycle.')
(r/'biome-crossing.json').write_text(json.dumps(doc,indent=2)+'\n')
sheet=Image.new('RGB',(1280,398),'#1a2024');draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',22)
for i,(path,text) in enumerate([(here/'ordinary-house/snowy-village.png','雪の降る村　snowy_plains'),(r/after['results']['plains'],'歩いて着いた平原　plains')]):
    im=Image.open(path).convert('RGB').resize((640,360),Image.Resampling.LANCZOS)
    sheet.paste(im,(640*i,0));draw.text((640*i+9,363),text,font=font,fill='white')
sheet.save(r/'snow-to-plains.jpg',quality=93,subsampling=0)
print(doc)
