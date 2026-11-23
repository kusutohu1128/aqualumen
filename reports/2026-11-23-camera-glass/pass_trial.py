"""Measure the separate eye pass against the candidate and its unmodified parent."""
import argparse
import json
import sys
from pathlib import Path
from room import HERE,ROOT,STAGES,GlassRoom,meter,guarded
sys.path.insert(0,str(HERE.parent/"2026-11-23-window-routing"))
from selective_room import SelectiveRoom
from frame_times import analyze
from compile_release import compile_pack
PACK=ROOT/"build/camera-glass/Aqualumen-Glass-View-Pass.zip"
DIGEST="0309eb7c180e1e4d27977463c438ab3fe135b2f5054a2c263eb6ca245de2b293"
def main():
    assert guarded.sha(PACK)==DIGEST
    aux=HERE/"view-pass";aux.mkdir(exist_ok=True)
    scratch=ROOT/"build/camera-glass/pass-compile";scratch.mkdir(exist_ok=True)
    if sys.argv[1]=="compile":
        extra=["deferred1.fsh","deferred2.fsh","gbuffers_block_translucent.fsh","gbuffers_entities_translucent.fsh",
               "gbuffers_entities_translucent.vsh","gbuffers_hand_water.fsh","gbuffers_particles_translucent.fsh"]
        for renderer in ("mesa","nvidia"):
            compile_pack(renderer,archive=PACK,artifacts=aux,scratch=scratch,additional_lighting=extra)
        return
    role=sys.argv[1]
    label="pass-"+role
    assert role in ("frames","meter","room") and not (HERE/label).exists()
    timing=role=="frames"
    stages="air,red-ew" if timing else (",".join(STAGES) if role=="meter" else "none,one,mix,front")
    fixed=dict(backend="vgl",size="2560x1440" if timing else "1280x720",settle="1",stages=stages,glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"550" if timing else "200","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    try:guarded.launch(meter(PACK) if role=="meter" else PACK,label,"off",fixed,HERE,SelectiveRoom if timing else GlassRoom)
    except SystemExit as exc:
        if exc.code:raise
    if timing:analyze(HERE/label,PACK,False,min_frames=50,required_passes=set())
if __name__=="__main__":main()
