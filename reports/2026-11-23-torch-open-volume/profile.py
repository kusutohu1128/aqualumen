"""Require the two extra cache dispatches on every measured trial frame."""
import sys
from zipfile import ZipFile
from pack import HERE,ROOT,BASE,BASE_SHA,WORK

sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
import measure_density as density

if __name__=="__main__":
    arm=sys.argv[1]
    assert arm in ("control","cell")
    pack,sha=(BASE,BASE_SHA) if arm=="control" else (WORK/"Aqualumen-Torch-Cell.zip","e1e06b864967cd61305931d499f71a8f0f07eb66d5696c49eb3a5ecd36903671")
    with ZipFile(pack) as z:
        extra={f"dispatch/shadowcomp{i}" for i in range(5,9) if f"shaders/shadowcomp{i}.csh" in z.namelist()}
    assert extra==(set() if arm=="control" else {"dispatch/shadowcomp5","dispatch/shadowcomp6"})
    density.gpu.EXPECTED=density.gpu.EXPECTED | extra
    stages="birch-0,birch-4" if arm=="control" else "birch-0,birch-1,birch-2,birch-4"
    sys.argv=[sys.argv[0],"gp-density-open-volume-gpu-"+arm,"--stages",stages,"--pack",str(pack),"--sha",sha]
    density.main()
