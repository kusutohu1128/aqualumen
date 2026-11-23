"""Restore the direction of a planar wet surface when Iris encodes +Y off axis."""
import sys
from packing import WORK,build,replace
from release import VERSION
from normals import CameraRoom
from flat_lamp import compare
from room import HERE, ROOT, STAGES, COMPILER, CACHE, guarded

TRIAL=WORK/"Aqualumen-Wet-Plane-Study.zip"
METER=WORK/"Aqualumen-Wet-Plane-Readout.zip"


def wet_plane(name,shader):
    path=ROOT/"release/wet-plane-study"/name
    return path.read_text() if path.is_file() else shader


def inspected(name,shader):
    shader=compare(name,wet_plane(name,shader))
    if name=="shaders/deferred.fsh":
        return replace(shader,"finiteValues?187.:252.", "finiteValues?(stored.w==-4.?188.:187.):252.")
    return shader


if __name__=="__main__":
    diagnostic=sys.argv[1]=="measure"
    assert diagnostic or sys.argv[1]=="play"
    pack=METER if diagnostic else VERSION.with_name("Aqualumen-Wet-Plane-Study.zip")
    digest=build(pack,inspected) if diagnostic else guarded.sha(pack)
    expected="2275262954eacdee221460df2494f5753a84060d04c3efa52c211b6de528db0e" if diagnostic else "8df2a8fcd645d58f0423d8b9974f99a186022d345c44a2ef9404b05a9c6a52c2"
    assert digest==expected
    print(digest,flush=True)
    fixed=dict(backend="vgl",size="1600x900",settle="1",glcache=str(CACHE),stages=",".join(STAGES),
               **{"period-ticks":"260","shot-gap":"0.15","compiler-mod":str(COMPILER)})
    guarded.launch(pack,"corrected-stone-meter" if diagnostic else "corrected-stone-release","off",fixed,HERE,CameraRoom)
