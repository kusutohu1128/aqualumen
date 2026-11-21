"""Retain actual optical precision RED before changing any production tracer."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-06-water-observed-plane'
with (OUT / 'actual-main-path-precision-red.log').open('xb') as output:
    result = subprocess.run(['rtk', 'proxy', 'python3', '-m', 'unittest', 'discover',
        '-s', 'tools', '-p', 'test_water_plane_path_precision.py'], cwd=ROOT,
        stdout=output, stderr=subprocess.STDOUT)
assert result.returncode == 1
print('RETAINED actual original-MAIN path/Beer optical RED; production unchanged')
