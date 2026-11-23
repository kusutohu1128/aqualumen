"""Run the same witnessed room edits as the original cache study."""
import sys
from pack import HERE, ROOT, WORK, NAME
from meter import METER_NAME
from continuous import NORMAL, METER
from swept import METER as HULL_METER

sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-open-volume"))
from room import Grove, STAGES, guarded

if __name__=="__main__":
    mode,label,expected=sys.argv[1:]
    packs={"normal":NAME,"meter":METER_NAME,"continuous":NORMAL,"continuous-meter":METER,"hull-meter":HULL_METER,"release":"ordinary/"+NAME}
    candidate=WORK/packs[mode]
    assert guarded.sha(candidate)==expected and not (HERE/label).exists()
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(STAGES),
               glcache=str(guarded.BUILD/"driver-cache"),**{"period-ticks":"200","shot-gap":".15",
               "compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(candidate,label,"off",fixed,HERE,Grove)
