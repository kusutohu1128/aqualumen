import hashlib
import json
import os
from pathlib import Path
import subprocess
import argparse

root = Path('/home/kusutohu/repos/aqualumen')
out = root / 'reports/2026-10-22-underwater-rim-fix'
parser = argparse.ArgumentParser()
parser.add_argument('--generation', default='')
parser.add_argument('--pack-relative')
args = parser.parse_args()
generation = args.generation
if generation:
    out = out / ('qualification' + generation)
    out.mkdir(exist_ok=False)
artifact_root = root / 'reports/2026-10-22-underwater-rim-fix'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
native_file = artifact_root / ('native-optical'+generation) / 'receipt.json'
native = json.loads(native_file.read_text())
assert native['passed'] and native['exit_code'] == 0 and all(c['c0_byte_equal'] for c in native['cases'])
pack = artifact_root / (args.pack_relative or ('optical'+generation+'/optical.zip'))
assert native['final_preview0_byte_equal'] and native['paired_zip_sha256'] == sha(pack)
environment = dict(os.environ, __EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/10_nvidia.json')
evidence = [native_file]
for role in ('control', 'paired'):
    shader_root = artifact_root / ('native-optical'+generation) / role / 'shaders'
    command = ['build/glcheck', str(shader_root), '--compile-only']
    before = {str(p.relative_to(shader_root)):sha(p) for p in shader_root.rglob('*') if p.is_file()}
    run = subprocess.run(command, cwd=root, env=environment, capture_output=True, text=True)
    for suffix, content in (('stdout', run.stdout), ('stderr', run.stderr)):
        with (out / (role+'-compile.'+suffix)).open('x') as stream:
            stream.write(content)
    assert before == {str(p.relative_to(shader_root)):sha(p) for p in shader_root.rglob('*') if p.is_file()}
    path = out / (role+'-compile-receipt.json')
    with path.open('x') as stream:
        json.dump(dict(command=command,cwd=str(root),exitCode=run.returncode,renderer=native['renderer'],
                       binarySHA256=sha(root/'build/glcheck'),inputs=before,
                       archiveSHA256=native[role+'_zip_sha256'], stdoutSHA256=sha(out/(role+'-compile.stdout'))),stream,indent=2)
    assert run.returncode == 0 and 'Renderer: NVIDIA' in run.stdout
    evidence.append(path)
proof = dict(schema='aqualumen-paired-water-qualification-v1', packSHA256=native['paired_zip_sha256'],
             renderer=native['renderer'], compileExitCode=0, nativeExitCode=0, C0Exact=True, classificationPassed=True,
             testedRoutes=native['tested_routes'], untestedRoutes=native['untested_routes'],
             evidence=[dict(path=str(p.relative_to(root)),sha256=sha(p)) for p in evidence],
             opticalMRTAllocationNativeVerified=False, actualIrisAccepted=False, physicalAccepted=False)
proof['C0ExactComparedToControlZipSHA256'] = native['control_zip_sha256']
with (out / 'optical-qualification.json').open('x') as stream:
    json.dump(proof, stream, indent=2)
print('Recorded both actual NVIDIA compile exits, exact source/ZIP hashes and native passivity; actual Iris allocation remains pending')
