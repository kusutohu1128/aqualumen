"""Serialize new native refinement jobs; no game or installation mutations."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-06-water-boundary-regression'


def execute(arguments, log):
    with (OUT / log).open('xb') as output:
        completed = subprocess.run(['rtk', 'proxy', *map(str, arguments)], cwd=ROOT,
                                   stdout=output, stderr=subprocess.STDOUT)
    assert completed.returncode == 0, (log, completed.returncode)


def run():
    assert not Path('/proc/3220839').exists()
    assert (OUT / 'main-01-audit.json').is_file()
    outputs = []
    for order in (128, 192):
        target = OUT / f'dense-{order}-main-01'
        execute(['/tmp/aqualumen-supported-reflector-main-20261006-v1',
                 OUT / f'dense-{order}-sources-v1', target], f'dense-{order}-main-01.log')
        outputs.append(target)
        print('FINISHED actual MAIN order', order, flush=True)
    execute(['python3', 'tools/water_boundary_refinement_audit.py', *outputs], 'dense-refinement-audit.json')
    before = json.loads((OUT / 'fresh-normal-baseline.json').read_text())
    execute(['python3', 'tools/water_legacy_branch_snapshot.py', before['backup']], 'normal-after-refinement.json')
    assert json.loads((OUT / 'normal-after-refinement.json').read_text()) == before
    print('PASSED independent refinement input/source audit and preservation; no convergence acceptance')


if __name__ == '__main__':
    run()
