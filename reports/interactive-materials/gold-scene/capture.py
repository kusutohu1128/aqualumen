"""Capture the same ore and torch in an isolated singleplayer room."""
from pathlib import Path
import sys, json, math, shutil, re, subprocess, threading, time
here=Path(__file__).resolve().parent
repo=here.parents[2]
sys.path.insert(0,str(repo/'reports/2026-11-22-gpu-profile'))
import run as guard
BASE='data/animal/function/'
POSE='406.5 151 -407.60 180 0'
LAMP={'left':'404 152 -409','right':'408 152 -409'}
STAGES=['left','right','strafe']
class Scene:
 def __init__(self,rooms):
  self.rooms=rooms; self.STAGE_TABLE=dict.fromkeys(STAGES)
 def __getattr__(self,k): return getattr(self.rooms,k)
 def self_test(self,names): assert names==STAGES
 def geometry(self,names): return dict(camera=POSE,wall='z=-412',source=LAMP,stages=STAGES)
 def datapack(self,names):
  f=self.rooms.datapack(['day-white'])
  def put(k,lines): f[BASE+k+'.mcfunction']='\n'.join(lines)+'\n'
  build=f[BASE+'build.mcfunction'].splitlines()
  vein=[(404,153),(405,153),(405,152),(406,152),(407,152),(407,151),(408,151)]
  build[0:1]=['fill 403 150 -413 410 155 -405 stone hollow','fill 404 151 -412 409 154 -412 andesite','fill 404 151 -412 408 153 -412 stone']+[f'setblock {x} {y} -412 gold_ore' for x,y in vein]+[f'setblock {x} 151 -409 cobblestone' for x in (404,408)]
  put('build',build)
  for i,name in enumerate(names):
   source='left' if name=='left' else 'right'
   commands=['time set 18000',f'gamemode spectator {self.PLAYER}',f'tp {self.PLAYER} {POSE}']
   commands += [f'setblock {pos} '+('torch' if side==source else 'air') for side,pos in LAMP.items()]
   commands += [f'say AQLAVA_BEGIN_{name}_END']
   if name=='strafe':
    # Ease a lateral walk while the camera tracks the central ore. Light remains fixed.
    for j in range(97):
     x=406.5-1.32*math.sin(2*math.pi*j/96)
     yaw=180+math.degrees(math.atan((406.5-x)/3.40))
     put(f'move{j}',[f'tp {self.PLAYER} {x:.5f} 151 -407.60 {yaw:.4f} 0'])
     commands.append(f'schedule function animal:move{j} {j+24}t replace')
   ready=142 if name=='strafe' else 55
   commands.extend([f'schedule function animal:v{i} {ready}t replace',f'schedule function animal:e{i} 240t replace',f'schedule function animal:s{(i+1)%3} 264t replace'])
   put('s'+str(i),commands)
   checks=' '.join([f'if block {pos} '+('torch' if side==source else 'air') for side,pos in LAMP.items()]+['if block 406 152 -412 gold_ore',f'positioned 406.5 151 -407.60 if entity @a[name={self.PLAYER},gamemode=spectator,distance=..0.02,x_rotation=-0.02..0.02]'])
   for fn,ok,bad in [('v','READY','FAIL'),('e','STILL','DRIFT')]:
    put(fn+str(i),['scoreboard players set #ok aq_room 0',f'execute {checks} run scoreboard players set #ok aq_room 1',f'execute if score #ok aq_room matches 1 run say AQLAVA_{ok}_{name}_END',f'execute unless score #ok aq_room matches 1 run say AQLAVA_{bad}_{name}_END'])
  return f
def record(game,out):
 log=out/'client.log'
 for _ in range(2100):
  if log.exists() and '[Server] AQLAVA_BEGIN_strafe_END' in log.read_text(errors='replace'):
   note=(here/'progress.txt').read_text()
   disp=re.search(r'display=(:[0-9]+) game='+re.escape(str(game)),note).group(1)
   result=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','x11grab','-draw_mouse','0','-video_size','1280x720','-framerate','24','-i',disp,'-t','7','-an','-c:v','libx264','-preset','ultrafast','-threads','2','-crf','16','-pix_fmt','yuv420p',str(out/'strafe.mp4')],capture_output=True,text=True)
   (out/'record.txt').write_text(f'ffmpeg={result.returncode}\n'+result.stderr)
   return
  time.sleep(.18)
def main():
 variant=sys.argv[1]
 assert variant in ('Faceted','Control')
 label=sys.argv[2]
 pack=here.parent/'gold'/'Aqualumen-1.9.0-gold-facets.zip'
 rp=here.parent/'gold-art'/f'Aqualumen-Gold-{variant}-32x.zip'
 def prepare(game,out,mods):
  target=game/'resourcepacks'/rp.name
  target.parent.mkdir(exist_ok=True);shutil.copy2(rp,target)
  opt=game/'options.txt';data,n=re.subn(r'(?m)^resourcePacks:.*$',lambda _:'resourcePacks:'+json.dumps(['vanilla','file/'+rp.name],separators=(',',':')),opt.read_text())
  assert n==1;opt.write_text(data)
  mods['resourcePackSha256']=guard.sha(target)
  threading.Thread(target=record,args=(game,out),daemon=True).start()
 fixed=dict(backend='vgl',size='1280x720',settle='1',stages=','.join(STAGES),glcache=str(guard.BUILD/'driver-cache'))
 fixed.update({'period-ticks':'264','compiler-mod':str(repo/'dist/aqualumen-lighting-compiler-0.3.0.jar')})
 guard.launch(pack,label,'off',fixed,here,Scene,prepare)
if __name__=='__main__':main()
