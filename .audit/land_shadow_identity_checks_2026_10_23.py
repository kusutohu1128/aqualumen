import json
import os
from pathlib import Path
import shutil
import sys
from zipfile import ZipFile

root = Path('/home/kusutohu/repos/aqualumen')
sys.path.insert(0, str(root / 'tools'))
from land_shadow_run import execute, save, sha

report = root / 'reports/2026-10-23-land-shadows'
out = report / 'identity-checks'
out.mkdir(exist_ok=False)
archive = report / 'identity.zip'
assert sha(archive) == 'a3473f5eda0b1f47e39b7cec3a256c9534b14e117936e7a58130d60b1933eb3d'
for name in ('shaders/lib/land_lighting.glsl', 'shaders/lib/land_shadows.glsl',
             'tools/land_shadow_pack.py', 'tools/test_land_shadow_pack.py'):
    destination = out / 'sources' / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / name, destination)
with ZipFile(archive) as bundle:
    bundle.extractall(out / 'pack')
unit = execute([sys.executable, root / 'tools/test_land_shadow_pack.py', '-v'], out, 'unit')
assert unit.returncode == 0 and 'Ran 26 tests' in unit.stderr
environment = dict(os.environ, __EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/10_nvidia.json')
compiler = root / 'build/glcheck'
compiled = execute([compiler, out / 'pack/shaders', '--compile-only'], out, 'compile-only', environment)
assert compiled.returncode == 0 and 'Renderer: NVIDIA GeForce RTX 3080 Ti' in compiled.stdout
observed = execute([sys.executable, root / 'tools/land_shadow_run.py', '--shader-root', out / 'pack/shaders',
                   '--algorithm', 'land', '--out', report / 'native-identity1', '--expected-exit', '2',
                   '--label', 'identity-routing-only-not-an-improved-filter'], out, 'identity-native')
assert observed.returncode == 0
identity = json.loads((report / 'native-identity1/receipt.json').read_text())
assert identity['completedExpectedObservation'] and not identity['candidateQualified']
baseline_capture = report / 'native-baseline1/capture'
identity_capture = report / 'native-identity1/capture'
compared = []
for path in sorted(baseline_capture.glob('*.rgba32f')):
    assert path.read_bytes() == (identity_capture / path.name).read_bytes(), path.name
    compared.append(path.name)
assert len(compared) == 26
save(out / 'receipt.json', dict(identityArchiveSHA256=sha(archive),
    sourcePins={path.relative_to(out / 'sources').as_posix(): sha(path)
                for path in (out / 'sources').rglob('*') if path.is_file()},
    focusedTests=26, unitExit=unit.returncode, compilerExit=compiled.returncode,
    compilerBinarySHA256=sha(compiler), compilerRenderer='NVIDIA GeForce RTX 3080 Ti',
    exactNativeLookupFrames=compared, identityRoutingPassed=True,
    improvedFilterAccepted=False, actualIrisAccepted=False, liveClientChanged=False))
print('Identity archive/26CPU tests/all-pair compilation/26native lookup frames passed; no improved-filter acceptance.')
