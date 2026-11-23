from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import zipfile,json
p=Path(__file__).resolve().parent
sheet=Image.new('RGB',(1200,1004),'#202222')
d=ImageDraw.Draw(sheet)
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',27)
d.text((23,8),'Aqualumen  /  白樺の樹皮　　左：消灯　　右：松明1本',font=font,fill='white')
for row,(v,title) in enumerate(zip('ABC',['細くまばら','中くらいの裂け目','太く密な裂け目'])):
 y=58+314*row
 d.text((23,y),f'{v}　{title}',font=font,fill='white')
 for col in range(2):
  img=Image.open(p/f'birch-{v.lower()}'/f'birch-{col}-ingame.png')
  assert img.size==(2560,1440)
  panel=img.crop((532,245,1152,529)).resize((590,270),Image.Resampling.LANCZOS)
  sheet.paste(panel,(6+col*599,y+40))
sheet.save(p/'Birch-comparison.jpg',quality=96,subsampling=0)
with zipfile.ZipFile(p/'Aqualumen-Birch-Study.zip','w',zipfile.ZIP_DEFLATED) as z:
 for v in 'ABC':
  z.write(p/f'Aqualumen-Birch-{v}.zip',f'Aqualumen-Birch-{v}.zip')
  for n in (0,1):
   src=p/f'birch-{v.lower()}'/f'birch-{n}-ingame.png'
   z.write(src,f'screenshots/{v}-{n}.png')
 z.write(p/'Birch-comparison.jpg','Birch-comparison.jpg')
