import json
import os
from pathlib import Path
import shutil
import sys

root = Path('/home/kusutohu/repos/aqualumen')
sys.path.insert(0, str(root / 'tools'))
from land_shadow_run import execute, save, sha

report = root / 'reports/2026-10-23-land-shadows'
out = report / 'motion2-checks'
out.mkdir(exist_ok=False)
for name in ('land_shadow_native.cpp', 'land_shadow_motion_native.cpp'):
    shutil.copyfile(root / 'tools' / name, out / name)
binary = out / 'land-shadow-motion'
built = execute(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                 out / 'land_shadow_motion_native.cpp', '-o', binary, '-lepoxy', '-lEGL'], out, 'build')
assert built.returncode == 0, 'Motion build failed; preserve output'
cpu = execute([binary, '--cpu-self-test'], out, 'cpu-self-test')
assert cpu.returncode == 0
environment = dict(os.environ, __EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/10_nvidia.json')
shader = report / 'candidate2-checks/pack/shaders'
results = {}
for algorithm in ('legacy', 'land'):
    run = execute([binary, shader, algorithm, out / algorithm], out, algorithm, environment)
    data = json.loads((out / algorithm / 'RESULT.json').read_text())
    results[algorithm] = dict(exitCode=run.returncode, result=data)
    assert 'NVIDIA GeForce RTX 3080 Ti' in data['renderer'] and data['endpointContrastPassed']
    assert run.returncode == 0
data = results['land']['result']
passed = data['monotonicPassed'] and data['maximumStepPassed']
save(out / 'receipt.json', dict(exitCode=results['land']['exitCode'], passed=passed,
     renderer=data['renderer'], packSHA256=sha(report / 'Aqualumen-LandShadows-Preview-2026-10-23.zip'),
     binarySHA256=sha(binary), sourcePins={name: sha(out / name) for name in ('land_shadow_native.cpp', 'land_shadow_motion_native.cpp')},
     result=dict(path=str(out / 'land/RESULT.json'), sha256=sha(out / 'land/RESULT.json')),
     control=results['legacy']['result'], actualMinecraft=False, performanceMeasured=False))
assert passed, 'Motion target failed; do not widen its declared budget'
print('Candidate fixed-light subtexel sweep passed; no dynamic Sun or Minecraft acceptance.')
