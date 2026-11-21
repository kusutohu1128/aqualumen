"""Reuse frozen scoped lifecycle functions with NEW destinations, never old writers."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import water_coast_attribution_lifecycle as reusable
from water_coast_stop_pack import ROOT,OUT,PACK
import report

# Process-local routing only. The sealed imported source file is unchanged.
reusable.OUT=OUT
reusable.PACK=reusable.BUILT_PACK=PACK
reusable.INFO='pack.json'
reusable.RUN='coast-stop-1440-20261006-v1'
GAME=reusable.GAME


def select_refined():
    from water_coast_stop_refine import REFINED_PACK
    reusable.PACK=reusable.BUILT_PACK=REFINED_PACK
    reusable.INFO='pack-refine32.json'
    reusable.RUN='coast-stop-refine32-1440-20261006-v1'


def baseline():
    reusable.closed()
    assert 'All dimensions are saved' in (GAME/'logs/latest.log').read_text()
    backup=Path(tempfile.mkdtemp(prefix='aqualumen-legacy-branch-host-coast-stop-',dir='/home/kusutohu/.cache'))
    for name in ('options.txt','config/iris.properties','config/aqualumen-benchmark.properties'):
        target=backup/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(GAME/name,target)
    value=json.loads(subprocess.check_output(['rtk','proxy','python3','tools/water_legacy_branch_snapshot.py',str(backup)],cwd=ROOT))
    reusable.save('fresh-normal-baseline.json',value)
    shutil.copy2(GAME/'logs/latest.log',OUT/'normal-clean-save-exit.log')
    print('NEW post-save ordinary baseline:',backup)


def compile():
    reusable.closed()
    command=['rtk','proxy','build/glcheck',str(OUT/'diagnostic-source-v1/shaders'),'--compile-only']
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    with (OUT/'native-compile-only.log').open('x') as f:f.write(result.stdout+result.stderr)
    assert result.returncode==0 and 'RTX 3080 Ti' in result.stdout
    print(result.stdout)


def collect(refined=False):
    if refined:select_refined()
    source=GAME/'aqualumen-benchmark/runs'/reusable.RUN
    run,rows=report.load_run(source)
    assert run['run_id']==reusable.RUN and run['pack_name']==reusable.PACK
    assert run['pack_sha256']==json.loads((OUT/reusable.INFO).read_text())['packSHA256']
    assert run['world_id']==reusable.WORLD and run['seed']==308060
    assert run['scenarios']==['coast-day'] and run['expected_resolution']==[2560,1440]
    assert 'RTX 3080 Ti' in run['gl_renderer'] and run['mods']['iris']=='1.8.8+mc1.21.1'
    assert len(rows)==1 and rows[0]['window_focused']
    target=OUT/('iris1440-refine32-run-v1' if refined else 'iris1440-run-v1');assert not target.exists()
    shutil.copytree(source,target)
    assert {str(p.relative_to(source)):reusable.sha(p) for p in source.rglob('*') if p.is_file()}=={
        str(p.relative_to(target)):reusable.sha(p) for p in target.rglob('*') if p.is_file()}
    reusable.save('iris1440-refine32-audit.json' if refined else 'iris1440-audit.json',dict(actualIrisActiveWithoutFallback=True,strictOriginalReportReaderPassed=True,
        worldUUID=run['world_id'],packSHA256=run['pack_sha256'],scenes=rows,
        naturalAppearanceAccepted=False,neutralityProven=False,PNGRawSameFrame=False,fullGoalAchieved=False))
    print('Actual coast stop atlas retained;',rows[0]['frames'],'raw intervals')


def refine_install():
    reusable.closed();select_refined()
    assert set(p.name for p in (GAME/'mods').glob('*.jar'))==set(reusable.PIN)|{'iris-fabric-1.8.8+mc1.21.1.jar','sodium-fabric-0.6.9+mc1.21.1.jar'}
    destination=GAME/'shaderpacks'/reusable.PACK
    with destination.open('xb') as f:f.write((OUT/reusable.PACK).read_bytes())
    assert reusable.sha(destination)==json.loads((OUT/reusable.INFO).read_text())['packSHA256']
    print('NEW single-budget32 TEST pack installed, old pack unchanged')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('baseline','compile','install','test','collect','refine_install','refine_test','refine_collect','restore','normal'))
    action=parser.parse_args().action
    if action=='refine_test':select_refined();reusable.launch('test')
    elif action=='refine_collect':collect(True)
    elif action in ('test','normal'):reusable.launch(action)
    elif action in ('install','restore'):getattr(reusable,action)()
    else:globals()[action]()
