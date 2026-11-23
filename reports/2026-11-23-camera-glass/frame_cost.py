"""Revisit the previously timed 1440p room with this production candidate."""
import sys
from room import HERE,ROOT,STUDY
sys.path.insert(0,str(HERE.parent/"2026-11-23-window-routing"))
from selective_room import SelectiveRoom,guarded
from frame_times import analyze
label="frames-1440"
assert not (HERE/label).exists()
fixed=dict(backend="vgl",size="2560x1440",settle="1",stages="air,red-ew",glcache=str(guarded.BUILD/"driver-cache"),
           **{"period-ticks":"550","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
try:
    guarded.launch(STUDY,label,"off",fixed,HERE,SelectiveRoom)
except SystemExit as exc:
    if exc.code: raise
analyze(HERE/label,STUDY,False,min_frames=50,required_passes=set())
