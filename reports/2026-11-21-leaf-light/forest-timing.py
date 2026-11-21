import sys,os,fcntl,threading,hashlib,shutil,subprocess,tempfile,time,json,re
from pathlib import Path
root=Path('/home/kusutohu/repos/aqualumen')
render_lock=open('/tmp/aql-render21-'+str(os.getuid())+'.lock','a+b');fcntl.flock(render_lock,fcntl.LOCK_EX)
sys.path.insert(0,str(root/'tools'));import ground_shadow_lab as g
r=root/'reports/2026-11-21-leaf-light'
scale=int(os.environ.get('AQUALUMEN_RIM_SCALE','1')); w=int(os.environ.get('AQUALUMEN_RIM_WIDTH',960*scale));h=int(os.environ.get('AQUALUMEN_RIM_HEIGHT',540*scale))
args=sys.argv[1:]; pack=Path(args[0]).resolve(); out=r/args[1]; scenes=args[2:]
forest=os.environ.get("AQUALUMEN_TEST_JAR")=="aqualumen-benchmark-forest-light.jar"
if forest and out.name in {"forest","forest-final"}:
 scenes.extend(["air-shadow-backlit","air-sunlit-front","air-backlit-open"])
assert out.is_relative_to(r) and not out.exists() and pack.is_file()
out.mkdir()
orig=g.GAME
snapshot=root/'reports/2026-11-20-underwater-refinement/local-launch.json'
if not snapshot.exists():
 proc=Path('/proc',str(g.lab.lab_java_processes(orig)[0]));aa=(proc/'cmdline').read_bytes().decode().split('\0')
 cp=[x for x in aa[aa.index('-cp')+1].split(':') if Path(x).is_file()]
 assert all(str(orig.parents[2]/'libraries') in x for x in cp)
 snapshot.write_text(json.dumps(dict(java=str((proc/'exe').resolve()),cp=cp),indent=2))
runtime=json.loads(snapshot.read_text())
assets=orig.parents[2]/'assets'
labroot=Path(tempfile.mkdtemp(prefix='carried-matrix-',dir=orig.parent))
game=labroot/'Aqualumen Lab/minecraft';game.mkdir(parents=True)
(out/'sandbox-location.txt').write_text(str(game))
for n in ['shaderpacks','mods','config','saves']: (game/n).mkdir()
src=orig/'saves'/g.lab.WORLD
g.lab.shared.world_marker()
with (src/'session.lock').open('r+b') as lock:
 fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 shutil.copytree(src,game/'saves'/g.lab.WORLD,ignore=shutil.ignore_patterns('session.lock'))
assert g.lab.pairs((game/'saves'/g.lab.WORLD/'aqualumen-world.properties').read_bytes())['world_id']==g.lab.WORLD_ID
for n in g.lab.NORMAL_MODS:shutil.copy(orig/'mods'/n,game/'mods')
testjar=os.environ.get('AQUALUMEN_TEST_JAR','aqualumen-benchmark-hand-light.jar')
if testjar=='aqualumen-benchmark-local-light-extended.jar' and (root/'build/aqualumen-benchmark-local-light-matrix.jar').is_file(): testjar='aqualumen-benchmark-local-light-matrix.jar'
shutil.copy(root/'build'/testjar,game/'mods');shutil.copy(pack,game/'shaderpacks')
# Keep only the explicit Lab TEST instrumentation in the disposable directory.
for n in ['sodium-options.json','iris.properties']:
 if (orig/'config'/n).exists():shutil.copy(orig/'config'/n,game/'config')
