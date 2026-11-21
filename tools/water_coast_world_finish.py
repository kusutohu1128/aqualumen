"""NEW coast-world packet snapshots, normal handoff checks and immutable sealing."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from water_coast_world_pack import ROOT,OUT
from water_coast_world_lifecycle import GAME,core
import report


def terrain():
    core.closed();assert 'All dimensions are saved' in (OUT/'test-clean-save-exit.log').read_text()
    world=GAME/'saves/AqualumenNaturalV2';marker=world/'aqualumen-world.properties'
    expected=dict(schema='2',world_id=core.WORLD,seed='308060',generator='minecraft:noise/overworld',minecraft='1.21.1')
    assert dict(line.split('=',1) for line in marker.read_text().splitlines())==expected
    region=world/'region/r.-1.0.mca'
    assert not world.is_symlink() and not region.is_symlink() and 8192<=region.stat().st_size<=64*1024*1024
    digest=core.sha(region);target=OUT/'saved-test-coast-terrain';target.mkdir(exist_ok=False)
    for p in (marker,region):
        with (target/p.name).open('xb') as f:f.write(p.read_bytes())
        assert core.sha(p)==core.sha(target/p.name)
    assert core.sha(region)==digest
    core.save('saved-test-coast-terrain.json',dict(worldUUID=core.WORLD,seed=308060,closedJava=True,
        regionSHA256=digest,regionSizeBytes=region.stat().st_size,ordinaryWorldReadOrWritten=False,
        geometryAndRawSameFrameProven=False,cleanExitLog='test-clean-save-exit.log'))
    print('NEW closed TEST coast snapshot retained; no ordinary save copied/restored')


def finish(pid,handle,runtime,pause):
    baseline=json.loads((OUT/'fresh-normal-baseline.json').read_text())
    for name in ('normal-restored.json','normal-final-prelaunch.json'):
        assert json.loads((OUT/name).read_text())==baseline
    proc=Path('/proc')/str(pid);assert (proc/'comm').read_text().strip()=='java'
    lock=GAME/'saves/新規ワールド/session.lock';fds=[]
    for p in (proc/'fd').iterdir():
        try:
            if p.readlink()==lock:fds.append(int(p.name))
        except (FileNotFoundError,PermissionError):pass
    assert len(fds)==1
    assert {p.name:core.sha(p) for p in (GAME/'mods').glob('*.jar')}==baseline['activeMods']
    assert not any((GAME/'config'/n).exists() for n in baseline['instrumentationEntryPointsAbsent'])
    assert all(not (GAME/'aqualumen-benchmark'/n).exists() for n in ('request.properties','opaque-test-journal.json','opaque-fixture-journal.json'))
    backup=Path(baseline['backup']);props=lambda t:sorted(l for l in t.splitlines() if l and not l.startswith('#'))
    assert props((GAME/'config/iris.properties').read_text())==props((backup/'config/iris.properties').read_text())
    for name in ('options.txt','config/aqualumen-benchmark.properties'):
        assert core.sha(GAME/name)==baseline['configSHA256'][name]
    assert core.sha(GAME/'shaderpacks/Aqualumen-0.6.0.zip')=='6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73'
    meta=json.loads((OUT/'pack.json').read_text())
    assert all(core.sha(ROOT/n)==digest for n,digest in meta['originalSHA256'].items())
    log=(GAME/'logs/latest.log').read_text()
    assert 'Using shaderpack: Aqualumen-0.6.0.zip' in log and 'NVIDIA GeForce RTX 3080 Ti' in log
    assert '[Aqualumen Physics] 0.2.0 contact bridge initialized' in log
    assert 'Failed to load the shaderpack' not in log and 'Benchmark idle' not in log
    with (OUT/'normal-runtime.log').open('x') as f:f.write(log)
    for kind,name in (('runtime',runtime),('pause',pause)):
        assert Path(name).name==name
        p=GAME/'screenshots'/name;report.check_png(p,[1600,900])
        with (OUT/f'normal-{kind}.png').open('xb') as f:f.write(p.read_bytes())
    for test in sorted((ROOT/'tools').glob('test_water_coast_world*.py')):
        r=subprocess.run(['rtk','proxy','python3',str(test)],cwd=ROOT,capture_output=True,text=True)
        with (OUT/(test.name+'.log')).open('x') as f:f.write(r.stdout+r.stderr)
        assert r.returncode==0
    r=subprocess.run(['rtk','proxy','git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
    with (OUT/'git-diff-check.log').open('x') as f:f.write(r.stdout+r.stderr)
    assert r.returncode==0
    core.save('checkpoint.json',dict(schema='aqualumen-coast-world-handoff-v1',ordinaryLiveOwnedHandle=handle,
        ordinaryHostJava=pid,ordinaryLockFD=fds[0],normalPack='Aqualumen-0.6.0.zip',physics='0.2.0',
        originalProductionSourceBytesUnchanged=True,allOptInEntryPointsAbsent=True,
        ordinarySaveExactBeforeReopening=True,ordinarySaveRestored=False,ordinaryWorldAutomation=False,
        currentSaveAfterReopeningFrozen=False,oldEvidencePreserved=True,nativeGLAfterFinalNormalRelaunch=False,
        runtimeScreenshot='normal-runtime.png',pauseScreenshot='normal-pause.png',
        physicalFirstVisibleObjectAccepted=False,productionCoastFixImplemented=False,fullGoalAchieved=False))
    print('Normal0.6/physics0.2 verified live; TEST disabled; production unchanged; full goal active')


def seal():
    assert (OUT/'checkpoint.json').exists() and not (OUT/'SHA256SUMS').exists()
    for role in ('water-coast-stop','water-coast-attribution','water-path-precision','water-observed-plane','water-source-boundary','water-boundary-regression'):
        subprocess.run(['rtk','proxy','sha256sum','--quiet','-c',str(ROOT/f'reports/2026-10-06-{role}/SHA256SUMS')],cwd=ROOT,check=True)
    paths=sorted((ROOT/'tools').glob('*water_coast_world*.py'))
    frozen=OUT/'frozen-tool-source';frozen.mkdir(exist_ok=False)
    for p in paths:shutil.copy2(p,frozen/p.name)
    for name in ('audit-fixture-air.py','water_coast_attribution_pack.py','water_coast_stop_pack.py','water_coast_stop_raw.py',
                 'water_coast_attribution_lifecycle.py','water_legacy_branch_snapshot.py','report.py'):
        shutil.copy2(ROOT/'tools'/name,frozen/name)
    shutil.copy2(ROOT/'docs/REALISM_GOAL.md',frozen/'REALISM_GOAL.md')
    shutil.copy2(ROOT/'docs/reviews/codex-occluded-water-receiver-next.md',frozen/'occluded-water-receiver-next.md')
    with (OUT/'tracked-diff-at-handoff.patch').open('xb') as f:
        f.write(subprocess.check_output(['rtk','proxy','git','diff','--binary'],cwd=ROOT))
    files=sorted(p for p in OUT.rglob('*') if p.is_file())
    with (OUT/'SHA256SUMS').open('x') as f:
        for p in files+paths:f.write(core.sha(p)+'  '+p.relative_to(ROOT).as_posix()+'\n')
    subprocess.run(['rtk','proxy','sha256sum','--quiet','-c',str(OUT/'SHA256SUMS')],cwd=ROOT,check=True)
    print('NEW coast-world packet sealed:',len(files)+len(paths),'files')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('terrain','finish','seal'))
    p.add_argument('--pid',type=int);p.add_argument('--handle',type=int);p.add_argument('--runtime');p.add_argument('--pause')
    a=p.parse_args()
    if a.action=='finish':finish(a.pid,a.handle,a.runtime,a.pause)
    else:globals()[a.action]()
