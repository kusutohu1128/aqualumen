"""Measure the ordinary old and new shaders in the already surveyed birch stand."""
import sys
from window_room import HERE, ROOT, PACKS, guarded, analyze
from measure_density import TorchCounts

def run(role, profile=False):
    name,sha=PACKS[role]
    pack=ROOT/"dist"/f"Aqualumen-{name}.zip"
    label=("gp-window-birch-"+role+"-profile") if profile else ("birch-"+role)
    folder=HERE/label
    assert guarded.sha(pack)==sha and not folder.exists()
    fixed=dict(backend="vgl",size="2560x1440",settle="1",stages="birch-0,birch-4",glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"620","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    try:
        guarded.launch(pack,label,"on" if profile else "off",fixed,HERE,TorchCounts)
    except SystemExit as exc:
        if exc.code: raise
    analyze(folder,pack,profile,min_frames=50)

if __name__=="__main__":run(sys.argv[1],"--profile" in sys.argv)
