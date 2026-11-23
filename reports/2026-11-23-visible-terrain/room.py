"""Use the previously registered two-lantern room with the normal deferred pack."""
import importlib.util
import sys

from visible_pack import HERE, PACK, STUDY_SHA
sys.path.insert(0, str(HERE.parent / "2026-11-23-torch-umbra"))
from moving import ANIMALS, CACHE, COMPILER, MovingScene, STAGES, guarded



def main():
    action, label = sys.argv[1:]
    assert guarded.sha(PACK) == STUDY_SHA
    if action == "play":
        fixed = {"backend":"vgl", "size":"1280x720", "settle":"1", "shot-gap":".15",
                 "period-ticks":"220", "glcache":str(CACHE), "compiler-mod":str(COMPILER),
                 "stages":",".join(STAGES)}
        guarded.launch(PACK, label, "off", fixed, HERE, MovingScene)
    elif action == "record":
        spec = importlib.util.spec_from_file_location("record_private_cow", ANIMALS / "walk.py")
        recorder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recorder)
        recorder.capture(PACK, label, COMPILER, CACHE, out_root=HERE,
                         command=[sys.executable, __file__, "play", label])
    else:
        raise ValueError(action)


if __name__ == "__main__":
    main()
