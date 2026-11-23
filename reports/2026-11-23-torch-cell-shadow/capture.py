"""Use the earlier world's verified poses, block changes and live animal positions with the new field."""
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-shadow-integral"))
from sweep import Sweep, POSES, guarded
from animal_run import EditedGrove, EDIT_STAGES

if __name__=="__main__":
    role=sys.argv[1]
    scene,stages={"forest":(Sweep,list(POSES)), "grove":(EditedGrove,EDIT_STAGES)}[role]
    pack=ROOT/"build/torch-cell-shadow/Aqualumen-Torch-Cell-Meter.zip"
    assert guarded.sha(pack)=="7cbf8e456ec5a2e9d812a74a5b8fb02b0063816e387fa6e53b0ea9f81e1b21e9"
    assert not (HERE/role).exists()
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(stages),
            glcache=str(guarded.BUILD/"driver-cache"),**{"period-ticks":"200","shot-gap":".15",
            "compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(pack,role,"off",fixed,HERE,scene)
