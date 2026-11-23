from pathlib import Path
from PIL import Image,ImageFont,ImageDraw
import numpy as np
p=Path(__file__).resolve().parent
files=[next(p.glob(f'water-{name}-*/open-ingame.png')) for name in ('baseline','combined')]
frames=[np.array(Image.open(f).convert('RGB')).astype(float) for f in files]
diff=frames[1]-frames[0]
# Registered full frames; on the lower half the pig's position and water may differ
# slightly across independent launches, so inspect only the actual ceiling.
box=(0,0,1280,370)
panel=Image.new('RGB',(1024,723),'#14191a');d=ImageDraw.Draw(panel)
ft='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
title=ImageFont.truetype(ft,28);sub=ImageFont.truetype(ft,18)
def paste(a,pos,sz):
 panel.paste(Image.fromarray(a.astype('uint8')).resize(sz,Image.Resampling.LANCZOS),pos)
d.text((18,5),'天窓の光が水面を経由して天井へ返る',font=title,fill='#e3e7e0')
for i,(im,t) in enumerate(zip(frames,['従来版  preview.10','水面反射の試作を適用'])):
 d.text((12+512*i,54),t,font=sub,fill='#d6d9d4');paste(im,(i*512,88),(511,288))
d.text((14,387),'明るさの差を6倍に強調　　天井だけを同じ位置で比較',font=sub,fill='#e9dcc4')
# Only brighten positive luminance, clamped to display white; keep image non-normalized.
crop=diff[box[1]:box[3],box[0]:box[2]]
paste(np.uint8(np.clip(crop*6,0,255)),(0,420),(1024,296))
panel.save(p/'water-real-effect.jpg',quality=96,subsampling=0)
print('Open, candidate minus baseline percent positive in ceiling',round((crop[:,:,0]>0).mean(),3))
