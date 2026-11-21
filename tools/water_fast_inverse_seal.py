"""Seal only new fast-inverse Evidence/tools, never mutable ordinary assets."""
import hashlib
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/2026-10-06-water-fast-inverse'
TOOLS=('water_fast_inverse.py','water_fast_inverse_audit.py',
    'water_fast_inverse_main_source.py','water_fast_inverse_source.py',
    'water_fast_inverse_timing.cpp','water_fast_inverse_timing_audit.py',
    'test_water_fast_inverse.py','water_supported_probability_rule.py',
    'test_water_supported_probability_rule.py','test_water_probability_main.py',
    'water_probability_main_source.py','water_probability_main_audit.py',
    'water_probability_timing.cpp','water_probability_timing_audit.py',
    'water_fast_inverse_finish.py','water_fast_inverse_seal.py')


def seal():
    assert not (OUT/'SHA256SUMS').exists()
    subprocess.run(['rtk','proxy','git','diff','--check'],cwd=ROOT,check=True)
    diff=subprocess.check_output(['rtk','proxy','git','diff'],cwd=ROOT)
    with (OUT/'tracked-diff-at-handoff.patch').open('xb') as f:f.write(diff)
    with (OUT/'tracked-diff-at-handoff.sha256').open('x') as f:f.write(hashlib.sha256(diff).hexdigest()+'\n')
    binaries=('/tmp/aqualumen-probability-timing-20261006-v2',
        '/tmp/aqualumen-fast-inverse-timing-20261006-v1',
        '/tmp/aqualumen-supported-sources-main-20261006-v3',
        '/tmp/aqualumen-supported-reflector-main-20261006-v1')
    with (OUT/'native-binaries.sha256').open('x') as f:
        for name in binaries:
            f.write(hashlib.sha256(Path(name).read_bytes()).hexdigest()+'  '+name+'\n')
    files=[p for p in OUT.rglob('*') if p.is_file()]+[ROOT/'tools'/n for n in TOOLS]
    files.append(ROOT/'shaders/lib/water_conditioned_inverse_test.glsl')
    assert not any(p.is_symlink() for p in files)
    with (OUT/'SHA256SUMS').open('x') as f:
        for p in sorted(set(files)):
            f.write(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(ROOT))+'\n')
    print('SEALED',len(set(files)),'files; no full-goal acceptance')


if __name__=='__main__':seal()
