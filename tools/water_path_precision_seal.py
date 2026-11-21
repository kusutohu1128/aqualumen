"""Seal only NEW precision/current-Iris records/tools, never mutable live files."""
import hashlib
from pathlib import Path
import subprocess
from water_path_precision_prepare import ROOT, OUT


def seal():
    assert (OUT/'checkpoint.json').exists() and not (OUT/'SHA256SUMS').exists()
    subprocess.run(['rtk','proxy','git','diff','--check'],cwd=ROOT,check=True)
    for role in ('water-observed-plane','water-source-boundary','water-boundary-regression'):
        subprocess.run(['rtk','proxy','sha256sum','--check','--quiet',ROOT/f'reports/2026-10-06-{role}/SHA256SUMS'],cwd=ROOT,check=True)
    diff = subprocess.check_output(['rtk','proxy','git','diff'],cwd=ROOT)
    with (OUT/'tracked-diff-at-handoff.patch').open('xb') as f:
        f.write(diff)
    files = [p for p in OUT.rglob('*') if p.is_file()] + list((ROOT/'tools').glob('water_path_precision_*.py'))
    assert not any(p.is_symlink() for p in files)
    with (OUT/'SHA256SUMS').open('x') as f:
        for path in sorted(set(files)):
            f.write(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+str(path.relative_to(ROOT))+'\n')
    print('SEALED',len(set(files)),'NEW native/current-Iris/motion records and tools; full goal ACTIVE')


if __name__ == '__main__':
    seal()
