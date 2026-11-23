"""Apply the same 10 s timing window even when fewer than 101 frames fit in it."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
from measure_density import analyze,guarded,TorchCounts,gpu,HERE as DENSITY

if __name__=="__main__":
    label,source,digest=sys.argv[1:4]
    assert sys.argv[4:] in ([],["--gpu"])
    profile=bool(sys.argv[4:])
    gpu.EXPECTED |= {"dispatch/shadowcomp5","dispatch/shadowcomp6"}
    pack=Path(source).resolve(strict=True)
    assert guarded.sha(pack)==digest and not (DENSITY/label).exists()
    fixed=dict(backend="vgl",size="2560x1440",stages="birch-4",settle="1",glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"800","compiler-mod":str(HERE.parents[1]/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    try:guarded.launch(pack,label,"on" if profile else "off",fixed,DENSITY,TorchCounts)
    except SystemExit as exc:
        if exc.code:raise
    analyze(DENSITY/label,pack,profile,min_frames=1)
