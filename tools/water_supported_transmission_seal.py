"""Seal completed CPU-reference slice; never overwrite old evidence."""
import hashlib
from pathlib import Path

root=Path(__file__).resolve().parents[1]
out=root/'reports/2026-10-06-water-supported-transmission'
manifest=out/'SHA256SUMS'
assert not manifest.exists() and not manifest.is_symlink()
paths=[p for p in out.rglob('*') if p.is_file()]
paths+=list((root/'tools').glob('*water_supported_transmission*'))
assert all(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root) for p in paths)
with manifest.open('x') as f:
    for p in sorted(set(paths)):
        f.write(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(root))+'\n')
print(f'Sealed {len(set(paths))} files; CPU reference only; no GPU/shader adoption.')
