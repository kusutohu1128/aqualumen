"""Close-only TEST terrain snapshot and verified ordinary handoff; exclusive evidence."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from water_coast_stop_pack import ROOT, OUT
from water_coast_stop_lifecycle import GAME, reusable
import report


def terrain():
    reusable.closed()
    assert 'All dimensions are saved' in (OUT/'test-clean-save-exit.log').read_text()
    world=GAME/'saves/AqualumenNaturalV2'
    marker=world/'aqualumen-world.properties'
    expected=dict(schema='2',world_id=reusable.WORLD,seed='308060',generator='minecraft:noise/overworld',minecraft='1.21.1')
    assert dict(line.split('=',1) for line in marker.read_text().splitlines())==expected
    source=world/'region/r.-1.0.mca'
    assert not world.is_symlink() and not source.is_symlink()
    assert 8192<=source.stat().st_size<=64*1024*1024
    before=reusable.sha(source)
    target=OUT/'saved-test-coast-terrain';target.mkdir(exist_ok=False)
    for path in (marker,source):
        with (target/path.name).open('xb') as f:f.write(path.read_bytes())
        assert reusable.sha(path)==reusable.sha(target/path.name)
    assert reusable.sha(source)==before
    reusable.save('saved-test-coast-terrain.json',dict(schema='aqualumen-closed-test-terrain-snapshot-v1',
        worldUUID=reusable.WORLD,seed=308060,region='r.-1.0.mca',regionSHA256=before,
        regionSizeBytes=source.stat().st_size,closedJava=True,cleanSaveLog='test-clean-save-exit.log',
        capturedCoastCamera=[-191.5,65.71999988555908,320.5],
        ordinaryWorldReadOrWritten=False,physicalFirstReceiverProven=False,
        reason='Read-only snapshot of exact UUID-guarded TEST coast after clean exit; future independent geometry reader'))
    print('Closed TEST coast region retained read-only; not a first-hit proof')


def finish(pid, handle, runtime, pause):
    baseline=json.loads((OUT/'fresh-normal-baseline.json').read_text())
    for name in ('normal-restored.json','normal-final-prelaunch.json'):
        assert json.loads((OUT/name).read_text())==baseline
    proc=Path('/proc')/str(pid)
    assert (proc/'comm').read_text().strip()=='java'
    expected=GAME/'saves/新規ワールド/session.lock'
    locks=[]
    for fd in (proc/'fd').iterdir():
        try:
            if fd.readlink()==expected:locks.append(int(fd.name))
        except (FileNotFoundError,PermissionError): pass
    assert len(locks)==1
    assert {p.name:reusable.sha(p) for p in (GAME/'mods').glob('*.jar')}==baseline['activeMods']
    assert not any((GAME/'config'/n).exists() for n in baseline['instrumentationEntryPointsAbsent'])
    for name in ('request.properties','opaque-test-journal.json','opaque-fixture-journal.json'):
        assert not (GAME/'aqualumen-benchmark'/name).exists()
    backup=Path(baseline['backup'])
    properties=lambda text:sorted(line for line in text.splitlines() if line and not line.startswith('#'))
    assert properties((GAME/'config/iris.properties').read_text())==properties((backup/'config/iris.properties').read_text())
    for name in ('options.txt','config/aqualumen-benchmark.properties'):
        assert reusable.sha(GAME/name)==baseline['configSHA256'][name]
    assert reusable.sha(GAME/'shaderpacks/Aqualumen-0.6.0.zip')=='6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73'
    packet=json.loads((OUT/'pack.json').read_text())
    assert all(reusable.sha(ROOT/n)==digest for n,digest in packet['originalSHA256'].items())
    log=(GAME/'logs/latest.log').read_text()
    assert 'Using shaderpack: Aqualumen-0.6.0.zip' in log
    assert '[Aqualumen Physics] 0.2.0 contact bridge initialized' in log
    assert 'NVIDIA GeForce RTX 3080 Ti' in log and 'Failed to load the shaderpack' not in log
    assert 'Benchmark idle' not in log
    with (OUT/'normal-runtime.log').open('x') as f:f.write(log)
    for kind,name in (('runtime',runtime),('pause',pause)):
        assert Path(name).name==name
        source=GAME/'screenshots'/name;report.check_png(source,[1600,900])
        with (OUT/f'normal-{kind}.png').open('xb') as f:f.write(source.read_bytes())
    tests=sorted((ROOT/'tools').glob('test_water_coast_stop*.py'))
    assert len(tests)==4
    for test in tests:
        result=subprocess.run(['rtk','proxy','python3',str(test)],cwd=ROOT,capture_output=True,text=True)
        with (OUT/(test.name+'.log')).open('x') as f:f.write(result.stdout+result.stderr)
        assert result.returncode==0
    result=subprocess.run(['rtk','proxy','git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
    with (OUT/'git-diff-check.log').open('x') as f:f.write(result.stdout+result.stderr)
    assert result.returncode==0
    reusable.save('checkpoint.json',dict(schema='aqualumen-coast-stop-handoff-v1',
        ordinaryLiveOwnedHandle=handle,ordinaryHostJava=pid,ordinaryLockFD=locks[0],
        normalPack='Aqualumen-0.6.0.zip',physics='0.2.0',normalSettings=[1600,900,120,12,6],
        originalProductionSourceBytesUnchanged=True,allOptInEntryPointsAbsent=True,
        ordinarySaveExactBeforeReopening=True,ordinarySaveRestored=False,ordinaryWorldAutomation=False,
        currentSaveAfterReopeningFrozen=False,oldEvidencePreserved=True,nativeGLAfterNormalRelaunch=False,
        runtimeScreenshot='normal-runtime.png',pauseScreenshot='normal-pause.png',
        eightMissesPersistAt32=True,productionCoastFixImplemented=False,
        physicalFirstVisibleObjectProven=False,fullGoalAchieved=False))
    print('Ordinary0.6/physics0.2 verified live;9 reader/source CPU tests passed; full goal active')


def seal():
    assert (OUT/'checkpoint.json').exists() and not (OUT/'SHA256SUMS').exists()
    for role in ('water-coast-attribution','water-path-precision','water-observed-plane','water-source-boundary','water-boundary-regression'):
        subprocess.run(['rtk','proxy','sha256sum','--quiet','-c',str(ROOT/f'reports/2026-10-06-{role}/SHA256SUMS')],cwd=ROOT,check=True)
    paths=sorted((ROOT/'tools').glob('*water_coast_stop*.py'))
    frozen=OUT/'frozen-tool-source';frozen.mkdir(exist_ok=False)
    for path in paths:
        shutil.copy2(path,frozen/path.name)
    for name in ('water_coast_attribution_lifecycle.py','water_coast_attribution_pack.py','report.py','water_legacy_branch_snapshot.py'):
        shutil.copy2(ROOT/'tools'/name,frozen/name)
    shutil.copy2(ROOT/'docs/REALISM_GOAL.md',frozen/'REALISM_GOAL.md')
    result=subprocess.check_output(['rtk','proxy','git','diff','--binary'],cwd=ROOT)
    with (OUT/'tracked-diff-at-handoff.patch').open('xb') as f:f.write(result)
    files=sorted(p for p in OUT.rglob('*') if p.is_file())
    with (OUT/'SHA256SUMS').open('x') as f:
        for path in files+paths:f.write(reusable.sha(path)+'  '+path.relative_to(ROOT).as_posix()+'\n')
    subprocess.run(['rtk','proxy','sha256sum','--quiet','-c',str(OUT/'SHA256SUMS')],cwd=ROOT,check=True)
    print('NEW immutable packet sealed:',len(files)+len(paths),'files; never regenerate into this report')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('terrain','finish','seal'))
    p.add_argument('--pid',type=int);p.add_argument('--handle',type=int)
    p.add_argument('--runtime');p.add_argument('--pause');a=p.parse_args()
    if a.action=='finish':finish(a.pid,a.handle,a.runtime,a.pause)
    else:globals()[a.action]()
