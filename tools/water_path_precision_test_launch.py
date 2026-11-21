"""Owned UUID-guarded TEST client, private authentication output."""
import json
import os
from pathlib import Path
import subprocess
from water_path_precision_prepare import ROOT, OUT, GAME
from water_path_precision_iris_setup import PACK, PIN, sha


def launch():
    assert subprocess.run(['rtk', 'proxy', 'pgrep', '-x', 'java'], stdout=subprocess.DEVNULL).returncode == 1
    baseline = json.loads((OUT / 'fresh-normal-baseline.json').read_text())
    receipt = json.loads((OUT / 'iris-setup.json').read_text())
    assert sha(GAME / 'shaderpacks' / PACK) == receipt['packSHA256']
    assert 'shaderPack='+PACK in (GAME / 'config/iris.properties').read_text()
    assert set(p.name for p in (GAME/'mods').glob('*.jar')) == set(PIN) | {'iris-fabric-1.8.8+mc1.21.1.jar', 'sodium-fabric-0.6.9+mc1.21.1.jar'}
    for name, digest in PIN.items():
        assert sha(GAME/'mods'/name) == digest
    assert (GAME / 'config/aqualumen-benchmark.enabled').exists()
    for name in baseline['instrumentationEntryPointsAbsent'][1:]:
        assert not (GAME/'config'/name).exists()
    private = Path(baseline['backup']) / 'launcher-pathprecision-test-private.log'
    descriptor = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    command = ['rtk', 'proxy', 'flatpak', 'run', '--command=prismrun', 'org.prismlauncher.PrismLauncher',
               '--launch', 'Aqualumen Lab', '--world', 'AqualumenNaturalV2']
    print('STARTING pathprecision TEST client; output private', flush=True)
    with os.fdopen(descriptor, 'wb') as log:
        result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, DISPLAY=':1'), stdout=log, stderr=subprocess.STDOUT)
    print('TEST LAUNCHER EXIT', result.returncode, flush=True)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    launch()
