"""Replay previously measured forest and edited-grove scenes with the isolated candidate."""
from pathlib import Path
import sys
from make_rows import HERE, PREVIOUS, WORK

sys.path.insert(0, str(PREVIOUS))
from sweep import Sweep, POSES, guarded, ROOT

if __name__ == "__main__":
    label = sys.argv[1]
    if label == "grove":
        from animal_run import EditedGrove, EDIT_STAGES
        scene, stages = EditedGrove, EDIT_STAGES
    else:
        assert label == "forest"
        scene, stages = Sweep, list(POSES)
    package = WORK / "Aqualumen-Torch-rows-meter.zip"
    assert guarded.sha(package) == "a00ac2e8c292a8c8dc304c0432fb27d94bdac56873894187eeaa4f384d267f8c"
    assert not (HERE / label).exists()
    fixed = dict(backend="vgl", size="1280x720", settle="1", stages=",".join(stages),
                 glcache=str(guarded.BUILD / "driver-cache"),
                 **{"period-ticks": "200", "shot-gap": ".15",
                    "compiler-mod": str(ROOT / "dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(package, label, "off", fixed, HERE, scene)
