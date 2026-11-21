import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path('/home/kusutohu/repos/aqualumen')
OUT=ROOT/'reports/2026-10-22-underwater-rim-fix'
sys.path.insert(0,str(ROOT/'tools'))
from water_optical_audit import load

parser=argparse.ArgumentParser()
parser.add_argument('action',choices=('build','near','deep'))
args=parser.parse_args()
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2)

binary=OUT/'reference-build/native'
inputs={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'tools/water_continuous_reference.cpp',ROOT/'tools/water_paired_native.cpp')}
if args.action=='build':
    binary.parent.mkdir(exist_ok=False)
    command=['g++','-std=c++17','-O2','-Wall','-Wextra','tools/water_continuous_reference.cpp','-o',str(binary),'-lepoxy','-lEGL']
    run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    for suffix,content in (('stdout',run.stdout),('stderr',run.stderr)):
        with (binary.parent/('compile.'+suffix)).open('x') as stream:stream.write(content)
    receipt=dict(command=command,cwd=str(ROOT),exitCode=run.returncode,inputs=inputs)
    if run.returncode==0:receipt['binarySHA256']=sha(binary)
    save(binary.parent/'receipt.json',receipt)
    print(json.dumps(receipt))
    raise SystemExit(run.returncode)

build=json.loads((binary.parent/'receipt.json').read_text())
assert build['exitCode']==0 and build['inputs']==inputs and build['binarySHA256']==sha(binary)
capture=OUT/'runtime-optics3'/('underwater-up-'+args.action+'-paired-capture')
m,data=load(capture)
del data
assert m['opticalSamplerMapsMatchedAfterQuad'] is True and m['observerVersion']=='0.1.0-optics3'
assert 'NVIDIA' in m['glRenderer'] and all(s['format']==34836 and s['width']==1600 and s['height']==900 for s in m['opticalSamplers'].values())
scene=json.loads((OUT/'runtime-optics3'/('underwater-up-'+args.action+'-scene')/('underwater-up-'+args.action+'.json')).read_text())
camera=scene['actual_camera_position']
assert camera[0]==448.5 and camera[2]==-383.5 and scene['shader_active'] and not scene['shader_fallback']
shaderRoot=OUT/'native-optical3/paired/shaders'
shaderInputs={str(p.relative_to(shaderRoot)):sha(p) for p in shaderRoot.rglob('*') if p.is_file()}
assert sha(OUT/'optical3/optical.zip')==m['packSha256']
output=OUT/('continuous-reference-'+args.action)
assert not output.exists()
command=[str(binary),str(shaderRoot),str(capture),str(output),str(camera[0]),str(camera[2])]
environment=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/10_nvidia.json')
run=subprocess.run(command,cwd=ROOT,env=environment,capture_output=True,text=True)
for suffix,content in (('stdout',run.stdout),('stderr',run.stderr)):
    with (OUT/('reference-'+args.action+'.'+suffix)).open('x') as stream:stream.write(content)
save(OUT/('reference-'+args.action+'-receipt.json'),dict(command=command,cwd=str(ROOT),exitCode=run.returncode,
    binarySHA256=sha(binary),sourceInputs=inputs,shaderInputs=shaderInputs,
    captureManifestSHA256=sha(capture/'manifest.json'),packSHA256=m['packSha256'],cameraPosition=camera,
    stdoutSHA256=sha(OUT/('reference-'+args.action+'.stdout')),outputs={str(p.relative_to(output)):sha(p) for p in output.rglob('*') if p.is_file()} if output.exists() else {}))
print(run.stdout)
print(run.stderr)
raise SystemExit(run.returncode)
