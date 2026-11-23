from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import numpy as np
from PIL import Image
p=Path(__file__).resolve().parent
screen=np.array(Image.open(p/'faceted-26/left-ingame.png').convert('RGB'),dtype=float)
with ZipFile(p.parent/'gold-art/Aqualumen-Gold-Faceted-32x.zip') as z:
 lab=np.array(Image.open(BytesIO(z.read('assets/minecraft/textures/block/gold_ore_s.png'))))
mask=lab[:,:,1]==231
vein=[(404,153),(405,153),(405,152),(406,152),(407,152),(407,151),(408,151)]
Y,X=np.mgrid[0:720:3,0:1280:3]
color=(screen[::3,::3,0]-screen[::3,::3,1]*1.50)/np.maximum(1,screen[::3,::3].mean(axis=2))
def projection(Y,X,scale,y0,sign):
 wx=406.5+(X+.5-640)/scale; wy=y0-(Y+.5-360)/scale
 bx=np.floor(wx);by=np.floor(wy)
 valid=np.zeros(X.shape,dtype=bool)
 for x,y in vein: valid|=(bx==x)&(by==y)
 tx=np.floor(32*(wx-bx)).astype(int).clip(0,31);ty=np.floor(32*(1-(wy-by))).astype(int).clip(0,31)
 grain=mask[ty,tx if sign else 31-tx]
 return valid,grain
best=(-100,None)
for scale in np.arange(125,140,.2):
 for y0 in np.arange(152.57,152.68,.01):
  for sign in [True,False]:
   valid,m=projection(Y,X,scale,y0,sign); score=color[valid&m].mean()-color[valid&~m].mean()
   if score>best[0]:best=score,(scale,y0,sign)
print(best)
Y,X=np.mgrid[:720,:1280];valid,m=projection(Y,X,*best[1]);np.savez(p/'mask-fit.npz',ore=valid&m,rock=valid&~m,score=best[0],scale=best[1][0],eye=best[1][1],sign=best[1][2])
