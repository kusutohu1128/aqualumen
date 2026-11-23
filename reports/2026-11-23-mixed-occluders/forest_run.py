"""Render a diagnostic frame on the existing four-torch route without benchmarking the probe."""
from pathlib import Path
import sys
from build_trial import HERE,ROOT
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
from measure_density import TorchCounts,guarded,HERE as DENSITY

if __name__=="__main__":
    label,name,digest=sys.argv[1:]
    pack=Path(name).resolve(strict=True)
    assert guarded.sha(pack)==digest and not (DENSITY/label).exists()
    fixed=dict(backend="vgl",size="2560x1440",settle="1",stages="birch-4",
               glcache=str(guarded.BUILD/"driver-cache"),**{"period-ticks":"800",
               "compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(pack,label,"off",fixed,DENSITY,TorchCounts)
