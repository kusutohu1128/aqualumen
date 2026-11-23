"""Run a single private client from the measured no-lava campaign."""
import argparse
from pathlib import Path
from collections import Counter
import csv
import json
from statistics import mean
import re
import shutil
import sys
from zipfile import ZipFile

from diagnostics import R, ROOT, OUT, digest, FACTORS

OLD=R.parent/'2026-11-22-gpu-profile'
sys.path.insert(0,str(OLD))
import run as guarded
import birch_scene as birch
import summarize as gpu
from profile_data import collect_window, read_rows, percentile
from measure import extract

RUNS=R/'runs'
BIRCH=('birch-off',)


CAMPAIGN = {
    'gp-idle-oh-off-a':('p8','off'),'gp-idle-p8-a':('p8','on'),
    'gp-idle-p9-a':('p9','on'),'gp-idle-p9-b':('p9','on'),
    'gp-idle-p8-b':('p8','on'),'gp-idle-oh-off-b':('p8','off'),
    'gp-idle-ft-p8-a':('p8','off'),'gp-idle-ft-p9-a':('p9','off'),
    'gp-idle-ft-p9-b':('p9','off'),'gp-idle-ft-p8-b':('p8','off')}
CHECKS=('check','check-lava','check-ground','check-canopy','check-animal','check-ceiling','check-eye')


def empty_hands(files, player, indices):
    prefix='data/animal/function/'
    checks=''.join(f'execute if items entity {player} weapon.{hand} * run scoreboard players set #ok aq_room 0\n'
                   for hand in ('mainhand','offhand'))
    for i in indices:
        for step in ('v','e'):
            key=f'{prefix}{step}{i}.mcfunction'
            line='execute if score #ok aq_room matches 1 run say'
            if line not in files[key]: raise ValueError(key)
            files[key]=files[key].replace(line,checks+line)
    return files


class FourScenes(birch.BirchRooms):
    def datapack(self,names):
        return empty_hands(super().datapack(names), self.PLAYER, range(4))


class BirchOnly(birch.BirchRooms):
    def self_test(self,names):
        if tuple(names) not in (BIRCH,birch.STAGES):
            raise ValueError(names)

    def geometry(self,names):
        result=super().geometry(birch.STAGES)
        result['birch']['stages']=list(BIRCH)
        result['stages']={}
        return result

    def datapack(self,names):
        self.self_test(names)
        files=super().datapack(birch.STAGES)
        prefix='data/animal/function/'
        files[prefix+'start.mcfunction']=files[prefix+'start.mcfunction'].replace('function animal:s0','function animal:s2')
        files[prefix+'s2.mcfunction']=files[prefix+'s2.mcfunction'].replace('function animal:s3','function animal:s2')
        return empty_hands(files,self.PLAYER,(2,))


def schedule():
    entries={}
    for key in ('stable','p3','comp-pragma','comp-default','def-five','def-four','p8','p9'):
        entries['gp-idle-src-'+key]=(key,'capture')
    for factor,(ctl,diag,_) in FACTORS.items():
        for prefix,side,key in (('ctl','a',ctl),('d','a',diag),('d','b',diag),('ctl','b',ctl)):
            entries[f'gp-idle-{prefix}-{factor}-{side}']=(key,'on')
    entries.update(CAMPAIGN)
    return entries


def snapshot_dist():
    return {p.relative_to(ROOT/'dist').as_posix():digest(p) for p in sorted((ROOT/'dist').rglob('*')) if p.is_file()}


def read(path):
    return json.loads(path.read_text())


