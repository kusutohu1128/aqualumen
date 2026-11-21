"""Recover normal assets/config bytes only after owned TEST client exits."""
import json
from pathlib import Path
import shutil
import subprocess
from water_path_precision_prepare import ROOT, OUT, GAME, execute
from water_path_precision_iris_setup import PIN, sha


def restore():
    assert subprocess.run(['rtk', 'proxy', 'pgrep', '-x', 'java'], stdout=subprocess.DEVNULL).returncode == 1
    baseline = json.loads((OUT / 'fresh-normal-baseline.json').read_text())
    backup = Path(baseline['backup'])
    assert 'All dimensions are saved' in (GAME / 'logs/latest.log').read_text()
    assert not (GAME / 'aqualumen-benchmark/request.properties').exists()
    assert not (GAME / 'aqualumen-benchmark/opaque-fixture-journal.json').exists()
    assert not (GAME / 'aqualumen-benchmark/opaque-test-journal.json').exists()
    # Recoverable moves, not deletion. Nothing touches either save tree.
    retained = backup / 'pathprecision-disabled-test-artifacts'
    retained.mkdir(exist_ok=False)
    for name, digest in PIN.items():
        source = GAME / 'mods' / name
        assert sha(source) == digest
        shutil.move(source, retained / name)
    marker = GAME / 'config/aqualumen-benchmark.enabled'
    assert marker.exists()
    shutil.move(marker, retained / marker.name)
    physics = GAME / 'mods/aqualumen-physics-0.2.0.jar'
    assert not physics.exists()
    assert sha(backup / physics.name) == baseline['activeMods'][physics.name]
    shutil.move(backup / physics.name, physics)
    for name in baseline['configSHA256']:
        assert sha(backup / name) == baseline['configSHA256'][name]
        shutil.copy2(backup / name, GAME / name)
    execute(['python3', 'tools/water_legacy_branch_snapshot.py', backup], 'normal-after-iris.json')
    assert json.loads((OUT/'normal-after-iris.json').read_text()) == baseline
    print('Restored normal0.6/physics0.2 config/assets; TEST markers/Mods recoverably disabled, ordinary save exact')


if __name__ == '__main__':
    restore()
