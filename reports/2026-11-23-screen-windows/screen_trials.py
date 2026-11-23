"""Exercise the tiled deferred program without altering the ordinary laboratory."""
import argparse
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ROUTE=HERE.parent/"2026-11-23-window-routing"
sys.path.insert(0,str(ROUTE))
from selective_room import SelectiveRoom, TorchCounts, guarded, gpu, analyze
from forest_window import ForestWindow
PACK=ROOT/"build/window-tiles/Aqualumen-Window-Tiles.zip"
DIGEST="4a3f9b865ba9ddc727e8a0ff3e703c3843f6ca84c212d109d42d0e558fe0d802"

def run(label,scene):
    assert guarded.sha(PACK)==DIGEST and not (HERE/label).exists()
    stages,room={"rear":("birch-0,birch-4",ForestWindow),"birch":("birch-0,birch-4",TorchCounts),
                 "room":("air,red-ew",SelectiveRoom)}[scene]
    fixed=dict(backend="vgl",size="2560x1440",settle="1",stages=stages,glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"620" if scene!="room" else "550","shot-gap":".15",
               "compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    try:guarded.launch(PACK,label,"off",fixed,HERE,room)
    except SystemExit as exc:
        if exc.code:raise
    analyze(HERE/label,PACK,False,min_frames=50)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("label")
    parser.add_argument("scene",choices=("rear","birch","room","optics"))
    a=parser.parse_args()
    if a.scene=="optics":
        import route_optics
        route_optics.run(a.label,route_optics.package(PACK,DIGEST,"Aqualumen-Tiled-Transmission.zip"),HERE)
    else: run(a.label,a.scene)
