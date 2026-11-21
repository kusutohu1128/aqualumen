"""Render-tail intervals for an exact-UUID disposable copy of the two-room house."""
import fcntl
import importlib.util
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

here=Path(__file__).resolve().parent
report=here.parent
root=report.parents[1]
# The earlier runner imports its own "fixture". Insert that directory before loading.
sys.path.insert(0,str(root/'reports/2026-11-21-indirect-light'))
spec=importlib.util.spec_from_file_location('house_capture_for_clock',report/'capture.py');capture=importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)
C,H,D=capture.C,capture.H,capture.D
sys.path.insert(0,str(root/'tools'))
import ground_shadow_lab as g

pack=Path(sys.argv[1]).resolve()
out=here/sys.argv[2]
roles=['off-closed','closed-both','open-both','open-warm']
assert set(roles)<=set(H.ROLE_NAMES) and out.parent==here and not out.exists() and pack.is_file()
lock=open(C.LOCK,'a+b');fcntl.flock(lock,fcntl.LOCK_EX)
out.mkdir()
orig=g.GAME.resolve()
C.NS=D.NS;C.F=H;C.CHECK=80;C.PERIOD=340
D.CHECK=C.CHECK
files=D.datapack(roles,C);D.check_datapack(files,roles);D.simulate(files,roles,C)
parent=Path(tempfile.mkdtemp(prefix='house-clock-',dir=orig.parent))
game=parent/'minecraft';game.mkdir()
(out/'private-game.txt').write_text(str(game))
for n in ['mods','saves','config','shaderpacks']:(game/n).mkdir()
g.lab.shared.world_marker()
src=orig/'saves'/g.lab.WORLD
with (src/'session.lock').open('r+b') as f:
    fcntl.lockf(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    manifest=C.copy_world(src,game/'saves'/g.lab.WORLD)
world=game/'saves'/g.lab.WORLD
assert C.tree(world)==manifest and g.lab.pairs((world/'aqualumen-world.properties').read_bytes())['world_id']==g.lab.WORLD_ID
kit=world/'datapacks/HouseClockFixture';assert not kit.exists()
for n,data in files.items():
    p=kit/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
mods={p:g.lab.sha(orig/'mods'/p) for p in sorted(g.lab.NORMAL_MODS)}
for n in mods:shutil.copy(orig/'mods'/n,game/'mods')
clock=root/'build/aqualumen-door-frameclock-v2-test.jar';shutil.copy(clock,game/'mods')
shutil.copy(pack,game/'shaderpacks')
for n in ['sodium-options.json','iris.properties']:shutil.copy(orig/'config'/n,game/'config')
iris=game/'config/iris.properties'
iris.write_bytes(g.lab.replace_values(iris.read_bytes(),{'shaderPack':pack.name},'='))
(game/'config/house-frameclock.enabled').write_text(g.lab.WORLD_ID)
opts=dict(g.lab.OPTIONS,maxFps='240',enableVsync='false',overrideWidth='2560',overrideHeight='1440',chatVisibility='2',pauseOnLostFocus='false',
          fov=H.fmt((H.FOV-70)/40),fovEffectScale='0.0',bobView='false')
(game/'options.txt').write_bytes(g.lab.replace_values((orig/'options.txt').read_bytes(),opts,':'))
runtime=json.loads((root/'reports/2026-11-20-underwater-refinement/local-launch.json').read_text())
args=[runtime['java'],'-Xms512m','-Xmx2600m','-XX:ActiveProcessorCount=4','-Daqualumen.house.frameclock='+str(game),
      '-Dorg.lwjgl.openal.libname=libopenal.so.1','-cp',':'.join(runtime['cp']),'net.fabricmc.loader.impl.launch.knot.KnotClient',
      '--username',H.PLAYER,'--version','1.21.1','--gameDir',str(game),'--assetsDir',str(orig.parents[2]/'assets'),'--assetIndex','17','--uuid',C.PLAYER_UUID,
      '--accessToken','0','--userType','legacy','--width','2560','--height','1440','--quickPlaySingleplayer',g.lab.WORLD]
env=dict(os.environ,DISPLAY=':1',__GLX_VENDOR_LIBRARY_NAME='nvidia',ALSOFT_DRIVERS='null',XDG_CACHE_HOME=str(parent/'cache'))
log=out/'client.log'; observed={};begin=0
with log.open('xb') as record:
    proc=subprocess.Popen(args,env=env,cwd=game,stdout=record,stderr=record)
    wid=None
    try:
        deadline=time.monotonic()+480
        while len(observed)<len(roles):
            text=log.read_text(errors='replace')
            assert proc.poll() is None and time.monotonic()<deadline, 'startup or capture timeout'
            assert 'AQD_FAIL_' not in text and 'AQD_ABORT_' not in text and 'AQD_DRIFT_' not in text
            assert '[HouseClock] disabled' not in text and 'disabling shaders' not in text.lower()
            if not wid and '[HouseClock] private frame clock ready; framebuffer 2560x1440' in text and C.READY_RE.search(text):
                rows=subprocess.run(['xdotool','search','--all','--onlyvisible','--pid',str(proc.pid),'--name','Minecraft'],capture_output=True,text=True,env=env).stdout.split()
                if rows:
                    wid=rows[-1]; subprocess.run(['xdotool','windowfocus','--sync',wid],env=env,timeout=5,check=True)
                    begin=len(text)
            if wid:
                now=time.monotonic_ns()
                for role in roles:
                    tag='AQD_READY_'+role+'_END'
                    index=text.find(tag,begin)
                    if index<0 or role in observed:continue
                    begin=index+len(tag)
                    focus=subprocess.check_output(['xdotool','getwindowfocus'],env=env,text=True).strip()
                    assert focus==wid
                    time.sleep(1.5)
                    start=time.monotonic_ns()
                    time.sleep(6.1)
                    end=time.monotonic_ns()
                    tail=log.read_text(errors='replace')[begin:]
                    assert 'AQD_BEGIN_' not in tail and 'AQD_DRIFT_' not in tail and 'AQD_FAIL_' not in tail
                    observed[role]=(start,end)
                    print(role,'captured',flush=True)
            time.sleep(.08)
        time.sleep(3.0)
    finally:
        if wid and proc.poll() is None:
            subprocess.run(['/tmp/aqualumen-wm-close',hex(int(wid))],env=env,timeout=5)
        if proc.poll() is None:
            try:proc.wait(timeout=25)
            except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=15)
        (game/'config/house-frameclock.enabled').unlink(missing_ok=True)
