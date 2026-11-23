"""Build and run the consecutive-frame edit test on each GL driver."""
import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from zipfile import ZipFile
from window_room import ROOT, HERE, guarded, PACKS

WORK=ROOT/"build/pane-beam/edits"
def build():
    WORK.mkdir(exist_ok=True,parents=True)
    old=HERE.parent/"2026-11-23-torch-open-volume"
    source=(old/"cache_probe.cpp").read_text().split("int main(int argc,char** argv) try {",1)[0]
    (WORK/"original_cache_helpers.h").write_text(source)
    path=ROOT/"dist/Aqualumen-Window-Cells.zip"
    assert guarded.sha(path)==PACKS["cells"][1]
    with ZipFile(path) as z: z.extractall(WORK)
    flags=subprocess.check_output(["pkg-config","--cflags","--libs","egl","epoxy"],text=True).split()
    subprocess.run(["g++","-O1","-std=c++17","-ffunction-sections","-fdata-sections","-Wl,--gc-sections","-I",WORK,"-I",old,
                    HERE/"cell_edits.cpp","-o",WORK/"edit-probe",*flags],check=True)

def run():
    for vendor in ("mesa","nvidia"):
        env=dict(os.environ,__EGL_VENDOR_LIBRARY_FILENAMES="/usr/share/glvnd/egl_vendor.d/"+("50_mesa.json" if vendor=="mesa" else "10_nvidia.json"))
        if vendor=="mesa": env.update(LIBGL_ALWAYS_SOFTWARE="1",GALLIUM_DRIVER="llvmpipe",LP_NUM_THREADS="2")
        cmd=[WORK/"edit-probe",WORK/"shaders"]
        trace=WORK/"edits-mesa.trace"
        recording=vendor=="mesa" and not trace.exists()
        if recording:
            cmd=["apitrace","trace","--api","egl","-o",trace,*cmd]
        output=subprocess.check_output(cmd,text=True,env=env)
        if recording:
            calls=subprocess.check_output(["apitrace","dump",trace],text=True)
            note=dict(file=str(trace.relative_to(ROOT)),bytes=trace.stat().st_size,
                      sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
                      dispatches=calls.count(" glDispatchCompute("),readbacks=calls.count(" glGetTextureSubImage("))
            assert note["dispatches"]==31 and note["readbacks"]>=30
            (HERE/"edit-trace.json").write_text(json.dumps(note,indent=2)+"\n")
        assert ("RTX 3080 Ti" if vendor=="nvidia" else "llvmpipe") in output
        (HERE/("edits-"+vendor+".txt")).write_text(output)
if __name__=="__main__":
    build()
    if "--build" not in sys.argv: run()
