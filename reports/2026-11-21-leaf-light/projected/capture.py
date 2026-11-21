"""Place a lit leaf in front of a white wall in a disposable exact-V2 world copy."""
from pathlib import Path
import argparse
import fcntl
import gzip
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

here=Path(__file__).resolve().parent
root=here.parents[2]
sys.path.insert(0,str(root/'tools'))
import ground_shadow_lab as g
sys.path.insert(0,str(root/'reports/2026-11-21-indirect-light'))
import capture as base
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('pack',type=Path)
parser.add_argument('label')
parser.add_argument('--species',action='store_true')
parser.add_argument('--lava-basin',action='store_true',help='Use the enclosed stepped-size lava emitter scene')
args=parser.parse_args()
assert not (args.species and args.lava_basin)
assert re.fullmatch('[a-z0-9-]+',args.label)
pack=args.pack.resolve(strict=True)
if args.lava_basin:
    study=root/'reports/2026-11-21-lava-light'
    sys.path.insert(0,str(study))
    import basin
else:
    study=here
out=study/args.label
lock=open(base.LOCK,'a+b')
fcntl.flock(lock,fcntl.LOCK_EX)
out.mkdir()
orig=g.GAME
source=orig/'saves'/g.lab.WORLD
work=Path(tempfile.mkdtemp(prefix='aql-leaf-cast-'))
game=work/'minecraft'
for folder in ('mods','saves','config','shaderpacks'):
    (game/folder).mkdir(parents=True)
