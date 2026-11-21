"""Seal this completed evidence slice and its new tools without overwriting."""
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/2026-10-06-water-legacy-branch'
manifest=OUT/'SHA256SUMS'
assert not manifest.exists() and not manifest.is_symlink()
paths=[p for p in OUT.rglob('*') if p.is_file()]
paths+=list((ROOT/'tools').glob('*water_legacy_branch*'))
assert all(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(ROOT) for p in paths)
paths=sorted(set(paths))
with manifest.open('x') as f:
    for p in paths:
        assert 'launcher-' not in p.name,'Private launcher logs excluded'
        f.write(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(ROOT))+'\n')
print(f'Sealed {len(paths)} files; repository-root-relative paths; no private launcher logs.')
