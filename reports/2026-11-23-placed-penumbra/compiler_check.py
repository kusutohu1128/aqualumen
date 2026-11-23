"""Prepare the standalone NVIDIA link check with the shipped compiler's directive."""
from pathlib import Path
import re
import shutil
import sys
from pack import WORK
source=WORK/"hull/shaders"
target=WORK/"native-compiler/shaders"
if len(sys.argv) == 3:
    source, target = map(Path, sys.argv[1:])
shutil.copytree(source,target,dirs_exist_ok=True)
def expand(p):
    s=p.read_text()
    def include(m):
        name=m.group(1)
        return expand(source/name[1:] if name.startswith("/") else p.parent/name)
    return re.sub(r'^\s*#include\s+"([^"]+)"',include,s,flags=re.M)
for p in target.iterdir():
    if p.suffix not in (".vsh",".fsh",".gsh",".csh"): continue
    all_source=expand(source/p.name)
    if "aqualumenAreaSourceLighting" in all_source and "aqualumenLightField" in all_source and "local_size_x" not in all_source:
        text=p.read_text()
        p.write_text(re.sub(r'(^#version[^\n]*\n)',r'\1#pragma optionNV(inline 128)\n',text,count=1))
        print(p.name)
