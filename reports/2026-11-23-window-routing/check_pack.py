"""Rebuild the ordinary archive, check its inputs and compile every shipped program."""
from selective_room import ROOT,HERE,PACK,DIGEST,guarded
from compile_release import compile_pack
from zipfile import ZipFile
from pathlib import Path
import json, subprocess, sys

def check():
    scratch=ROOT/"build/window-routing/compilers"
    scratch.mkdir(exist_ok=True)
    dest=scratch/"Aqualumen-Window-Routing.zip"
    subprocess.run([sys.executable,ROOT/"tools/build.py","--window-routing","--output",dest],check=True)
    assert guarded.sha(dest)==guarded.sha(PACK)==guarded.sha(ROOT/"dist"/dest.name)==DIGEST
    with ZipFile(dest) as z:
        programs=sorted(Path(n).stem if n.endswith(".vsh") else Path(n).name for n in z.namelist() if n.endswith((".csh",".vsh")))
        assert z.testzip() is None and len(programs)==40
        assert z.read("shaders/lib/ordinary_lighting.glsl")== (ROOT/"release/stained-panes/shaders/lib/local_lighting.glsl").read_bytes()
        assert not any(b"routeAudit" in z.read(n) for n in z.namelist())
    for vendor in ("mesa","nvidia"):
        compile_pack(vendor,archive=dest,artifacts=HERE,scratch=scratch,additional_lighting=("deferred1.fsh",))
    (HERE/"build.json").write_text(json.dumps(dict(sha256=DIGEST,programs=programs),indent=2)+"\n")
if __name__=="__main__":check()
