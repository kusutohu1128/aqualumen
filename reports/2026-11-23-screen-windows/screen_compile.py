"""Verify the tiled study's complete program set on both renderers."""
from screen_trials import ROOT,HERE,PACK,DIGEST,guarded
from compile_release import compile_pack
from zipfile import ZipFile
import json, subprocess, sys
work=ROOT/"build/window-tiles/compilers"
work.mkdir(exist_ok=True)
p=work/PACK.name
subprocess.run([sys.executable,ROOT/"tools/build.py","--window-tiles","--output",p],check=True)
assert guarded.sha(p)==DIGEST==guarded.sha(PACK)
with ZipFile(p) as z:
    assert z.testzip() is None
    programs=[s for s in z.namelist() if s.endswith((".vsh",".csh"))]
    assert len(programs)==41
for driver in ("mesa","nvidia"):
    compile_pack(driver,archive=p,artifacts=HERE,scratch=work,additional_lighting=("deferred1.fsh",))
(HERE/"build.json").write_text(json.dumps(dict(sha256=DIGEST,programCount=len(programs)),indent=2)+"\n")