def validate(folder,pack,mode):
    receipt=read(folder/'complete.json')
    pre=read(folder/'preflight.json')
    assert receipt['complete'] and receipt['originalWorldAndConfigUnchanged'] and receipt['shaderpackLogged']
    assert receipt['packSha256']==receipt['sourcePackShaNow']==digest(pack)
    assert receipt['sourceDigest']==read(OLD/'runs/gp-stable-b/complete.json')['sourceDigest']
    assert receipt['compilerModSha256']==guarded.LAB['compilerSha256']
    assert pre['labAfter']==pre['labBefore'] and pre['samples'] and not pre['foreignObservations']
    assert read(folder/'birch-world.json')==birch.audit_world()
    log=(folder/'client.log').read_text()
    assert 'AQ_PROFILE_INVALID' not in log and 'AQ_RENDER_PROBE_FAILED' not in log
    common=dict(renderer=receipt['gl'],packSha256=digest(pack),label=folder.name,mode=mode)
    scenes=receipt['stages']
    multi=tuple(scenes)==birch.STAGES
    assert multi or tuple(scenes)==BIRCH
    if multi:
        assert read(folder/'geometry.json')==read(OLD/'runs/gp-stable-b/geometry.json')
        assert '[Server] AQ_BIRCH_RESTORED' in log
    observer=read(folder/'observer.json')
    assert observer['frameObserverSha256']==digest(guarded.BUILD/'frame-sample.jar')
    assert observer['worldId']==read(folder/'birch-world.json')['world']
    frames={}
    if mode=='on':
        assert 'captureJar' not in observer and observer['gpuProfilerSha256']==digest(guarded.BUILD/'gpu-profiler.jar')
        hooks=re.findall(r'AQ_PROFILE_HOOK [^\n]+',log)
        assert Counter(hooks)==Counter((guarded.BUILD/'injections.txt').read_text().splitlines())
        assert 'AQ_PROFILE_STATE bindings preserved' in log and 'AQ_PROFILE_DROP' not in log
        with (guarded.BUILD/(folder.name+'.csv')).open() as stream:
            frames=read_rows(stream)
        with ZipFile(pack) as z:
            expected={('quad/' if ext=='fsh' else 'dispatch/')+name for path in z.namelist()
               for name,ext in re.findall(r'^shaders/((?:begin|prepare|shadowcomp|deferred|composite|final)\d*)\.(csh|fsh)$',path)}
    else:
        assert 'gpuProfilerSha256' not in observer and 'AQ_PROFILE_HOOK' not in log
        assert (mode=='capture')==('captureJar' in observer)
    windows={}
    rows=[]
    for scene in scenes:
        observation=extract(folder,scene,None,pack_path=pack,condition=scene)
        intervals=observation['intervalsUs']
        ids=gpu.window_ids(log,scene,intervals)
        image=birch.image_check(folder,scene) if scene in birch.BIRCH else {'sha256':observation['captureHash']}
        w=dict(frames=len(ids),image=image,firstFrame=ids[0],lastFrame=ids[-1],
               cpuMeanMs=mean(intervals)/1000,cpuP95Ms=percentile(intervals,.95)/1000,
               cpuP99Ms=percentile(intervals,.99)/1000,fps=1e6/mean(intervals))
        windows[scene]=w
        if frames:
            samples=collect_window(frames,ids)
            assert all({k for k in f['calls'] if k.startswith(('quad/','dispatch/'))}==expected
                       and all(f['draws'][k]==f['calls'][k]==1 for k in expected) for f in samples)
            w['gpu']=gpu.gpu_stats(samples)
            w['meanMs']={n:mean(f['inclusive'].get(n,0) for f in samples)/1e6 for n in w['gpu']['ranges']}
            w['meanMs']['uncovered']=mean(f['residual'] for f in samples)/1e6
            epoch,=set(e for e,n in frames if n==ids[0])
            for i,us in zip(ids,intervals):
                rows.extend((epoch,i,*row,scene,us) for row in frames[epoch,i])
    if rows:
        with (folder/'frames.csv').open('w') as stream:
            w=csv.writer(stream,lineterminator='\n')
            w.writerow(gpu.HEADER);w.writerows(rows)
    summary={**common,'scenes':windows} if multi else {**common,'scene':scenes[0],**windows[scenes[0]]}
    if mode=='capture':
        assert observer['captureJar']==digest(OUT/'idle-capture.jar')
        sources=OUT/'submitted'/folder.name
        for n in ('deferred','composite'):
            assert all((sources/(n+suffix)).is_file() for suffix in ('.vsh','.fsh','.state'))
        summary['sources']={p.name:digest(p) for p in sources.iterdir()}
        summary['pragma']={n:'#pragma optionNV(inline 128)' in (sources/(n+'.fsh')).read_text() for n in ('deferred','composite')}
        summary['fbo']={n:(sources/(n+'.state')).read_text().splitlines() for n in ('deferred','composite')}
    summary['validated']=True
    guarded.save(folder/'summary.json',summary)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('label')
    args=ap.parse_args()
    label=args.label
    base=guarded.run_base(label)
    name,mode=schedule()[base]
    packs=read(R/'packs.json')
    data=packs[name]
    pack=ROOT/data['file']
    assert digest(pack)==data['sha256']
    if (RUNS/label).exists(): raise FileExistsError(label)
    if base!=label:
        prior=base if label.endswith('1') else base+'-retry1'
        assert (RUNS/prior/'complete.json').exists() and len(list(RUNS.glob('*-retry[12]')))<2
    if base in CAMPAIGN:
        for driver in ('nvidia','mesa'):
            assert read(R/('candidate-full-'+driver+'.json'))['exit']==0
        for target in CHECKS:
            for phase in ('historical','regression'):
                assert read(R/(phase+'-'+target+'.json'))['exit']==0
        order=list(CAMPAIGN)
        for prior in order[:order.index(base)]:
            assert read(RUNS/guarded.latest(prior,RUNS)/'summary.json')['validated']
        if order.index(base)>order.index('gp-idle-p8-a'):
            assert all(x['pass'] for x in read(OUT/'overhead-a.json').values())
        if base.startswith('gp-idle-ft-'):
            assert read(OUT/'profile.json')['pass'] and all(x['pass'] for x in read(OUT/'overhead-b.json').values())
    elif mode=='on':
        factor=base.split('-')[-2]
        order=[k for k in schedule() if k.split('-')[-2]==factor and schedule()[k][1]=='on']
        for prior in order[:order.index(base)]:
            assert read(RUNS/guarded.latest(prior,RUNS)/'summary.json')['validated']
        for source in FACTORS[factor][:2]:
            assert read(RUNS/guarded.latest('gp-idle-src-'+source,RUNS)/'summary.json')['validated']
    if mode=='capture':
        assert digest(OUT/'idle-capture.jar')=='494b192287da88d4d52f34aa1648d291cb104640578e67b2277cc2036d5486f1'
    assert digest(guarded.BUILD/'gpu-profiler.jar')=='75d6e7307d9437c3aa165d25530878ea7f42456644e7112713728cc2c918ea20'
    assert digest(guarded.BUILD/'frame-sample.jar')=='636e71f6ad232cc0719391008612871d58c05d38cea8a39f8fbd0f7bc1c614fb'
    baseline=OUT/'dist-before.json'
    before=snapshot_dist()
    if not baseline.exists(): guarded.save(baseline,before)
    assert read(baseline)==before
    def prepare(game,out,mods):
        if mode=='capture':
            jar=shutil.copy2(OUT/'idle-capture.jar',game/'mods')
            mods['captureJar']=digest(Path(jar))
            (game/'config/idle-source.enabled').write_text(str(game))
    def collect(game,out):
        d=game/'idle-capture'
        if d.exists():
            shutil.copytree(d,OUT/'submitted'/label)
    fixed={'backend':'vgl','size':'2560x1440','period-ticks':'680','settle':'1','stages':'birch-off',
           'glcache':str(guarded.BUILD/'driver-cache'),'compiler-mod':str(ROOT/'dist/aqualumen-lighting-compiler-0.3.0.jar')}
    try:
        factory=BirchOnly
        if base in CAMPAIGN:
            factory=FourScenes
            fixed['stages']=','.join(birch.STAGES)
        guarded.launch(pack,label,'on' if mode=='on' else 'off',fixed,RUNS,factory,prepare,collect)
    except SystemExit as e:
        if e.code: raise
    finally:
        assert snapshot_dist()==before
    validate(RUNS/label,pack,mode)


if __name__=='__main__':
    main()
