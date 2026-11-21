"""Seal the completed new RGB core checkpoint without changing old Evidence."""
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/2026-10-06-water-supported-rgb'
manifest=OUT/'SHA256SUMS';assert not manifest.exists() and not manifest.is_symlink()
paths=[p for p in OUT.rglob('*') if p.is_file()]
paths+=[ROOT/p for p in (
    'shaders/lib/water_supported_rgb_test.glsl','tools/water_supported_rgb_cpu.py',
    'tools/test_water_supported_rgb_cpu.py','tools/water_supported_rgb_source.py',
    'tools/water_supported_rgb_main.cpp','tools/water_supported_rgb_audit.py',
    'tools/test_water_supported_rgb_audit.py','tools/water_supported_rgb_finish.py',
    'tools/water_supported_rgb_seal.py')]
assert all(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(ROOT) for p in paths)
with manifest.open('x') as f:
    for p in sorted(set(paths)):
        assert 'launcher-' not in p.name,'Private launcher logs excluded'
        f.write(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(ROOT))+'\n')
print(f'Sealed {len(set(paths))} new files; repository-root-relative paths.')
