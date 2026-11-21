"""NEW current-production TEST ZIP and reversible Lab-only Mod installation."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
from water_path_precision_prepare import ROOT, OUT, GAME, tracer

PACK = 'Aqualumen-PathPrecision-refine12-TEST-v1.zip'
BENCH = 'aqualumen-benchmark-0.3.9-projection-guards.jar'
PHYSICS = 'aqualumen-physics-0.3.0.jar'
PIN = {BENCH: 'ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29',
       PHYSICS: '958a34a9195f260921a43ea296a4968ef691339aac2b038129702d4ca572a310'}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def setup():
    assert subprocess.run(['rtk', 'proxy', 'pgrep', '-x', 'java'], stdout=subprocess.DEVNULL).returncode == 1
    assert (OUT / 'production-near-first-01/BLACK-FIRST-SUMMARY.txt').read_text().count('behavioralPass=1') == 1
    assert '11 program pairs compiled and linked' in (OUT / 'production-make-check.log').read_text()
    assert tracer((ROOT / 'shaders/gbuffers_water.fsh').read_text()) == tracer((OUT / 'refine12-observer-v1/baseline.fsh').read_text())
    baseline = json.loads((OUT / 'fresh-normal-baseline.json').read_text())
    result = subprocess.check_output(['rtk', 'proxy', 'python3', 'tools/water_legacy_branch_snapshot.py', baseline['backup']], cwd=ROOT)
    assert json.loads(result) == baseline
    with (OUT / 'normal-before-iris.json').open('xb') as f:
        f.write(result)
    marker = dict(line.split('=', 1) for line in (GAME / 'saves/AqualumenNaturalV2/aqualumen-world.properties').read_text().splitlines())
    assert marker == dict(schema='2', world_id='b22dbccb-2970-41e6-847f-f183b1ec923d', seed='308060',
                          generator='minecraft:noise/overworld', minecraft='1.21.1')
    for name in ('request.properties', 'opaque-test-journal.json', 'opaque-fixture-journal.json'):
        assert not (GAME / 'aqualumen-benchmark' / name).exists()
    destination = OUT / PACK
    expected = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in sorted([*(ROOT/'shaders').rglob('*'), ROOT/'LICENSE']) if p.is_file()}
    with destination.open('xb') as f, ZipFile(f, 'w', compression=ZIP_DEFLATED) as z:
        for name, blob in expected.items():
            entry = ZipInfo(name, (2026, 10, 6, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            z.writestr(entry, blob)
    with ZipFile(destination) as z:
        assert {n: z.read(n) for n in z.namelist()} == expected
    installed = GAME / 'shaderpacks' / PACK
    with installed.open('xb') as f:
        f.write(destination.read_bytes())
    backup = Path(baseline['backup'])
    old = GAME / 'mods/aqualumen-physics-0.2.0.jar'
    assert sha(old) == baseline['activeMods'][old.name]
    assert not (backup / old.name).exists()
    for name in (BENCH, PHYSICS):
        assert not (GAME / 'mods' / name).exists()
    with ZipFile(ROOT / 'reports/2026-10-06-water-legacy-branch/actual-test-mods.zip') as z:
        blobs = {name: z.read(name) for name in (BENCH, PHYSICS)}
    assert {n: hashlib.sha256(v).hexdigest() for n, v in blobs.items()} == PIN
    shutil.move(old, backup / old.name)
    for name, blob in blobs.items():
        with (GAME / 'mods' / name).open('xb') as f:
            f.write(blob)
    receipt = dict(schema='aqualumen-path-precision-iris-setup-v1', pack=PACK, packSHA256=sha(installed),
                   packedSourcesExact=True, sourceFunctionSHA256=hashlib.sha256(tracer(expected['shaders/gbuffers_water.fsh'].decode()).encode()).hexdigest(),
                   testMods=PIN, testWorld='AqualumenNaturalV2', testWorldUUID=marker['world_id'],
                   ordinarySaveModified=False, normalPhysicsRecoverablyMovedTo=str(backup/old.name),
                   configurationPrepared=False, actualIrisAccepted=False, fullGoalAchieved=False)
    with (OUT / 'iris-setup.json').open('x') as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == '__main__':
    setup()
