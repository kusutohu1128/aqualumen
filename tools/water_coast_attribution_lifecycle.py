"""New reversible Lab lifecycle. Never restores a world or writes old evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile
import report
from water_coast_attribution_pack import ROOT, OUT, PACK as BUILT_PACK, INFO

# Pinned passive observer accepts only this TEST namespace; do not weaken guards.
PACK = 'Aqualumen-ShoreProbe-world-CoastAttribution-v2.zip'

GAME = Path('/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft')
RUN = 'coast-attribution-rolepair-1440-20261006-v1'
WORLD = 'b22dbccb-2970-41e6-847f-f183b1ec923d'
PIN = {'aqualumen-benchmark-0.3.9-projection-guards.jar': 'ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29',
       'aqualumen-physics-0.3.0.jar': '958a34a9195f260921a43ea296a4968ef691339aac2b038129702d4ca572a310'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (OUT/name).open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True)


def closed():
    assert subprocess.run(['rtk','proxy','pgrep','-x','java'], stdout=subprocess.DEVNULL).returncode == 1


def baseline():
    closed()
    assert 'All dimensions are saved' in (GAME/'logs/latest.log').read_text()
    backup = Path(tempfile.mkdtemp(prefix='aqualumen-legacy-branch-host-coast-attribution-', dir='/home/kusutohu/.cache'))
    for name in ('options.txt','config/iris.properties','config/aqualumen-benchmark.properties'):
        target = backup/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(GAME/name, target)
    result = subprocess.check_output(['rtk','proxy','python3','tools/water_legacy_branch_snapshot.py',str(backup)], cwd=ROOT)
    value = json.loads(result)
    save('fresh-normal-baseline.json', value)
    shutil.copy2(GAME/'logs/latest.log', OUT/'normal-clean-save-exit.log')
    for stamp in ('14.06.13','14.07.01','14.07.16','14.07.29','14.07.40','14.08.22'):
        source = GAME/'screenshots'/f'2026-10-06_{stamp}.png'
        shutil.copy2(source, OUT/source.name)
    print('Fresh post-save baseline recorded:', backup)


def install():
    closed()
    value = json.loads((OUT/'fresh-normal-baseline.json').read_text())
    packet = json.loads((OUT/INFO).read_text())
    assert sha(OUT/BUILT_PACK) == packet['packSHA256']
    marker = dict(line.split('=',1) for line in (GAME/'saves/AqualumenNaturalV2/aqualumen-world.properties').read_text().splitlines())
    assert marker == dict(schema='2',world_id=WORLD,seed='308060',generator='minecraft:noise/overworld',minecraft='1.21.1')
    for name in ('request.properties','opaque-test-journal.json','opaque-fixture-journal.json'):
        assert not (GAME/'aqualumen-benchmark'/name).exists()
    old = GAME/'mods/aqualumen-physics-0.2.0.jar'
    assert sha(old) == value['activeMods'][old.name]
    backup = Path(value['backup'])
    assert not (backup/old.name).exists()
    destination = GAME/'shaderpacks'/BUILT_PACK
    assert not destination.exists()
    with destination.open('xb') as f:
        f.write((OUT/BUILT_PACK).read_bytes())
    with ZipFile(ROOT/'reports/2026-10-06-water-legacy-branch/actual-test-mods.zip') as z:
        blobs = {n:z.read(n) for n in PIN}
    assert {n:hashlib.sha256(b).hexdigest() for n,b in blobs.items()} == PIN
    assert not any((GAME/'mods'/n).exists() for n in PIN)
    shutil.move(old, backup/old.name)
    for name, blob in blobs.items():
        with (GAME/'mods'/name).open('xb') as f:
            f.write(blob)
    save('install.json', dict(pack=BUILT_PACK,packSHA256=sha(destination),testMods=PIN,
        worldUUID=WORLD,normalPhysicsMovedTo=str(backup/old.name),ordinarySaveModified=False))
    print('Installed isolated TEST assets; configuration not yet changed')


def launch(kind):
    closed()
    value = json.loads((OUT/'fresh-normal-baseline.json').read_text())
    backup = Path(value['backup'])
    if kind == 'test':
        assert sha(GAME/'shaderpacks'/PACK) == json.loads((OUT/INFO).read_text())['packSHA256']
        assert 'shaderPack='+PACK in (GAME/'config/iris.properties').read_text()
        assert (GAME/'config/aqualumen-benchmark.enabled').exists()
        assert set(p.name for p in (GAME/'mods').glob('*.jar')) == set(PIN)|{'iris-fabric-1.8.8+mc1.21.1.jar','sodium-fabric-0.6.9+mc1.21.1.jar'}
        for name,digest in PIN.items():
            assert sha(GAME/'mods'/name) == digest
        world = 'AqualumenNaturalV2'
    else:
        observed = json.loads(subprocess.check_output(['rtk','proxy','python3','tools/water_legacy_branch_snapshot.py',str(backup)],cwd=ROOT))
        assert observed == value
        save('normal-final-prelaunch.json', observed)
        world = '新規ワールド'
    private = backup/f'launcher-coast-attribution-{kind}-{PACK}-private.log'
    descriptor = os.open(private,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    print('STARTING',kind,'client; authentication output private',flush=True)
    command = ['rtk','proxy','flatpak','run','--command=prismrun','org.prismlauncher.PrismLauncher',
        '--launch','Aqualumen Lab','--world',world]
    with os.fdopen(descriptor,'wb') as log:
        result = subprocess.run(command,cwd=ROOT,env=dict(os.environ,DISPLAY=':1'),stdout=log,stderr=subprocess.STDOUT)
    print(kind.upper(),'LAUNCHER EXIT',result.returncode,flush=True)
    raise SystemExit(result.returncode)


def collect():
    original = GAME/'aqualumen-benchmark/runs'/RUN
    run,rows = report.load_run(original)
    assert run['run_id'] == RUN and run['pack_name'] == PACK
    assert run['pack_sha256'] == json.loads((OUT/INFO).read_text())['packSHA256']
    assert run['world_id'] == WORLD and run['seed'] == 308060
    assert run['scenarios'] == ['coast-day'] and run['expected_resolution'] == [2560,1440]
    assert 'RTX 3080 Ti' in run['gl_renderer'] and run['mods']['iris'] == '1.8.8+mc1.21.1'
    assert len(rows) == 1 and rows[0]['window_focused']
    target = OUT/'iris1440-rolepair-run-v1'
    assert not target.exists()
    shutil.copytree(original,target)
    assert {str(p.relative_to(original)):sha(p) for p in original.rglob('*') if p.is_file()} == {
        str(p.relative_to(target)):sha(p) for p in target.rglob('*') if p.is_file()}
    save('iris1440-rolepair-audit.json',dict(actualIrisActiveWithoutFallback=True,strictOriginalReportReaderPassed=True,
        worldUUID=WORLD,packSHA256=run['pack_sha256'],scenes=rows,
        atlasClockSeconds=120.0,fullNaturalAppearanceAccepted=False,neutralityProven=False,
        PNGAndSelectedRawSameFrameProven=False,fullGoalAchieved=False))
    print('Actual NVIDIA/Iris coast atlas and raw timings archived;',rows[0]['frames'],'intervals')


def restore():
    closed()
    value = json.loads((OUT/'fresh-normal-baseline.json').read_text())
    backup = Path(value['backup'])
    assert 'All dimensions are saved' in (GAME/'logs/latest.log').read_text()
    for name in ('request.properties','opaque-fixture-journal.json','opaque-test-journal.json'):
        assert not (GAME/'aqualumen-benchmark'/name).exists()
    shutil.copy2(GAME/'logs/latest.log',OUT/'test-clean-save-exit.log')
    retained = backup/'coast-attribution-disabled-test-artifacts'
    retained.mkdir(exist_ok=False)
    for name,digest in PIN.items():
        assert sha(GAME/'mods'/name) == digest
        shutil.move(GAME/'mods'/name,retained/name)
    for name in value['instrumentationEntryPointsAbsent']:
        source = GAME/'config'/name
        if source.exists():
            shutil.move(source,retained/name)
    old = GAME/'mods/aqualumen-physics-0.2.0.jar'
    assert not old.exists() and sha(backup/old.name) == value['activeMods'][old.name]
    shutil.move(backup/old.name,old)
    for name,digest in value['configSHA256'].items():
        assert sha(backup/name) == digest
        shutil.copy2(backup/name,GAME/name)
    observed = json.loads(subprocess.check_output(['rtk','proxy','python3','tools/water_legacy_branch_snapshot.py',str(backup)],cwd=ROOT))
    assert observed == value
    save('normal-restored.json',observed)
    print('Normal0.6/physics0.2 restored; TEST disabled; ordinary saved files exact; no save restore')


def corrected_pack():
    closed()
    assert set(p.name for p in (GAME/'mods').glob('*.jar')) == set(PIN)|{'iris-fabric-1.8.8+mc1.21.1.jar','sodium-fabric-0.6.9+mc1.21.1.jar'}
    destination=GAME/'shaderpacks'/BUILT_PACK
    with destination.open('xb') as f:
        f.write((OUT/BUILT_PACK).read_bytes())
    assert sha(destination) == json.loads((OUT/INFO).read_text())['packSHA256']
    print('Corrected NEW TEST pack installed; failed v1 remains retained')


def alias_pack():
    closed()
    assert 'All dimensions are saved' in (GAME/'logs/latest.log').read_text()
    shutil.copy2(GAME/'logs/latest.log',OUT/'iris-v2-clean-save-exit.log')
    destination=GAME/'shaderpacks'/PACK
    with destination.open('xb') as f:
        f.write((OUT/BUILT_PACK).read_bytes())
    assert sha(destination) == json.loads((OUT/INFO).read_text())['packSHA256']
    save('observer-namespace-alias.json',dict(originalPack=BUILT_PACK,observerPack=PACK,
        exactSameZIPBytes=True,sha256=sha(destination),guardWeakened=False,
        reason='Pinned ShoreRuntimeObserver accepts only Aqualumen-ShoreProbe-world-* namespace'))
    print('Exact-byte TEST namespace alias installed; all observer/world guards retained')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('baseline','install','corrected_pack','alias_pack','test','collect','restore','normal'))
    action=parser.parse_args().action
    if action in ('test','normal'):
        launch(action)
    else:
        globals()[action]()
