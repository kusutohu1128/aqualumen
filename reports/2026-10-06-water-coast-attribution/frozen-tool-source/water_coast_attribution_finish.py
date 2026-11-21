"""Verify normal live configuration and freeze this NEW packet, not old evidence."""
import json
from pathlib import Path
import shutil
import subprocess
from water_coast_attribution_pack import ROOT, OUT
from water_coast_attribution_lifecycle import GAME, sha, save
import report


def finish():
    baseline=json.loads((OUT/'fresh-normal-baseline.json').read_text())
    assert json.loads((OUT/'normal-restored.json').read_text()) == baseline
    assert json.loads((OUT/'normal-final-prelaunch.json').read_text()) == baseline
    assert Path('/proc/3268991/comm').read_text().strip()=='java'
    assert Path('/proc/3268991/fd/154').readlink() == GAME/'saves/新規ワールド/session.lock'
    assert {p.name:sha(p) for p in (GAME/'mods').glob('*.jar')} == baseline['activeMods']
    assert not any((GAME/'config'/n).exists() for n in baseline['instrumentationEntryPointsAbsent'])
    for name in ('request.properties','opaque-test-journal.json','opaque-fixture-journal.json'):
        assert not (GAME/'aqualumen-benchmark'/name).exists()
    def properties(text):
        return sorted(line for line in text.splitlines() if line and not line.startswith('#'))
    backup=Path(baseline['backup'])
    assert properties((GAME/'config/iris.properties').read_text()) == properties((backup/'config/iris.properties').read_text())
    for name in ('options.txt','config/aqualumen-benchmark.properties'):
        assert sha(GAME/name)==baseline['configSHA256'][name]
    assert sha(GAME/'shaderpacks/Aqualumen-0.6.0.zip')=='6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73'
    packet=json.loads((OUT/'pack-v2.json').read_text())
    assert all(sha(ROOT/n)==digest for n,digest in packet['originalSHA256'].items())
    log=(GAME/'logs/latest.log').read_text()
    assert 'Using shaderpack: Aqualumen-0.6.0.zip' in log
    assert '[Aqualumen Physics] 0.2.0 contact bridge initialized' in log
    assert 'NVIDIA GeForce RTX 3080 Ti' in log and 'Failed to load the shaderpack' not in log
    assert 'Benchmark idle' not in log
    shutil.copy2(GAME/'logs/latest.log',OUT/'normal-runtime.log')
    for kind,stamp in (('runtime','14.17.48'),('pause','14.18.31')):
        source=GAME/'screenshots'/f'2026-10-06_{stamp}.png'
        report.check_png(source,[1600,900])
        shutil.copy2(source,OUT/f'normal-{kind}.png')
    for name in ('test_water_coast_attribution_pack.py','test_water_coast_attribution_image.py','test_water_coast_attribution_raw.py'):
        result=subprocess.run(['rtk','proxy','python3','tools/'+name],cwd=ROOT,capture_output=True,text=True)
        with (OUT/(name+'.log')).open('x') as f:
            f.write(result.stdout+result.stderr)
        assert result.returncode==0
    result=subprocess.run(['rtk','proxy','git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
    with (OUT/'git-diff-check.log').open('x') as f:
        f.write(result.stdout+result.stderr)
    assert result.returncode==0
    result=subprocess.check_output(['rtk','proxy','git','diff','--binary'],cwd=ROOT)
    with (OUT/'tracked-diff-at-handoff.patch').open('xb') as f:
        f.write(result)
    save('checkpoint.json',dict(schema='aqualumen-coast-attribution-handoff-v1',
        ordinaryLiveOwnedHandle=68513,ordinaryHostJava=3268991,ordinaryLockFD=154,
        window=62914567,display=':1',runtimeScreenshot='normal-runtime.png',pauseScreenshot='normal-pause.png',
        normalPack='Aqualumen-0.6.0.zip',physics='0.2.0',normalSettings=[1600,900,120,12,6],
        originalProductionSourceBytesUnchanged=True,allOptInEntryPointsAbsent=True,
        ordinarySaveExactBeforeReopening=True,ordinarySaveRestored=False,ordinaryWorldAutomation=False,
        currentSaveAfterReopeningFrozen=False,oldEvidencePreserved=True,nativeGLAfterNormalRelaunch=False,
        naturalCoastReceiverProxyCorrelationQualified=True,productionCoastFixImplemented=False,
        physicalFirstVisibleObjectProven=False,fullGoalAchieved=False))
    print('Normal0.6/physics0.2 verified live, TEST disabled;7 CPU tests and diff check pass; production unchanged')


def seal():
    assert (OUT/'checkpoint.json').exists() and not (OUT/'SHA256SUMS').exists()
    paths=sorted((ROOT/'tools').glob('*water_coast_attribution*.py'))
    frozen=OUT/'frozen-tool-source'
    frozen.mkdir(exist_ok=False)
    for path in paths:
        shutil.copy2(path,frozen/path.name)
    for name in ('report.py','water_legacy_branch_snapshot.py'):
        shutil.copy2(ROOT/'tools'/name,frozen/name)
    shutil.copy2(ROOT/'docs/REALISM_GOAL.md',frozen/'REALISM_GOAL.md')
    result=subprocess.check_output(['rtk','proxy','git','diff','--binary'],cwd=ROOT)
    with (OUT/'final-tracked-diff.patch').open('xb') as f:
        f.write(result)
    files=sorted(p for p in OUT.rglob('*') if p.is_file())
    with (OUT/'SHA256SUMS').open('x') as f:
        for path in files+paths:
            f.write(sha(path)+'  '+path.relative_to(ROOT).as_posix()+'\n')
    result=subprocess.run(['rtk','proxy','sha256sum','--quiet','-c',str((OUT/'SHA256SUMS').relative_to(ROOT))],cwd=ROOT)
    assert result.returncode==0
    print('NEW packet sealed:',len(files)+len(paths),'files; never regenerate into this evidence')


if __name__=='__main__':
    import sys
    {'finish':finish,'seal':seal}[sys.argv[1]]()
