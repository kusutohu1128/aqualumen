import hashlib
import json
from pathlib import Path
import subprocess

root=Path('/home/kusutohu/repos/aqualumen')
out=root/'reports/2026-10-22-underwater-rim-fix/current-regression'
out.mkdir(exist_ok=False)
cases=[]
for pattern in ('test_water_optical_probe.py','test_water_continuous_candidate.py','test_water_paired_runtime.py','test_water_paired_diagnostic.py'):
    command=['python3','-m','unittest','discover','-s','tools','-p',pattern]
    result=subprocess.run(command,cwd=root,capture_output=True,text=True)
    for suffix,content in (('stdout',result.stdout),('stderr',result.stderr)):
        with (out/(pattern+'.'+suffix)).open('x') as stream:stream.write(content)
    cases.append(dict(command=command,exitCode=result.returncode))
sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'tools').glob('water_*') if p.is_file()}
with (out/'receipt.json').open('x') as stream:json.dump(dict(cases=cases,sourceSHA256=sources,passed=all(c['exitCode']==0 for c in cases)),stream,indent=2)
print(json.dumps(cases))
raise SystemExit(0 if all(c['exitCode']==0 for c in cases) else 1)
