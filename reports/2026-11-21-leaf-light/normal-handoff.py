"""Install the accepted shader and verify an uninstrumented launch inside the isolated Lab."""
import json,os,re,subprocess,sys,time,tempfile,fcntl,shutil
from zipfile import ZipFile
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tools'))
import ground_shadow_lab as g

renderLock=open('/tmp/aql-render21-'+str(os.getuid())+'.lock','a+b')
fcntl.flock(renderLock,fcntl.LOCK_EX)
root=Path('reports/2026-11-21-leaf-light')
base=json.loads((root/'normal-before.json').read_text())
game=g.GAME
zipfile=Path('dist/Aqualumen-1.8.0.zip')
physics=Path('dist/aqualumen-physics-0.2.0.jar')
sha=g.lab.sha(zipfile)
dest=game/'shaderpacks'/zipfile.name
iris=game/'config/iris.properties'
ownedlog=Path(tempfile.mkdtemp(prefix='aqualumen-final-normal-',dir=Path.home()/'.cache'))
env=dict(os.environ,DISPLAY=':1',XDG_RUNTIME_DIR='/run/user/1000',DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus')
def state():
    assert set(p.name for p in (game/'mods').glob('*.jar'))==g.lab.NORMAL_MODS
    assert g.lab.tree(game/'mods')==base['mods'] and not g.SENTINEL.exists()
    assert not any((g.CONTROL/p).exists() for p in ('request.properties','opaque-fixture-journal.json','local-light-fixture-journal.json','hand-light-fixture-journal.json'))
    assert g.lab.shared.prior.ordinary_tree()==base['ordinarySave']
    assert g.lab.tree(game/'saves/Aqualumen-Rain-Walk')==base['rainWalk']
    assert g.lab.tree(game/'saves/Aqualumen-Lantern-House')==base['lanternHouse']
    assert g.lab.sha(game/'mods'/physics.name)==g.lab.sha(physics)
    assert g.lab.sha(game/'shaderpacks'/g.lab.ORDINARY)==g.lab.ORDINARY_SHA
    assert not (dest.parent/(zipfile.name+'.txt')).exists()
def launch(tag,world=None):
    args=['flatpak','run','--command=prismrun','org.prismlauncher.PrismLauncher','--launch','Aqualumen Lab']
    if world:args+=['--world',world]
    with (ownedlog/(tag+'.log')).open('xb') as log:
        os.fchmod(log.fileno(),0o600)
        return subprocess.Popen(args,env=env,stdout=log,stderr=log)
# Only close the ordinary title we left running. The isolated QA clients have exited.
pids=[pid for pid in g.lab.lab_java_processes(game) if Path('/proc',str(pid),'cwd').resolve()==game.resolve()]
if pids:
    title=json.loads(Path("reports/2026-11-21-rain-eaves/handoff.json").read_text())
    assert title["launchedWithoutWorld"] and not title["joinedWorld"] and title["shader"]==base["previous"]
    assert pids==base["ownedTitleAtStart"] and Path("/proc",str(pids[0]),"cwd").resolve()==game.resolve()
    last=(game/"logs/latest.log").read_text(errors="replace").lower()
    assert "logged in with entity id" not in last and "starting integrated minecraft server" not in last and "connecting to " not in last
    state()
    subprocess.run([sys.executable,"/tmp/aqualumen-owned-close.py"],check=True)
    end=time.monotonic()+35
    while g.lab.lab_java_processes(game) and time.monotonic()<end: time.sleep(.3)
g.stopped();state();g.lab.shared.owned_paths();g.lab.shared.world_marker()
# A fresh smoke save keeps both the delivered rainy spawn and the V2 evidence unchanged.
smoke_name="Aqualumen-Private-Install-"+sha[:12]
smoke_save=game/'saves'/smoke_name
assert not smoke_save.exists()
source_zip=Path('dist/Aqualumen-Rain-Walk.zip')
expected=json.loads((Path('reports/2026-11-21-rain-eaves/playable/validation.json')).read_text())['archiveFiles']
source_digest=g.lab.tree(game/'saves'/g.lab.WORLD)
with tempfile.TemporaryDirectory(prefix='rain-install-',dir=game.parent) as scratch:
    with ZipFile(source_zip) as world_zip:
        assert sorted(world_zip.namelist())==sorted(expected)
        for entry in world_zip.namelist():
            target=Path(scratch)/entry
            assert target.resolve().is_relative_to(Path(scratch)/'Aqualumen-Rain-Walk')
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(world_zip.read(entry))
    (Path(scratch)/'Aqualumen-Rain-Walk').rename(smoke_save)
before=iris.read_bytes()
assert not (root/'normal-selection.json').exists() and not (root/'normal-smoke.json').exists()
assert g.lab.sha(game/'shaderpacks'/base['previous'])==base['previousSHA']
optionsBefore=g.lab.pairs((game/'options.txt').read_bytes(),':')
assert g.lab.pairs(before)['enableShaders']=='true' and g.lab.pairs(before)['shaderPack']==base['previous']
if not dest.exists():g.lab.shared.install_new(zipfile,dest,sha)
assert not dest.is_symlink() and g.lab.sha(dest)==sha
updated=g.lab.replace_values(before,{'shaderPack':zipfile.name},'=')
try:
    g.replace(iris,updated)
    g.receipt(root/'normal-selection.json',dict(previous=base["previous"],selected=dest.name,sha256=sha,physics=g.lab.sha(physics),ordinaryFiles=len(base['ordinarySave'])))
    logpath=game/'logs/latest.log'
    previous=logpath.stat().st_mtime_ns
    p=launch('smoke',smoke_name)
    deadline=time.monotonic()+900
    while time.monotonic()<deadline:
        if logpath.exists() and logpath.stat().st_mtime_ns!=previous:
            log=logpath.read_text(errors='replace')
            if re.search(r'disabling shaders|reverting to default|\[Render thread/ERROR\]',log,re.I):
                raise RuntimeError('Original Lab reported a renderer failure')
            if (len(g.lab.lab_java_processes(game))==1 and 'Using shaderpack: '+dest.name in log and
                'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti' in log and 'logged in with entity id' in log and
                re.search(r'Creating pipeline for dimension minecraft:overworld.*?Started [1-9]\d* worker threads',log,re.S)
                and '0.2.0 contact bridge initialized' in log):
                break
        time.sleep(.5)
    else:raise RuntimeError('Normal shader launch not confirmed')
    assert 'disabling shaders' not in log.lower() and '[Render thread/ERROR]' not in log and 'reverting to default' not in log.lower() and '[Aqualumen] Benchmark' not in log
    assert smoke_name in ' '.join(str(x) for x in p.args)
    state()
    time.sleep(5)
    pid=g.lab.lab_java_processes(game)[0]
    ids=next(line.split()[1:] for line in Path('/proc',str(pid),'status').read_text().splitlines() if line.startswith('NSpid:'))
    windows=[row for line in subprocess.check_output(['wmctrl','-lp'],env=env,text=True).splitlines()
             if len(row:=line.split(None,4))==5 and row[2] in ids and 'Minecraft' in row[4]]
    assert len(windows)==1
    subprocess.run(['ffmpeg','-v','error','-n','-f','x11grab','-window_id',str(int(windows[0][0],16)),
                    '-i',env['DISPLAY'],'-frames:v','1','-vf','scale=960:-2',str(root/'normal-world.jpg')],env=env,check=True,timeout=10)
    # Only signal WM_DELETE_WINDOW for the single Minecraft window owned by this
    # exact Lab Java namespace. Minecraft performs its own save and shutdown.
    subprocess.run([sys.executable,'/tmp/aqualumen-owned-close.py'],check=True)
    deadline=time.monotonic()+40
    while g.lab.lab_java_processes(game) and time.monotonic()<deadline:time.sleep(.4)
    g.stopped()
    saved=logpath.read_text(errors='replace')
    assert 'Saving chunks' in saved and 'All dimensions are saved' in saved
    assert not re.search(r'disabling shaders|reverting to default|\[Render thread/ERROR\]|\[Aqualumen\] Benchmark',saved,re.I)
    state()
    assert g.lab.pairs(iris.read_bytes())==g.lab.pairs(updated)
    assert g.lab.pairs((game/'options.txt').read_bytes(),':')==optionsBefore
    assert g.lab.tree(game/'saves'/g.lab.WORLD)==source_digest
    archive=Path(tempfile.mkdtemp(prefix='aqualumen-rain-smoke-save-',dir=game.parent))
    smoke_save.rename(archive/smoke_name)
    g.receipt(root/'normal-smoke.json',dict(renderer='NVIDIA GeForce RTX 3080 Ti',shaderPack=dest.name,packSHA=sha,
        uninstrumentedWorld=smoke_name,protectedV2Exact=True,pipelineCreated=True,physicsInitialized='0.2.0',benchmarkDisabled=True,
        clientSaveAndShutdown=True,ordinaryFilesExact=len(base['ordinarySave']),normalModsExact=True,optionsExact=True))
    
    print("Normal smoke succeeded", flush=True)
except BaseException:
    # Keep the original choice recoverable even if the new smoke/title launch fails.
    if iris.read_bytes()==updated or g.lab.pairs(iris.read_bytes())==g.lab.pairs(updated):
        g.replace(iris,before)
    raise
