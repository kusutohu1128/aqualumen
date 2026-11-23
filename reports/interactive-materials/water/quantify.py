from pathlib import Path
import json
import numpy as np
from PIL import Image
from review import getrun
p=Path(__file__).resolve().parent
regions={'leftCeiling':[100,125,550,260],'midCeiling':[300,200,600,360],'rightCeiling':[1050,230,1200,335],'backWall':[150,450,350,540]}
probe={}
normal={}
for mode in ('combined/candidate','baseline','debug'):
 run=getrun(mode)
 if run is None: continue
 stats={}
 for stage in ('open','closed','dry'):
  rgb=np.asarray(Image.open(run/(stage+'-ingame.png')).convert('RGB'),dtype=float)
  stats[stage]={}
  for label,(x,y,X,Y) in regions.items():
   area=rgb[y:Y,x:X]
   stats[stage][label]=list(area.mean(axis=(0,1)).round(3))
   normal[(mode,stage,label)]=area
 probe[mode]=stats
if 'baseline' in probe:
 delta={}
 for label in regions:
  arr=lambda m,s:normal[(m,s,label)]
  interaction=(arr('combined/candidate','open')-arr('combined/candidate','dry'))-(arr('baseline','open')-arr('baseline','dry'))
  delta[label]={'meanOpenMinusDryChangeRelativeToBaseline':list(interaction.mean(axis=(0,1)).round(3)),'p90Delta':list(np.percentile(interaction,90,axis=(0,1)).round(2))}
 probe['paired']=delta
 for label in regions:
  def delta_comparison(stage):
   return np.mean(normal[('combined/candidate',stage,label)]-normal[('baseline',stage,label)],axis=(0,1)).round(3).tolist()
  delta[label]['normalMinusOld']={stage:delta_comparison(stage) for stage in ('open','closed','dry')}

probe['boxes']=regions
(p/'ingame-quantification.json').write_text(json.dumps(probe,indent=2)+'\n')
