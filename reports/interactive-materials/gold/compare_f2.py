"""Measure local, tone-mapped material differences in registered F2 pairs."""
from pathlib import Path
from PIL import Image
from statistics import median
import json
from math import floor
import sys
root=Path(__file__).resolve().parent.parent/'gold-scene'
f,c=map(Path,sys.argv[1:3])
cells=[(308,181),(441,181),(441,314),(574,314),(707,314),(707,447),(840,447)]
res={}
def pct(values,t):
 s=sorted(values)
 return s[round((len(s)-1)*t)]
for stage in ['left','right']:
 A,B=[Image.open(fold/(stage+'-ingame.png')).convert('RGB') for fold in [f,c]]
 metal=[];stone=[]
 for x0,y0 in cells:
  for y in range(y0+6,y0+127,2):
   for x in range(x0+6,x0+127,2):
    col=B.getpixel((x,y)); deltaR=A.getpixel((x,y))[0]-col[0]
    # Use only pure gold and pure rock texels from the control's display image.
    ratio=col[0]/max(1,col[2])
    if ratio<3.05:stone.append(deltaR)
    if ratio>3.85:metal.append((deltaR,(x,y)))
 if not metal:continue
 m=[a for a,p in metal]
 res[stage]={'goldSamples':len(m),'goldRed_delta_p05_p50_p95':[pct(m,t) for t in [.05,.5,.95]],'goldBrighterOver10':sum(v>10 for v in m)/len(m),'goldDarkerOver10':sum(v< -10 for v in m)/len(m),'stoneRed_delta_p05_p50_p95':[pct(stone,t) for t in [.05,.5,.95]],'brightestPixel':max(metal),'dimmestPixel':min(metal)}
print(json.dumps(res,indent=2))
