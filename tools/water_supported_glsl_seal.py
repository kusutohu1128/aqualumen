"""Seal only this new checkpoint's Evidence/tools, excluding private logs."""
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/2026-10-06-water-supported-glsl'
manifest=OUT/'SHA256SUMS'
assert not manifest.exists() and not manifest.is_symlink()
paths=[p for p in OUT.rglob('*') if p.is_file()]
paths+=[ROOT/p for p in (
    'shaders/lib/water_supported_transmission_test.glsl',
    'tools/water_supported_main_red.cpp','tools/water_supported_main_red_audit.py',
    'tools/water_supported_glsl_source.py','tools/water_supported_glsl_gpu.cpp',
    'tools/water_supported_glsl_audit.py','tools/test_water_supported_glsl.py',
    'tools/water_supported_glsl_finish.py','tools/water_supported_glsl_seal.py')]
assert all(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(ROOT) for p in paths)
with manifest.open('x') as f:
    for p in sorted(set(paths)):
        assert 'launcher-' not in p.name,'Private launcher log must not be archived'
        f.write(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(ROOT))+'\n')
print(f'Sealed {len(set(paths))} files; paths are repository-root relative.')
