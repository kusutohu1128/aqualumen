"""Seal NEW conditional-sampling Evidence and its new tools, no old overwrites."""
import hashlib
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/2026-10-06-water-conditioned-sampling'
TOOLS=('water_supported_conditioned.py','water_supported_rotated.py',
       'test_water_supported_conditioned.py','test_water_supported_rotated.py',
       'water_conditioned_gpu_source.py','water_conditioned_gpu.cpp',
       'water_conditioned_gpu_audit.py','test_water_conditioned_gpu.py',
       'water_conditioned_sources_source.py','water_conditioned_sources_audit.py',
       'test_water_conditioned_sources.py','water_conditioned_finish.py','water_conditioned_seal.py',
       'water_supported_reflector_main.cpp','water_supported_reflector_audit.py')


def seal():
    assert not (OUT/'SHA256SUMS').exists()
    diff=subprocess.check_output(['rtk','proxy','git','diff'],cwd=ROOT)
    with (OUT/'tracked-diff-at-handoff.patch').open('xb') as f:f.write(diff)
    with (OUT/'tracked-diff-at-handoff.sha256').open('x') as f:f.write(hashlib.sha256(diff).hexdigest()+'\n')
    subprocess.run(['rtk','proxy','git','diff','--check'],cwd=ROOT,check=True)
    files=[p for p in OUT.rglob('*') if p.is_file()]+[ROOT/'tools'/n for n in TOOLS]
    files += [ROOT/'shaders/lib/water_conditioned_sampling_test.glsl']
    assert not any(p.is_symlink() for p in files)
    with (OUT/'SHA256SUMS').open('x') as f:
        for path in sorted(set(files)):
            f.write(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+str(path.relative_to(ROOT))+'\n')
    print('SEALED',len(set(files)),'files; full goal remains active')


if __name__=='__main__':seal()
