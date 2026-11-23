"""Compile/link the packaged shader programs with each driver's normal directive."""
import argparse
import os
import re
import subprocess
import tempfile
from zipfile import ZipFile
from packs import ROOT, HERE, WORK

def compile_pack(vendor,filtered=False,*,archive=None,artifacts=HERE,scratch=WORK,additional_lighting=()):
    label="compile-"+("sun-" if filtered else "")+vendor
    work=scratch/label
    work.mkdir(exist_ok=True)
    if archive is None: archive=ROOT/"dist"/("Aqualumen-Sunlit-Panes.zip" if filtered else "Aqualumen-Stained-Panes.zip")
    with ZipFile(archive) as z:
        z.extractall(work)
    shader=work/"shaders"
    def expand(path):
        return re.sub(r'^\s*#include\s+"([^"]+)"',lambda m:expand(shader/m[1].lstrip("/")),path.read_text(),flags=re.M)
    directive="#pragma optionNV(inline 128)"
    selected=[]
    if vendor=="nvidia":
        for p in sorted(shader.iterdir()):
            if p.suffix not in (".fsh",".vsh"):continue
            src=expand(p)
            if "aqualumenAreaSourceLighting" in src and "aqualumenLightField" in src and "local_size_x" not in src:
                text=p.read_text()
                assert directive not in text
                p.write_text(re.sub(r'(?m)^(\s*#version[^\n]*\n)',r'\g<1>'+directive+'\n',text,count=1))
                selected.append(p.name)
        previous=(HERE.parent/"2026-11-23-torch-brick-scan/nvidia-programs.txt").read_text().splitlines()
        assert selected==sorted([*previous,*additional_lighting]),selected
    env=os.environ.copy()
    env["__EGL_VENDOR_LIBRARY_FILENAMES"]="/usr/share/glvnd/egl_vendor.d/"+("10_nvidia.json" if vendor=="nvidia" else "50_mesa.json")
    if vendor=="mesa":env.update(LIBGL_ALWAYS_SOFTWARE="1",GALLIUM_DRIVER="llvmpipe",LP_NUM_THREADS="2")
    with tempfile.TemporaryFile(mode="w+") as log:
        process=subprocess.run([ROOT/"build/glcheck",shader,"--compile-only"],stdout=log,stderr=subprocess.STDOUT,env=env)
        log.seek(0);output=log.read()
    (artifacts/(label+".txt")).write_text(output)
    assert process.returncode==0 and ("3080 Ti" if vendor=="nvidia" else "llvmpipe") in output,output[-1200:]
    expected={"PASS "+p.stem+(" (vsh+gsh+fsh)" if p.with_suffix(".gsh").is_file() else "")
              for p in shader.glob("*.vsh")}
    expected.update("PASS compile/link "+p.name for p in shader.glob("*.csh"))
    compiled={line for line in output.splitlines() if line.startswith("PASS ") and not line.startswith("PASS compile/link only;")}
    assert compiled==expected,(compiled^expected)
    print(vendor,len(expected),"programs")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("vendor",choices=("mesa","nvidia"))
    parser.add_argument("--filtered",action="store_true")
    args=parser.parse_args()
    compile_pack(args.vendor,args.filtered)
