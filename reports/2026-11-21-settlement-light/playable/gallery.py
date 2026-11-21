"""Use unretouched player-camera photos from the two saved visits to the generated house."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
here=Path(__file__).resolve().parent
original=here/'ordinary-house'; entry=here/'enter-by-porch'
assert json.loads((entry/'complete.json').read_text())['cleanExit']
panels=[(original/'snowy-village.png','降雪中の集落'),(original/'door-closed.png','トウヒの扉を閉めた状態'),(original/'door-open.png','素手で開けたあと'),
        (original/'soul-at-door.png','魂の松明を持って戸口に立つ'),(entry/'naturally-lit-interior.png','室内から窓を見る'),(entry/'interior-soul-torch.png','同じ位置で魂の松明を持つ')]
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',20)
sheet=Image.new('RGB',(1440,620),'#202321');pen=ImageDraw.Draw(sheet)
for i,(p,title) in enumerate(panels):
 im=Image.open(p).convert('RGB').resize((480,270),Image.Resampling.LANCZOS)
 x=i%3*480;y=i//3*310;sheet.paste(im,(x,y));pen.text((x+8,y+277),title,font=font,fill='#eeeee8')
sheet.save(here/'village-house.jpg',quality=94,subsampling=0)
