"""Retain CPU diagnostic test output without overwriting old Evidence."""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-06-water-observed-plane'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('red', 'green', 'final', 'fade-red', 'fade-green', 'fade-final'))
    args = parser.parse_args()
    with (OUT / f'partition-{args.stage}.log').open('xb') as log:
        result = subprocess.run(['rtk', 'proxy', 'python3', '-m', 'unittest', 'discover',
            '-s', 'tools', '-p', 'test_water_observed_plane_partition.py'],
            cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    print(args.stage, 'actual test exit', result.returncode)
    assert result.returncode == (1 if args.stage.endswith('red') else 0)
