from pathlib import Path
import sys, json
from PIL import Image,ImageDraw,ImageFont,ImageStat,ImageChops
here=Path(__file__).parent
run=here/sys.argv[1]; receipt=json.loads((run/'complete.json').read_text())
assert receipt['complete']
labels=[('open','格子なし'),('grate','銅格子'),('redglass','格子 ＋ 赤いガラス'),('duo','格子 ＋ 通常・魂のランタン')]
dest=Image.new('RGB',(1200,800),'#181b1d')
d=ImageDraw.Draw(dest)
font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
d.text((18,7),'Aqualumen  /  銅格子を通して壁を照らす',font=ImageFont.truetype(font,30),fill='white')
stats={}
for i,(stage,title) in enumerate(labels):
 im=Image.open(run/(stage+'-ingame.png')).convert('RGB')
 x,y=10+(i%2)*600,62+368*(i//2)
 d.text((x,y),title,font=ImageFont.truetype(font,24),fill='white')
 dest.paste(im.resize((580,326),Image.Resampling.LANCZOS),(x,y+37))
 cx=im.width//2;cy=im.height//2
 stats[stage]=ImageStat.Stat(im.crop((cx-220,cy-140,cx+220,cy+140))).mean
dest.save(here/'Copper-in-game.jpg',quality=96)
print(json.dumps(stats,indent=2))
