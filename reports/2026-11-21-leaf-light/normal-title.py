import os,sys,json,time,subprocess,tempfile
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tools'))
import ground_shadow_lab as g
r=Path('reports/2026-11-21-leaf-light')
base=json.loads((r/'normal-before.json').read_text())
selected=json.loads((r/'normal-selection.json').read_text())
s=json.loads((r/'normal-smoke.json').read_text())
assert s['optionsExact'] and s['benchmarkDisabled']
import fcntl
lock=open("/tmp/aql-render21-"+str(os.getuid())+".lock","a+b")
fcntl.flock(lock,fcntl.LOCK_EX)
g.stopped()
def verified():
 assert g.lab.tree(g.GAME/'saves/Aqualumen-Rain-Walk')==base['rainWalk'] and g.lab.tree(g.GAME/'saves/Aqualumen-Lantern-House')==base['lanternHouse']
 assert g.lab.tree(g.GAME/'mods')==base['mods'] and not g.SENTINEL.exists()
 assert not any((g.CONTROL/k).exists() for k in ['request.properties','opaque-fixture-journal.json','local-light-fixture-journal.json','hand-light-fixture-journal.json'])
 assert g.lab.shared.prior.ordinary_tree()==base['ordinarySave']
 assert g.lab.pairs((g.GAME/'config/iris.properties').read_bytes())['shaderPack']==selected['selected']
 assert g.lab.sha(g.GAME/'shaderpacks'/selected['selected'])==selected['sha256']
iris=g.GAME/'config/iris.properties'
prior=iris.read_bytes()
assert g.lab.pairs(prior)['shaderPack'] in (base['previous'],selected['selected'])
assert g.lab.pairs(prior)['enableShaders']=='true'
assert g.lab.tree(g.GAME/'mods')==base['mods'] and g.lab.shared.prior.ordinary_tree()==base['ordinarySave']
assert g.lab.sha(g.GAME/'shaderpacks'/selected['selected'])==selected['sha256'] and not g.SENTINEL.exists()
g.replace(iris,g.lab.replace_values(prior,{'shaderPack':selected['selected']},'='))
verified()
env=dict(os.environ,DISPLAY=':1',XDG_RUNTIME_DIR='/run/user/1000',DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
latest=g.GAME/'logs/latest.log'; old=latest.stat().st_mtime_ns; d=tempfile.mkdtemp(prefix='aqualumen-final-title-',dir=Path.home()/'.cache')
with open(Path(d)/'launcher.log','xb') as f:
 os.fchmod(f.fileno(),0o600)
 subprocess.run(['systemd-run','--user','--unit=aql-ordinary-title-'+str(time.time_ns()),'--property=ExitType=cgroup','--setenv=DISPLAY=:1','--setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus','--setenv=XDG_RUNTIME_DIR=/run/user/1000','/usr/bin/flatpak','run','--command=prismrun','org.prismlauncher.PrismLauncher','--launch','Aqualumen Lab'],env=env,stdout=f,stderr=f,check=True)
until=time.monotonic()+100
while time.monotonic()<until:
 pids=g.lab.lab_java_processes(g.GAME)
 if len(pids)==1 and latest.exists() and old!=latest.stat().st_mtime_ns:
  lines=latest.read_text(errors='replace')
  if ('Using shaderpack: '+selected['selected'] in lines and 'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti' in lines and 'Created: ' in lines and 'textures/atlas/particles.png-atlas' in lines):
   ids={s for line in Path('/proc',str(pids[0]),'status').read_text().splitlines() if line.startswith('NSpid:') for s in line.split()[1:]}
   windows=[a for line in subprocess.check_output(['wmctrl','-lp'],env=env,text=True).splitlines() if len(a:=line.split(None,4))==5 and a[2] in ids and 'Minecraft' in a[4]]
   if len(windows)==1:break
 time.sleep(.5)
else:raise RuntimeError('Title startup not confirmed')
time.sleep(3)
verified()
lines=latest.read_text(errors='replace')
assert 'logged in with entity id' not in lines and 'starting integrated minecraft server' not in lines.lower() and 'reverting to default' not in lines.lower()
result=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-n','-f','x11grab','-window_id',str(int(windows[0][0],16)),'-i',env['DISPLAY'],'-frames:v','1','-vf','scale=800:-2',str(r/'lab-title.jpg')],env=env,timeout=6)
print('Lab window',windows[0][4], 'image exit',result.returncode)
g.receipt(r/'handoff.json',dict(running=True,launchedWithoutWorld=True,joinedWorld=False,normalConfiguration=True,normalModsExact=True,shader=selected['selected'],sha256=selected['sha256'],ordinaryFilesExact=len(base['ordinarySave']),benchmarkDisabled=True,renderer=s['renderer'],window=windows[0][4]))
