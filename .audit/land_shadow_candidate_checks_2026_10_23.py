import json
import os
from pathlib import Path
import shutil
import sys
from zipfile import ZipFile

root = Path('/home/kusutohu/repos/aqualumen')
sys.path.insert(0, str(root / 'tools'))
from land_shadow_pack import build_pack
from land_shadow_run import execute, save, sha

report = root / 'reports/2026-10-23-land-shadows'
out = report / 'candidate2-checks'
out.mkdir(exist_ok=False)
archive = report / 'Aqualumen-LandShadows-Preview-2026-10-23.zip'
for name in ('shaders/lib/land_lighting.glsl', 'shaders/lib/land_shadows.glsl',
             'tools/land_shadow_pack.py', 'tools/test_land_shadow_pack.py',
             'tools/land_shadow_native.cpp', 'tools/land_shadow_motion_native.cpp',
             'tools/land_shadow_run.py'):
    destination = out / 'sources' / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / name, destination)
manifest = build_pack(report / 'ordinary-0.6.zip', archive, root / 'shaders/lib')
with ZipFile(archive) as bundle:
    bundle.extractall(out / 'pack')
unit = execute([sys.executable, root / 'tools/test_land_shadow_pack.py', '-v'], out, 'unit')
assert unit.returncode == 0 and 'Ran 28 tests' in unit.stderr
environment = dict(os.environ, __EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/10_nvidia.json')
compiler = root / 'build/glcheck'
compiled = execute([compiler, out / 'pack/shaders', '--compile-only'], out, 'compile-only', environment)
assert compiled.returncode == 0 and 'Renderer: NVIDIA GeForce RTX 3080 Ti' in compiled.stdout
save(out / 'compile.json', dict(exitCode=compiled.returncode, renderer='NVIDIA GeForce RTX 3080 Ti',
     packSHA256=sha(archive), compilerBinarySHA256=sha(compiler),
     stdout=dict(path=str(out / 'compile-only.stdout'), sha256=sha(out / 'compile-only.stdout')),
     stderr=dict(path=str(out / 'compile-only.stderr'), sha256=sha(out / 'compile-only.stderr'))))
native = execute([sys.executable, root / 'tools/land_shadow_run.py', '--shader-root', out / 'pack/shaders',
                  '--algorithm', 'land', '--out', report / 'native-candidate2',
                  '--label', 'land-metric-receiver-plane-comment-reviewed'], out, 'candidate-native')
save(out / 'receipt.json', dict(archiveSHA256=sha(archive), nativeRunnerExit=native.returncode,
     unitExit=unit.returncode, focusedTests=28, compilerExit=compiled.returncode,
     preservation=manifest, sourcePins={path.relative_to(out / 'sources').as_posix(): sha(path)
         for path in (out / 'sources').rglob('*') if path.is_file()}))
assert native.returncode == 0, 'Candidate physical target failed; keep immutable observations'
proof = json.loads((report / 'native-candidate2/receipt.json').read_text())
assert proof['candidateQualified'] is True
print('Comment-reviewed candidate archive/CPU/all-pair compile/native passed; motion and Minecraft remain open.')
