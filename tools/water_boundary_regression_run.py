"""New affected regression evidence; no ordinary save restoration/GL concurrency."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-06-water-boundary-regression'
GAME = Path('/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft')
SOURCE = ROOT / 'reports/2026-10-06-water-source-boundary/fixed-ten-case-sources-v1'
BINARY = Path('/tmp/aqualumen-supported-sources-main-20261006-v3')


def execute(command, name):
    with (OUT / name).open('xb') as log:
        result = subprocess.run(['rtk', 'proxy', *map(str, command)], cwd=ROOT,
                                stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError((name, result.returncode))


def run():
    assert not Path('/proc/3220839').exists()
    assert not (OUT / 'fresh-normal-baseline.json').exists()
    seal = ROOT / 'reports/2026-10-06-water-source-boundary/SHA256SUMS'
    execute(['sha256sum', '--check', '--quiet', seal], 'old-boundary-seal-before.log')
    backup = Path(tempfile.mkdtemp(prefix='aqualumen-legacy-branch-host-boundaryregression-', dir='/home/kusutohu/.cache'))
    (backup / 'config').mkdir()
    for name in ('options.txt', 'config/iris.properties', 'config/aqualumen-benchmark.properties'):
        shutil.copy2(GAME / name, backup / name)
    execute(['python3', 'tools/water_legacy_branch_snapshot.py', backup], 'fresh-normal-baseline.json')
    shutil.copy2(GAME / 'logs/latest.log', OUT / 'ordinary-clean-exit.log')
    for name, role in (('2026-10-06_13.28.52.png', 'savequit-focus.png'),
                       ('2026-10-06_13.29.09.png', 'title-quit-focus.png')):
        shutil.copy2(GAME / 'screenshots' / name, OUT / role)
    old_binary = json.loads((ROOT / 'reports/2026-10-06-water-fast-inverse/checkpoint.json').read_text())
    assert not old_binary['fullGoalAchieved']
    binary_hash = hashlib.sha256(BINARY.read_bytes()).hexdigest()
    sealed_binaries = (ROOT / 'reports/2026-10-06-water-source-boundary/native-binaries.sha256').read_text()
    assert binary_hash + '  ' + str(BINARY) in sealed_binaries
    execute([BINARY, SOURCE, OUT / 'main-01'], 'main-01.log')
    execute(['python3', 'tools/water_probability_main_audit.py', OUT / 'main-01', SOURCE], 'main-01-audit.json')
    execute(['python3', 'tools/water_legacy_branch_snapshot.py', backup], 'normal-prelaunch.json')
    before = json.loads((OUT / 'fresh-normal-baseline.json').read_text())
    after = json.loads((OUT / 'normal-prelaunch.json').read_text())
    assert before == after
    execute(['sha256sum', '--check', '--quiet', seal], 'old-boundary-seal-after.log')
    print('PASSED affected ten-case MAIN and independent dense/source audit; normal baseline unchanged')


if __name__ == '__main__':
    run()
