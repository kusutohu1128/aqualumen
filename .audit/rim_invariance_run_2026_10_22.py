import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import argparse

root=Path('/home/kusutohu/repos/aqualumen')
parser=argparse.ArgumentParser()
parser.add_argument('--generation',default='')
args=parser.parse_args()
out=root/('reports/2026-10-22-underwater-rim-fix/invariance-hit1'+args.generation)
out.mkdir(exist_ok=False)
sys.path.insert(0,str(root/'tools'))
from water_paired_native_run import extract
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=root/'tools/water_continuous_invariance.cpp'
inputs={str(p.relative_to(root)):sha(p) for p in (source,root/'tools/water_paired_native.cpp')}
archive=root/'reports/2026-10-22-joint-paired-water/packs/control.zip'
assert sha(archive)=='a150afe2261970d88eff432b1a30c5b2ad1127bf9926324222300ee12c43fcf5'
base=extract(archive,out/'base')
corrected=root/'reports/2026-10-22-underwater-rim-fix/native-opticalhit1/control/shaders'
binary=out/'native'
commands=[['g++','-std=c++17','-O2','-Wall','-Wextra',str(source),'-o',str(binary),'-lepoxy','-lEGL'],
    [str(binary),str(base),str(corrected),str(out/'captures')]]
receipt=dict(inputs=inputs,archiveSHA256=sha(archive),commands=commands,exitCodes=[],
    correctedShaderSHA256=sha(corrected/'gbuffers_water.fsh'))
environment=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/10_nvidia.json')
for i,command in enumerate(commands):
    run=subprocess.run(command,cwd=root,env=environment,capture_output=True,text=True)
    for suffix,content in (('stdout',run.stdout),('stderr',run.stderr)):
        with (out/(str(i)+'.'+suffix)).open('x') as f:f.write(content)
    receipt['exitCodes'].append(run.returncode)
    print(run.stdout,flush=True)
    if run.returncode:break
receipt['passed']=receipt['exitCodes']==[0,0]
receipt['artifacts']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
with (out/'receipt.json').open('x') as f:json.dump(receipt,f,indent=2)
raise SystemExit(0 if receipt['passed'] else 1)
