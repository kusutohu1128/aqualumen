"""Owned ordinary normal-account launch; private authentication log stays private."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-06-water-boundary-regression'


def launch():
    assert not Path('/proc/3220839').exists()
    assert (OUT / 'dense-refinement-audit.json').is_file()
    baseline = json.loads((OUT / 'fresh-normal-baseline.json').read_text())
    result = subprocess.run(['rtk', 'proxy', 'python3', 'tools/water_legacy_branch_snapshot.py', baseline['backup']],
                            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    assert json.loads(result.stdout) == baseline
    with (OUT / 'normal-final-prelaunch.json').open('xb') as output:
        output.write(result.stdout)
    private = Path(baseline['backup']) / 'launcher-ordinary-private.log'
    descriptor = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    command = ['rtk', 'proxy', 'flatpak', 'run', '--command=prismrun',
               'org.prismlauncher.PrismLauncher', '--launch', 'Aqualumen Lab',
               '--world', '新規ワールド']
    env = dict(os.environ, DISPLAY=':1')
    print('STARTING normal0.6/physics0.2, TEST disabled; launcher output private', flush=True)
    with os.fdopen(descriptor, 'wb') as log:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    print('ORDINARY LAUNCHER EXIT', result.returncode, flush=True)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    launch()