g.lab.shared.world_marker()
clone=game/'saves'/g.lab.WORLD
with (source/'session.lock').open('r+b') as handle:
    fcntl.lockf(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    manifest=base.copy_world(source,clone)
assert base.tree(clone)==manifest
assert g.lab.pairs((clone/'aqualumen-world.properties').read_bytes())['world_id']==g.lab.WORLD_ID
assert base.nbt(gzip.decompress((clone/'level.dat').read_bytes()))['Data']['WorldGenSettings']['seed']==308060
for name in g.lab.NORMAL_MODS:
    shutil.copy2(orig/'mods'/name,game/'mods')
for name in ('iris.properties','sodium-options.json'):
    shutil.copy2(orig/'config'/name,game/'config')
shutil.copy(pack,game/'shaderpacks')
cfg=game/'config/iris.properties'
cfg.write_bytes(g.lab.replace_values(cfg.read_bytes(),{'shaderPack':pack.name},'='))
config=dict(g.lab.OPTIONS,maxFps='120',overrideWidth='1280',overrideHeight='720',chatVisibility='2',fov='0.0',pauseOnLostFocus='false',bobView='false',fovEffectScale='0.0',fullscreen='false')
(game/'options.txt').write_bytes(g.lab.replace_values((orig/'options.txt').read_bytes(),config,':'))

kit=clone/'datapacks/AqualumenCastStudy'
assert not kit.exists()
def write(name,data):
    path=kit/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(data)
def fn(name,*lines):write('data/aqcast/function/'+name+'.mcfunction','\n'.join(lines)+'\n')
write('pack.mcmeta',json.dumps({'pack':{'pack_format':48,'description':'Private through-leaf cast shadow study'}}))
write('data/minecraft/tags/function/tick.json',json.dumps({'values':['aqcast:tick']}))
player='AqualumenCast'
eye=(205.5,174.62,362.5)
aim=(202.5,173.64,366.0)
dx,dy,dz=[b-a for a,b in zip(eye,aim)]
yaw=-math.degrees(math.atan2(dx,dz))
pitch=-math.degrees(math.atan2(dy,math.hypot(dx,dz)))
pose=f'tp {player} {eye[0]} {eye[1]-1.62:.2f} {eye[2]} {yaw:.6f} {pitch:.6f}'
fn('tick',f'execute as @a[name={player},tag=!aqcast] run function aqcast:setup',
   f'execute as @a[name={player},tag=castarmed,tag=!castrun] if items entity @s weapon.offhand minecraft:paper run function aqcast:go')
fn('setup','tag @s add aqcast','gamerule doDaylightCycle false','gamerule doWeatherCycle false','gamerule doMobSpawning false','gamerule randomTickSpeed 0','gamerule doTileDrops false','difficulty peaceful','time set midnight','weather clear','gamemode creative @s','forceload add 198 359 209 367',f'tp {player} 205.5 174 362.5','schedule function aqcast:prepare 20t replace')
fn('prepare','execute if loaded 202 173 364 run function aqcast:build','execute unless loaded 202 173 364 run schedule function aqcast:prepare 20t replace')
fn('build','fill 198 172 359 209 172 367 minecraft:smooth_stone','fill 198 173 366 209 179 366 minecraft:white_concrete',*(basin.room if args.lava_basin else []),pose,f'item replace entity {player} weapon.mainhand with minecraft:paper',f'tag {player} add castarmed','say AQCAST_ARM')
fn('go','tag @s add castrun','item replace entity @s weapon.offhand with minecraft:air','function aqcast:s0')
leaf='minecraft:oak_leaves[persistent=true]'
stages=[('open','minecraft:air','minecraft:torch'),('foliage',leaf,'minecraft:torch'),('stone','minecraft:stone','minecraft:torch'),('dark',leaf,'minecraft:air'),('soul',leaf,'minecraft:soul_torch'),('again',leaf,'minecraft:torch')]
if args.species:
    stages.extend([('oak-white',leaf,'minecraft:sea_lantern'),('cherry-white','minecraft:cherry_leaves[persistent=true]','minecraft:sea_lantern'),
                   ('birch-white','minecraft:birch_leaves[persistent=true]','minecraft:sea_lantern'),('open-white','minecraft:air','minecraft:sea_lantern')])
if args.lava_basin: stages=basin.stages
for i,(name,block,lamp) in enumerate(stages):
    if args.lava_basin:
        assignments,condition=basin.layout(name,block,lamp)
    else:
        assignments=[f'setblock 202 173 364 {block}',f'setblock 202 173 361 {lamp}']
        condition=f'if block 202 173 364 {block} if block 202 173 361 {lamp}'
    lines=[pose,*assignments,f'schedule function aqcast:v{i} 30t replace']
    if i+1<len(stages):lines+=[f'schedule function aqcast:s{i+1} 130t replace']
    fn('s'+str(i),*lines)
    fn('v'+str(i),f'execute {condition} if block 202 173 366 minecraft:white_concrete if entity @a[name={player},x=205.5,y=173,z=362.5,distance=..0.04] run say AQCAST_{name}_READY')
runtime=json.loads((root/'reports/2026-11-20-underwater-refinement/local-launch.json').read_text())
java=[runtime['java'],'-Xms512m','-Xmx2600m','-XX:ActiveProcessorCount=4','-Dorg.lwjgl.openal.libname=libopenal.so.1','-cp',':'.join(runtime['cp']),'net.fabricmc.loader.impl.launch.knot.KnotClient','--username',player,'--version','1.21.1','--gameDir',str(game),'--assetsDir',str(orig.parents[2]/'assets'),'--assetIndex','17','--uuid','00000000000040008000000000000471','--accessToken','0','--userType','legacy','--width','1280','--height','720','--quickPlaySingleplayer',g.lab.WORLD]
env=dict(os.environ,DISPLAY=':1',__GLX_VENDOR_LIBRARY_NAME='nvidia',ALSOFT_DRIVERS='null',__GL_SHADER_DISK_CACHE_PATH=str(Path.home()/'.cache/aqualumen-lab-shader-driver'))
log=out/'client.log'
(out/'private-game.txt').write_text(str(game))
geometry=dict(eye=eye,target=aim,yaw=yaw,pitch=pitch,wallZ=366,cameraFov=70,stages=stages)
if args.lava_basin:
    geometry.update(sourceCell=[202,172,361],poolCorners=[[201,172,360],[203,172,362]],pillar=[[202,173,364],[202,175,364]],room=basin.room)
else:
    geometry.update(source=[202.5,173.64,361.5],leaf=[202,173,364])
(out/'geometry.json').write_text(json.dumps(geometry,indent=2))
with log.open('xb') as sink:
    proc=subprocess.Popen(java,cwd=game,env=env,stdout=sink,stderr=sink)
    wid=None
    try:
        armed=False
        done={}
        until=time.monotonic()+600
        while len(done)<len(stages):
            txt=log.read_text(errors='replace')
            assert proc.poll() is None and time.monotonic()<until,done
            assert '/ERROR]' not in txt and 'reverting to default' not in txt.lower()
            if not wid:
                wins=subprocess.run(['xdotool','search','--all','--onlyvisible','--pid',str(proc.pid),'--name','Minecraft'],env=env,capture_output=True,text=True).stdout.split()
                if len(wins)==1:wid=wins[0]
            if wid and not armed and 'AQCAST_ARM' in txt and re.search(r'Creating pipeline for dimension minecraft:overworld.*?Started [1-9]\d* worker threads',txt,re.S):
                subprocess.run(['xdotool','windowfocus','--sync',wid],env=env,check=True,timeout=4)
                assert subprocess.check_output(['xdotool','getwindowfocus'],env=env,text=True).strip()==wid
                time.sleep(2)
                subprocess.run(['xdotool','key','F1','f'],env=env,check=True)
                armed=True
                until=time.monotonic()+85
            for name,_,_ in stages:
                if armed and name not in done and f'[Server] AQCAST_{name}_READY' in txt:
                    time.sleep(2.0)
                    path=out/(name+'.png')
                    subprocess.run(['ffmpeg','-v','error','-n','-f','x11grab','-window_id',wid,'-i',':1','-frames:v','1',str(path)],check=True,timeout=6)
                    assert base.png_size(path)==(1280,720)
                    done[name]=g.lab.sha(path)
            time.sleep(.12)
    finally:
        if wid and proc.poll() is None:subprocess.run(['/tmp/aqualumen-wm-close',hex(int(wid))],env=env,timeout=6)
        try:proc.wait(timeout=25)
        except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=20)
txt=log.read_text(errors='replace')
assert 'All dimensions are saved' in txt and 'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti' in txt and 'Using shaderpack: '+pack.name in txt and base.tree(source)==manifest
(out/'complete.json').write_text(json.dumps(dict(pack=pack.name,sha256=g.lab.sha(pack),renderer='NVIDIA GeForce RTX 3080 Ti',screenshots=done,sourceDigest=base.digest(manifest)),indent=2))