(game/'config/iris.properties').write_bytes(g.lab.replace_values((game/'config/iris.properties').read_bytes(),{'shaderPack':pack.name},'='))
(game/'options.txt').write_bytes(g.lab.replace_values((orig/'options.txt').read_bytes(),dict(g.lab.OPTIONS,maxFps=os.environ.get('AQUALUMEN_FPS','45'),overrideWidth=str(w),overrideHeight=str(h),pauseOnLostFocus='false'),':'))
(game/'config/aqualumen-benchmark.enabled').write_text('Private duplicate of the exact V2 TEST world')
(game/'config/aqualumen-benchmark.properties').write_bytes(g.lab.properties(dict(schema=2, world=g.lab.WORLD,world_id=g.lab.WORLD_ID,expected_pack=pack.name,expected_pack_sha256=g.lab.sha(pack),width=w,height=h,render_chunks=12,simulation_chunks=6,capture_motion=os.environ.get('AQUALUMEN_LAMP_MOTION','false'),ground_frame_strip='false',water_frame_clip=os.environ.get('AQUALUMEN_RIM_FILM','false'))))
control=game/'aqualumen-benchmark'
run='carried-'+out.name
java=[runtime['java'],'-Xms512m','-Xmx2600m','-XX:ActiveProcessorCount=4','-Dorg.lwjgl.openal.libname=libopenal.so.1','-cp',':'.join(runtime['cp']),'net.fabricmc.loader.impl.launch.knot.KnotClient','--username','AqualumenOptics','--version','1.21.1','--gameDir',str(game),'--assetsDir',str(assets),'--assetIndex','17','--uuid','00000000000040008000000000000411','--accessToken','0','--userType','legacy','--width',str(w),'--height',str(h),'--quickPlaySingleplayer',g.lab.WORLD]
env=dict(os.environ,ALSOFT_DRIVERS='null',GALLIUM_DRIVER='zink',LIBGL_KOPPER_DRI2='1',__GLX_VENDOR_LIBRARY_NAME='mesa',VK_DRIVER_FILES='/usr/share/vulkan/icd.d/nvidia_icd.json',XDG_CACHE_HOME=str(labroot/'cache'))
for key in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS'):env.pop(key,None)
if os.environ.get('AQUALUMEN_NATIVE')=='1':
 assert os.environ.get('DISPLAY')==':1'
 for k in ('GALLIUM_DRIVER','LIBGL_KOPPER_DRI2','VK_DRIVER_FILES'):env.pop(k,None)
 env['__GLX_VENDOR_LIBRARY_NAME']='nvidia'
logfile=out/'client.log'
with logfile.open('xb') as log:
 p=subprocess.Popen(java,stdout=log,stderr=log,env=env,cwd=game)
 try:
  end=time.monotonic()+660; asked=False;focused=False
  while p.poll() is None:
   tx=logfile.read_text(errors='replace')
   if not focused and 'OpenGL' in tx:
    wins=subprocess.run(['xdotool','search','--all','--onlyvisible','--pid',str(p.pid),'--name','Minecraft'],capture_output=True,text=True).stdout.split()
    if wins:
     subprocess.run(['xdotool','windowfocus',wins[-1]],capture_output=True);focused=True
   if not asked and 'logged in with entity id' in tx and (control/'status.json').exists() and re.search(r'Creating pipeline for dimension minecraft:overworld.*?Started [1-9]\d* worker threads',tx,re.S):
    time.sleep(2)
    cmd=[sys.executable,str(root/'tools/benchmark-control.py'),'--game',str(game),'start','--run-id',run,'--scenes',*scenes,'--warmup',('15' if forest or any(x.startswith('lamp-') for x in scenes) else '5'),'--sample',os.environ.get('AQUALUMEN_SAMPLE_SECONDS','5'),'--auto-quit']
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL);asked=True;end=time.monotonic()+max(120,65+38*len(scenes))
   if asked and 'Benchmark aborted:' in tx:raise RuntimeError('guarded private benchmark aborted')
   if time.monotonic()>end:raise TimeoutError('private client timeout')
   time.sleep(.75)
  assert p.returncode==0,p.returncode
  src=control/'runs'/run
  d=json.loads((src/'run.json').read_text())
  assert d['world_id']==g.lab.WORLD_ID and d['pack_sha256']==g.lab.sha(pack) and d['shader_active'] and not d['shader_fallback'] and 'NVIDIA' in d['gl_renderer']
  assert json.loads((src/'complete.json').read_text())['status']=='complete'
  assert 'disabling shaders' not in tx.lower() and '[Render thread/ERROR]' not in tx
  for n in scenes:
   row=json.loads((src/(n+'.json')).read_text());assert row['frames'] and row['camera_follows_local_player'] and row['framebuffer_resolution']==[w,h]
  shutil.copytree(src,out/'capture')
  print(d['gl_renderer'],d['pack_name'],scenes)
 finally:
  if p.poll() is None:
   p.terminate()
   try:p.wait(timeout=12)
   except subprocess.TimeoutExpired:p.kill();p.wait()
  for f in ('config/aqualumen-benchmark.enabled','aqualumen-benchmark/request.properties'):
   (game/f).unlink(missing_ok=True)
