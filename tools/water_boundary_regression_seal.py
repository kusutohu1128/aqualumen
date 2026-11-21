"""Seal this new regression/refinement Evidence and tools, never ordinary saves."""
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-06-water-boundary-regression'
TOOLS = ('water_boundary_regression_run.py', 'water_boundary_dense_refinement.py',
         'water_boundary_refinement_audit.py', 'water_boundary_refinement_run.py',
         'water_boundary_regression_launch.py', 'water_boundary_regression_finish.py',
         'water_boundary_regression_seal.py')


def seal():
    assert not (OUT / 'SHA256SUMS').exists()
    assert (OUT / 'checkpoint.json').is_file()
    subprocess.run(['rtk', 'proxy', 'git', 'diff', '--check'], cwd=ROOT, check=True)
    prior = ROOT / 'reports/2026-10-06-water-source-boundary/SHA256SUMS'
    subprocess.run(['rtk', 'proxy', 'sha256sum', '--check', '--quiet', prior], cwd=ROOT, check=True)
    diff = subprocess.check_output(['rtk', 'proxy', 'git', 'diff'], cwd=ROOT)
    with (OUT / 'tracked-diff-at-handoff.patch').open('xb') as output:
        output.write(diff)
    with (OUT / 'tracked-diff-at-handoff.sha256').open('x') as output:
        output.write(hashlib.sha256(diff).hexdigest() + '\n')
    with (OUT / 'native-binaries.sha256').open('x') as output:
        for name in ('/tmp/aqualumen-supported-sources-main-20261006-v3',
                     '/tmp/aqualumen-supported-reflector-main-20261006-v1'):
            output.write(hashlib.sha256(Path(name).read_bytes()).hexdigest() + '  ' + name + '\n')
    files = [p for p in OUT.rglob('*') if p.is_file()] + [ROOT / 'tools' / n for n in TOOLS]
    assert not any(p.is_symlink() for p in files)
    with (OUT / 'SHA256SUMS').open('x') as output:
        for path in sorted(set(files)):
            output.write(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + str(path.relative_to(ROOT)) + '\n')
    print('SEALED', len(set(files)), 'files; full goal remains active')


if __name__ == '__main__':
    seal()
