"""One 1440p four-torch run; retain the native render intervals even below 100 frames."""
import sys
from pack import HERE, ROOT, WORK
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
from measure_density import TorchCounts, analyze, guarded


def run(label,pack,expected):
    assert guarded.sha(pack)==expected and not (HERE/label).exists()
    fixed={"backend":"vgl","size":"2560x1440","settle":"1","stages":"birch-4","period-ticks":"800",
           "glcache":str(guarded.BUILD/"driver-cache"),"compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")}
    try:
        guarded.launch(pack,label,"off",fixed,HERE,TorchCounts)
    except SystemExit as exc:
        if exc.code:
            raise
    # The common analysis still requires a real >=10 s window and three
    # post-photo batches of warm-up. A slow candidate can yield fewer frames.
    analyze(HERE/label,pack,False,min_frames=2)


if __name__=="__main__":
    from pathlib import Path
    label,path,sha=sys.argv[1:]
    run(label,Path(path).resolve(),sha)
