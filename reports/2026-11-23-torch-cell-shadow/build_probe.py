"""Build the field test with the existing EGL and light-input fixture helpers."""
from pathlib import Path
import subprocess
from zipfile import ZipFile
from hashlib import sha256

here = Path(__file__).resolve().parent
work = here.parents[1] / "build/torch-cell-shadow"
previous = here.parent / "2026-11-23-torch-open-volume"
helpers, marker, _ = (previous/"cache_probe.cpp").read_text().partition("int main(int argc,char** argv) try {")
assert marker
(work/"original_cache_helpers.h").write_text(helpers)
pack = work/"Aqualumen-Torch-Cell-Shadow.zip"
assert sha256(pack.read_bytes()).hexdigest()=="14e849c5b54ee04db05c75216a75764e865d553b711e67b180ed328c6afb7db0"
with ZipFile(pack) as z:
    z.extractall(work/"candidate")
flags = subprocess.check_output(["pkg-config","--cflags","--libs","epoxy","egl"],text=True).split()
subprocess.run(["g++","-O1","-ffunction-sections","-fdata-sections","-Wl,--gc-sections","-std=c++17","-I",work,"-I",previous,here/"check_field.cpp","-o",work/"field-probe",*flags],check=True)
