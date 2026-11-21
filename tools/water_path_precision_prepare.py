"""NEW-only one-variable hit precision experiment, no save/config restoration."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import water_source_boundary_source as passive

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-06-water-path-precision'
OLD = ROOT / 'reports/2026-10-06-water-source-boundary/fixed-observer-12-v1'
GAME = Path('/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft')
BINARY = Path('/tmp/aqualumen-source-boundary-probe-20261006-v1')


def execute(command, name):
    with (OUT / name).open('xb') as log:
        result = subprocess.run(['rtk', 'proxy', *map(str, command)], cwd=ROOT,
                                stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError((name, result.returncode))


def tracer(text):
    start = text.index('vec4 reflectionTrace(')
    opening = text.index('{', start)
    level, end = 1, opening + 1
    while level:
        level += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def run():
    assert not Path('/proc/3229665').exists()
    assert subprocess.run(['rtk', 'proxy', 'pgrep', '-x', 'java'],
                          stdout=subprocess.DEVNULL).returncode == 1
    for role in ('water-observed-plane', 'water-source-boundary', 'water-boundary-regression'):
        execute(['sha256sum', '--check', '--quiet', ROOT / f'reports/2026-10-06-{role}/SHA256SUMS'],
                f'old-{role}-seal-before.log')
    clean_exit = (GAME / 'logs/latest.log').read_text()
    assert 'All dimensions are saved' in clean_exit
    backup = Path(tempfile.mkdtemp(prefix='aqualumen-legacy-branch-host-pathprecision-', dir='/home/kusutohu/.cache'))
    (backup / 'config').mkdir()
    for name in ('options.txt', 'config/iris.properties', 'config/aqualumen-benchmark.properties'):
        shutil.copy2(GAME / name, backup / name)
    execute(['python3', 'tools/water_legacy_branch_snapshot.py', backup], 'fresh-normal-baseline.json')
    shutil.copy2(GAME / 'logs/latest.log', OUT / 'ordinary-clean-exit.log')
    for name, role in (('2026-10-06_13.49.02.png', 'savequit-focus.png'),
                       ('2026-10-06_13.49.22.png', 'title-quit-focus.png')):
        shutil.copy2(GAME / 'screenshots' / name, OUT / role)
    digest = hashlib.sha256(BINARY.read_bytes()).hexdigest()
    assert digest + '  ' + str(BINARY) in (ROOT / 'reports/2026-10-06-water-source-boundary/native-binaries.sha256').read_text()
    with (OUT / 'native-binary.sha256').open('x') as f:
        f.write(digest + '  ' + str(BINARY) + '\n')
    original = (OLD / 'baseline.fsh').read_text()
    assert tracer(original) == tracer((ROOT / 'shaders/gbuffers_water.fsh').read_text())
    anchor = 'for (int refine=0;refine<4;++refine)'
    assert original.count(anchor) == 1
    fixed = original.replace(anchor, 'for (int refine=0;refine<12;++refine)', 1)
    sources = OUT / 'refine12-observer-v1'
    sources.mkdir(exist_ok=False)
    for name, value in (('baseline.fsh', fixed), ('observer.fsh', passive.observe(fixed))):
        with (sources / name).open('x') as f:
            f.write(value)
    for name in [f'geometry-stage{i}.glsl' for i in range(3)] + ['probability-rule.json']:
        shutil.copy2(OLD / name, sources / name)
    print('Prepared NEW post-save baseline and single-variable refine12 TEST sources')


if __name__ == '__main__':
    run()
