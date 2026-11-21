"""Owned normal-account handoff; never print private authentication output."""
import json
import os
from pathlib import Path
import subprocess
from water_path_precision_prepare import ROOT, OUT, GAME, execute


def launch():
    assert subprocess.run(['rtk', 'proxy', 'pgrep', '-x', 'java'], stdout=subprocess.DEVNULL).returncode == 1
    baseline = json.loads((OUT/'fresh-normal-baseline.json').read_text())
    execute(['python3','tools/water_legacy_branch_snapshot.py',baseline['backup']], 'normal-final-prelaunch.json')
    assert json.loads((OUT/'normal-final-prelaunch.json').read_text()) == baseline
    private = Path(baseline['backup'])/'launcher-normal-after-pathprecision-private.log'
    descriptor = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    print('STARTING normal0.6/physics0.2, TEST disabled; launcher output private', flush=True)
    command = ['rtk','proxy','flatpak','run','--command=prismrun','org.prismlauncher.PrismLauncher',
               '--launch','Aqualumen Lab','--world','新規ワールド']
    with os.fdopen(descriptor,'wb') as log:
        result = subprocess.run(command,cwd=ROOT,env=dict(os.environ,DISPLAY=':1'),stdout=log,stderr=subprocess.STDOUT)
    print('ORDINARY LAUNCHER EXIT',result.returncode,flush=True)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    launch()
