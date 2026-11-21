"""Seal new code/Evidence only; never rewrite a previous manifest."""
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/2026-10-06-water-supported-sources'
assert not (OUT/'SHA256SUMS').exists()
paths=[p for p in OUT.rglob('*') if p.is_file() and p.name!='seal-verification.log']
paths += [ROOT/'shaders/lib/water_supported_sources_test.glsl']
paths += list((ROOT/'tools').glob('water_supported_sources*.py'))
paths += list((ROOT/'tools').glob('water_supported_sources*.cpp'))
paths += list((ROOT/'tools').glob('test_water_supported_sources*.py'))
paths += [ROOT/'tools/water_supported_sampling_cpu.py',ROOT/'tools/test_water_supported_sampling_cpu.py']
assert len(paths)==len(set(paths)) and all(not p.is_symlink() for p in paths)
with (OUT/'SHA256SUMS').open('x') as manifest:
    for p in sorted(paths):
        with p.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
        manifest.write(digest+'  '+str(p.relative_to(ROOT))+'\n')
print('Sealed',len(paths),'new code/Evidence files; verification log intentionally excluded.')
