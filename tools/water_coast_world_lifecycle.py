"""New-destination reversible Lab operations; sealed lifecycle code is unchanged."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import water_coast_attribution_lifecycle as core
from water_coast_world_pack import ROOT,OUT,PACK
import report

core.OUT=OUT;core.PACK=core.BUILT_PACK=PACK;core.INFO='pack.json'
core.RUN='coast-world-1440-20261006-v1'
GAME=core.GAME


def recover_normal():
    core.closed()
    old=json.loads((ROOT/'reports/2026-10-06-water-coast-stop/fresh-normal-baseline.json').read_text())
    assert {p.name:core.sha(p) for p in (GAME/'mods').glob('*.jar')}==old['activeMods']
    assert 'shaderPack=Aqualumen-0.6.0.zip' in (GAME/'config/iris.properties').read_text()
    assert not any((GAME/'config'/n).exists() for n in old['instrumentationEntryPointsAbsent'])
    assert core.sha(GAME/'options.txt')==old['configSHA256']['options.txt']
    assert not (OUT/'fresh-normal-baseline.json').exists()
    shutil.copy2(GAME/'logs/latest.log',OUT/'ordinary-ui-close-interruption.log')
    backup=Path(tempfile.mkdtemp(prefix='aqualumen-legacy-branch-host-coast-world-recovery-',dir='/home/kusutohu/.cache'))
    core.save('ordinary-recovery-launch.json',dict(previousJavaAbsent=True,previousCleanSaveExitProven=False,
        normalAssetsVerified=True,TESTInstalled=False,privateCache=str(backup),ordinarySaveRestored=False))
    descriptor=os.open(backup/'launcher-private.log',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    print('NORMAL recovery launch; original saves retained; authentication log private',flush=True)
    with os.fdopen(descriptor,'wb') as log:
        r=subprocess.run(['rtk','proxy','flatpak','run','--command=prismrun','org.prismlauncher.PrismLauncher',
            '--launch','Aqualumen Lab','--world','新規ワールド'],cwd=ROOT,env=dict(os.environ,DISPLAY=':1'),stdout=log,stderr=subprocess.STDOUT)
    print('NORMAL RECOVERY LAUNCHER EXIT',r.returncode,flush=True)
    raise SystemExit(r.returncode)


def baseline():
    core.closed();assert 'All dimensions are saved' in (GAME/'logs/latest.log').read_text()
    backup=Path(tempfile.mkdtemp(prefix='aqualumen-legacy-branch-host-coast-world-',dir='/home/kusutohu/.cache'))
    for name in ('options.txt','config/iris.properties','config/aqualumen-benchmark.properties'):
        p=backup/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(GAME/name,p)
    value=json.loads(subprocess.check_output(['rtk','proxy','python3','tools/water_legacy_branch_snapshot.py',str(backup)],cwd=ROOT))
    core.save('fresh-normal-baseline.json',value)
    shutil.copy2(GAME/'logs/latest.log',OUT/'normal-clean-save-exit.log')
    print('NEW post-save baseline recorded:',backup)


def compile():
    core.closed()
    r=subprocess.run(['rtk','proxy','build/glcheck',str(OUT/'diagnostic-source-v1/shaders'),'--compile-only'],cwd=ROOT,capture_output=True,text=True)
    with (OUT/'native-compile-only.log').open('x') as f:f.write(r.stdout+r.stderr)
    assert r.returncode==0 and 'RTX 3080 Ti' in r.stdout
    print(r.stdout)


def collect():
    source=GAME/'aqualumen-benchmark/runs'/core.RUN
    run,rows=report.load_run(source)
    assert run['run_id']==core.RUN and run['pack_name']==PACK
    assert run['pack_sha256']==json.loads((OUT/'pack.json').read_text())['packSHA256']
    assert run['world_id']==core.WORLD and run['seed']==308060 and run['scenarios']==['coast-day']
    assert run['expected_resolution']==[2560,1440] and 'RTX 3080 Ti' in run['gl_renderer']
    assert run['mods']['iris']=='1.8.8+mc1.21.1' and len(rows)==1 and rows[0]['window_focused']
    target=OUT/'iris1440-run-v1';assert not target.exists();shutil.copytree(source,target)
    assert {p.relative_to(source).as_posix():core.sha(p) for p in source.rglob('*') if p.is_file()}=={
        p.relative_to(target).as_posix():core.sha(p) for p in target.rglob('*') if p.is_file()}
    core.save('iris1440-audit.json',dict(actualIrisActiveWithoutFallback=True,strictOriginalReportReaderPassed=True,
        worldUUID=run['world_id'],packSHA256=run['pack_sha256'],scenes=rows,
        naturalAppearanceAccepted=False,neutralityProven=False,PNGAndRawSameFrame=False,fullGoalAchieved=False))
    print('NEW actual coast world witness run archived:',rows[0]['frames'],'raw intervals')


if __name__=='__main__':
    import sys
    action=sys.argv[1]
    if action in ('test','normal'):core.launch(action)
    elif action in ('restore','install'):getattr(core,action)()
    else:{'baseline':baseline,'compile':compile,'collect':collect,'recover_normal':recover_normal}[action]()
