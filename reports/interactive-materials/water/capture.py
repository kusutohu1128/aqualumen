"""Private Lab clone. Three guarded states; controls share exposure/time and camera."""
from pathlib import Path
import sys,re,threading,time,subprocess,fcntl,signal,importlib.machinery
here=Path(__file__).resolve().parent
repo=here.parents[2]
sys.path.insert(0,str(repo/'reports/2026-11-22-gpu-profile'))
import run as guard
BASE='data/animal/function/'
STAGES=('open','closed','dry')
POSE='405.30 150.05 -401.25 180 -25'
APERTURE='406 154 -408 407 154 -404'
POOL='401 150 -409 411 150 -402'
class Scene:
 def __init__(self,rooms):
  self.rooms=rooms;self.STAGE_TABLE=dict.fromkeys(STAGES)
 def __getattr__(self,k):return getattr(self.rooms,k)
 def self_test(self,names): assert tuple(names)==STAGES
 def geometry(self,names):
  return dict(camera=POSE,aperture=APERTURE,pool=POOL,time=3300,receiver='underside of stone roof y=154',stages=names)
 def datapack(self,names):
  f=self.rooms.datapack(['day-white'])
  def put(key,lines):f[BASE+key+'.mcfunction']='\n'.join(lines)+'\n'
  build=f[BASE+'build.mcfunction'].splitlines()
  build[:1]=['fill 399 149 -411 413 154 -399 stone hollow',
      'fill 400 150 -410 412 150 -400 stone','fill 401 150 -409 411 150 -402 water',
      'setblock 402 153 -410 andesite','setblock 408 152 -410 andesite']
  put('build',build)
  for i,name in enumerate(names):
   roof='stone' if name=='closed' else 'air'
   pool='stone' if name=='dry' else 'water'
   put('s'+str(i),['weather clear 1000000','time set 3300',f'gamemode spectator {self.PLAYER}',f'tp {self.PLAYER} {POSE}',
     f'fill {APERTURE} {roof}',f'fill {POOL} {pool}',f'say AQLAVA_BEGIN_{name}_END',
     f'schedule function animal:v{i} 110t replace',f'schedule function animal:e{i} 322t replace',
     f'schedule function animal:s{(i+1)%len(names)} 350t replace'])
   if name=='open':
    # A real non-spectator entity moves through source water while the spectator camera stays fixed.
    # Delay contact until after the initial F2; bridge force samples are retained for the video.
    lines=f[BASE+'s'+str(i)+'.mcfunction'].splitlines()
    lines+=['summon pig 403.4 150.15 -405.60 {Tags:["aq_water_trial"],NoAI:1b,NoGravity:1b,Silent:1b}',
        'schedule function animal:contact0 134t replace','schedule function animal:clearcontact 201t replace']
    put('s'+str(i),lines)
    for step in range(57):
     at=403.4+step*.079
     cmds=[f'tp @e[tag=aq_water_trial,limit=1] {at:.3f} 150.15 -405.60']
     if step<56: cmds+=[f'schedule function animal:contact{step+1} 1t replace']
     put('contact'+str(step),cmds)
    put('clearcontact',['kill @e[tag=aq_water_trial]'])
   checks=f'if block 403 154 -406 stone if block 409 154 -406 stone if block 407 154 -406 {roof} if block 405 150 -406 {pool} if block 405 149 -406 stone positioned 405.30 150.05 -401.25 if entity @a[name={self.PLAYER},gamemode=spectator,distance=..0.02,x_rotation=-25.05..-24.95]'
   for fn,ok,bad in [('v','READY','FAIL'),('e','STILL','DRIFT')]:
    put(fn+str(i),['scoreboard players set #ok aq_room 0',f'execute {checks} run scoreboard players set #ok aq_room 1',f'execute if score #ok aq_room matches 1 run say AQLAVA_{ok}_{name}_END',f'execute unless score #ok aq_room matches 1 run say AQLAVA_{bad}_{name}_END'])
  return f

def record(game,out):
 deadline=time.monotonic()+330
 log=out/'client.log'
 while time.monotonic()<deadline:
  if log.exists() and '[Server] AQLAVA_READY_open_END' in log.read_text(errors='replace'):
   disp=re.search(r'display=(:[0-9]+) game='+re.escape(str(game)),(here/'progress.txt').read_text()).group(1)
   r=subprocess.Popen(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-f','x11grab','-draw_mouse','0','-video_size','1280x720','-framerate','20','-i',disp,'-t','5','-an','-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p',str(out/'water-open.mp4')],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
   source=game/'config/aqualumen-physics-status.json'
   with (out/'wake-telemetry.jsonl').open('w') as trace:
    prev=''
    while r.poll() is None:
     if source.exists():
      raw=source.read_text()
      if raw!=prev and raw.strip():
       trace.write(raw.strip()+'\n');trace.flush();prev=raw
     time.sleep(.14)
   (out/'record-log.txt').write_bytes(r.stderr.read());return
  time.sleep(.25)
if __name__=='__main__':
 if sys.argv[1]=='debug' and not any(here.glob('water-baseline-*/complete.json')):
  raise SystemExit('Diagnostic deferred until a matched normal baseline is reviewed.')
 pack={'combined':here.parent/'integration/Aqualumen-Interactive-Materials.zip','candidate':here.parent/'water-shader/Aqualumen-1.9.0-water-ceiling.zip','debug':here.parent/'water-shader/Aqualumen-Water-Ceiling-Debug.zip','baseline':repo/'dist/Aqualumen-1.9.0-preview.10.zip'}[sys.argv[1]]
 fixed=dict(backend='vgl',size='1280x720',settle='1',stages=','.join(STAGES),glcache=str(guard.BUILD/'driver-cache'))
 fixed.update({'period-ticks':'350','compiler-mod':str(repo/'dist/aqualumen-lighting-compiler-0.3.0.jar')})
 def prepare(game,out,mods):threading.Thread(target=record,args=(game,out),daemon=True).start()
 # Scope the shared-lock change to this isolated launcher. Queue at the kernel
 # instead of polling LOCK_NB, which can starve behind several blocking waiters.
 loader=importlib.machinery.SourceFileLoader
 original=loader.exec_module
 lease_path=Path('/tmp/aql-render21-1000.lock')
 lease=lease_path.open('a+b')
 def expired(*args):raise TimeoutError('render lock still held after 1200s')
 old=signal.signal(signal.SIGALRM,expired);signal.alarm(1200)
 print('Joining shared render queue before GPU preflight',flush=True)
 try:
  fcntl.flock(lease,fcntl.LOCK_EX)
 finally:
  signal.alarm(0);signal.signal(signal.SIGALRM,old)
 print('Shared render lock acquired',flush=True)
 def exec_queued(loader_self,module):
  original(loader_self,module)
  if not loader_self.path.endswith('/runtime-v190/run.py'):return
  def acquire(seconds):
   assert Path(module.base.LOCK).samefile(lease_path) and not lease.closed
   return lease
  module.acquire_lock=acquire
 loader.exec_module=exec_queued
 guard.launch(pack,sys.argv[2],'off',fixed,here,Scene,prepare)
