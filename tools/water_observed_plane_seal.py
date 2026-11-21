"""Freeze new CPU diagnostic evidence/tools; ordinary files stay outside seal."""
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-06-water-observed-plane'
TOOLS = ('water_observed_plane_partition.py', 'test_water_observed_plane_partition.py',
    'water_observed_plane_evidence.py', 'water_observed_plane_integral.py',
    'water_observed_plane_run.py', 'water_observed_plane_audit.py',
    'test_water_plane_path_precision.py', 'water_plane_path_red.py',
    'water_observed_plane_finish.py', 'water_observed_plane_seal.py')


def seal():
    assert not (OUT / 'SHA256SUMS').exists()
    assert (OUT / 'checkpoint.json').exists()
    subprocess.run(['rtk', 'proxy', 'git', 'diff', '--check'], cwd=ROOT, check=True)
    for name in ('water-source-boundary', 'water-boundary-regression'):
        subprocess.run(['rtk', 'proxy', 'sha256sum', '--check', '--quiet',
            ROOT / f'reports/2026-10-06-{name}/SHA256SUMS'], cwd=ROOT, check=True)
    diff = subprocess.check_output(['rtk', 'proxy', 'git', 'diff'], cwd=ROOT)
    with (OUT / 'tracked-diff-at-handoff.patch').open('xb') as stream:
        stream.write(diff)
    with (OUT / 'tracked-diff-at-handoff.sha256').open('x') as stream:
        stream.write(hashlib.sha256(diff).hexdigest()+'\n')
    files = [p for p in OUT.rglob('*') if p.is_file()] + [ROOT / 'tools' / name for name in TOOLS]
    assert not any(p.is_symlink() for p in files)
    with (OUT / 'SHA256SUMS').open('x') as stream:
        for path in sorted(set(files)):
            stream.write(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+str(path.relative_to(ROOT))+'\n')
    print('SEALED', len(set(files)), 'CPU/RED records and tools; full goal active')


if __name__ == '__main__':
    seal()