raw=game/'client-frames.csv';shutil.copy(raw,out/'client-frames.csv')
frames=list(map(int,raw.read_text().splitlines()))
rows={}
for role,(start,end) in observed.items():
    v=[n for n in frames if start<=n<=end];assert len(v)>15 and (v[-1]-v[0])*1e-9>5.6
    ms=sorted((b-a)*1e-6 for a,b in zip(v,v[1:]))
    rows[role]=dict(meanFPS=1000/statistics.mean(ms),p99Ms=ms[int(.99*len(ms))],maxMs=max(ms),
                    frames=len(ms),seconds=(v[-1]-v[0])/1e9,monotonicNs=[start,end])
txt=log.read_text(errors='replace')
assert f'Using shaderpack: {pack.name}' in txt and 'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti' in txt and 'All dimensions are saved' in txt
assert C.tree(src)==manifest and not g.SENTINEL.exists()
data=dict(renderer='NVIDIA GeForce RTX 3080 Ti',resolution=[2560,1440],renderChunks=12,pack=pack.name,sha256=g.lab.sha(pack),roles=rows,
          realFrameIntervals=True,nativeMinecraftRenderTail=True,extraObserverMod=g.lab.sha(clock),ordinaryMods=mods,
          sourceDigest=C.digest(manifest),sourceUnchanged=True,privateOptInRemoved=True)
(out/'complete.json').write_text(json.dumps(data,indent=2))
print(rows,flush=True)
