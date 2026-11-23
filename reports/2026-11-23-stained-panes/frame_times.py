"""Measure the installed ZIP in a private 1440p room, with GPU timestamps off."""
import argparse
from glass_room import HERE, ROOT, Room, guarded
import sys

sys.path.insert(0,str(HERE.parent / "2026-11-23-torch-density"))
from measure_density import analyze


def run(label, pack):
    path = ROOT / "dist" / ("Aqualumen-" + pack + ".zip")
    assert guarded.sha(path) == {"Diffuse-Display":"1794d020679d80cb65986ed4a8f2f2b0f453b6e3d9ee04c560f0b43dd285439c",
                                 "Stained-Panes":"7f5403e7c3fd57666f2417837bfe3d72d4d142d7b4cce29fdeff891504e36a77",
                                 "Sunlit-Panes":"c84ea61f7ae5cc97872edaf6789bc5541297f4a253f7465d6e16dbc51b60443f"}[pack]
    folder = HERE / label
    assert not folder.exists(), folder
    fixed = dict(backend="vgl",size="2560x1440",settle="1",stages="air,red-ew",
                 glcache=str(guarded.BUILD/"driver-cache"),
                 **{"period-ticks":"550","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    try:
        guarded.launch(path,label,"off",fixed,HERE,Room)
    except SystemExit as exc:
        if exc.code: raise
    analyze(folder,path,False,min_frames=50)


if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("label")
    ap.add_argument("pack", choices=("Diffuse-Display","Stained-Panes","Sunlit-Panes"))
    a=ap.parse_args()
    run(a.label,a.pack)
