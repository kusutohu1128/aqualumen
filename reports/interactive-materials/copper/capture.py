"""Four-state test: north receiver wall viewed from within a sealed room."""
import sys
from pathlib import Path
here=Path(__file__).resolve().parent
repo=here.parents[2]
sys.path.insert(0,str(repo/'reports/2026-11-22-gpu-profile'))
import run as guard
BASE='data/animal/function/'
STAGES=('open','grate','redglass','duo','blocked')
GATE='406 152 -407'
FILTER='406 152 -405'
LAMP='406 152 -404'
SOUL='407 152 -404'
POSE='406.5 151 -407.8 180 0'

class Scene:
 def __init__(self,rooms):
  self.rooms=rooms;self.STAGE_TABLE=dict.fromkeys(STAGES)
 def __getattr__(self,k):return getattr(self.rooms,k)
 def self_test(self,names):assert tuple(names)==STAGES
 def geometry(self,names):return dict(camera=POSE,gate=GATE,filter=FILTER,lantern=LAMP,stages=names)
 def datapack(self,names):
  f=self.rooms.datapack(['day-white'])
  def put(key,lines): f[BASE+key+'.mcfunction']='\n'.join(lines)+'\n'
  build=f[BASE+'build.mcfunction'].splitlines()
  build[:1]=['fill 400 149 -413 412 156 -401 stone hollow','fill 401 150 -410 411 155 -410 white_concrete','fill 401 150 -407 411 155 -407 black_concrete','fill 406 151 -404 407 151 -404 stone',f'setblock {LAMP} lantern']
  put('build',build)
  for i,name in enumerate(names):
   material={'open':'air','grate':'copper_grate','redglass':'copper_grate','duo':'copper_grate','blocked':'black_concrete'}[name]
   glass='red_stained_glass' if name=='redglass' else 'air'
   soul='soul_lantern' if name=='duo' else 'air'
   put('s'+str(i),['time set 18000',f'gamemode spectator {self.PLAYER}',f'tp {self.PLAYER} {POSE}',f'setblock {GATE} {material}',f'setblock {FILTER} {glass}',f'setblock {SOUL} {soul}',f'say AQLAVA_BEGIN_{name}_END',f'schedule function animal:v{i} 86t replace',f'schedule function animal:e{i} 320t replace',f'schedule function animal:s{(i+1)%len(names)} 348t replace'])
   checks=f'if block {GATE} {material} if block {FILTER} {glass} if block {LAMP} lantern if block {SOUL} {soul} if block 406 152 -410 white_concrete positioned 406.5 151 -407.8 if entity @a[name={self.PLAYER},gamemode=spectator,distance=..0.02,x_rotation=-0.02..0.02]'
   for fn,ok,bad in [('v','READY','FAIL'),('e','STILL','DRIFT')]:
    put(fn+str(i),['scoreboard players set #ok aq_room 0',f'execute {checks} run scoreboard players set #ok aq_room 1',f'execute if score #ok aq_room matches 1 run say AQLAVA_{ok}_{name}_END',f'execute unless score #ok aq_room matches 1 run say AQLAVA_{bad}_{name}_END'])
  return f

if __name__=='__main__':
 fixed=dict(backend='vgl',size='1280x720',settle='1',stages=','.join(STAGES),glcache=str(guard.BUILD/'driver-cache'))
 fixed.update({'period-ticks':'348','compiler-mod':str(repo/'dist/aqualumen-lighting-compiler-0.3.0.jar')})
 pack=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else here.parent/'integration/Aqualumen-Interactive-Materials.zip'
 guard.launch(pack,sys.argv[1],'off',fixed,here,Scene)
