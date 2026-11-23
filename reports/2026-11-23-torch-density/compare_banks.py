"""Compare full reflection banks on a fixed input, once per renderer."""
import fcntl
import os
import subprocess
import sys

from pack import ROOT, OUT
sys.path.insert(0,str(ROOT/"reports/2026-11-22-gpu-profile"))
import run as guarded

if __name__=="__main__":
    renderer=sys.argv[1]
    vendor,expected={"nvidia":("10_nvidia","RTX 3080 Ti"),"mesa":("50_mesa","llvmpipe")}[renderer]
    out=ROOT/"reports/2026-11-23-torch-density"/("reflection-pair-"+renderer+".log")
    if out.exists(): raise FileExistsError(out)
    with open("/tmp/aql-render21-1000.lock","a+b") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        before=guarded.lab_check()
        assert not guarded.inspect_gpu()["foreign"]
        env={**os.environ,"__EGL_VENDOR_LIBRARY_FILENAMES":f"/usr/share/glvnd/egl_vendor.d/{vendor}.json"}
        if renderer=="mesa": env["LIBGL_ALWAYS_SOFTWARE"]="1"
        with out.open("x") as stream:
            run=subprocess.run([ROOT/"build/glcheck",OUT/"base/shaders","--ceiling-light-probe",OUT/"candidate/shaders"],
                               env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=500)
        print(out.read_text(),flush=True)
        assert run.returncode==0 and expected in out.read_text() and 'PASS full reflection banks' in out.read_text()
        assert guarded.lab_check()==before
