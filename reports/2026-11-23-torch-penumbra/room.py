"""Use the exact preview 12 moving-room scene and observer on a private clone."""
import importlib.util
import sys
from pack import HERE, WORK
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-umbra"))
from moving import ANIMALS, CACHE, COMPILER, STAGES, MovingScene, guarded


def main():
    op,label,expected=sys.argv[1:]
    pack=WORK/("Aqualumen-Hand-Penumbra.zip" if "joint" in label else "Aqualumen-Torch-Penumbra.zip")
    assert guarded.sha(pack)==expected
    if op=="play":
        fixed={"backend":"vgl","size":"1280x720","settle":"1","shot-gap":".15",
               "period-ticks":"220","glcache":str(CACHE),"compiler-mod":str(COMPILER),
               "stages":",".join(STAGES)}
        guarded.launch(pack,label,"off",fixed,HERE,MovingScene)
    elif op=="record":
        spec=importlib.util.spec_from_file_location("cow_room_walk",ANIMALS/"walk.py")
        runner=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        runner.capture(pack,label,COMPILER,CACHE,out_root=HERE,
                       command=[sys.executable,__file__,"play",label,expected])
    else:
        raise ValueError(op)


if __name__=="__main__":
    main()
