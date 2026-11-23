from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/"2026-11-23-stained-panes"))
from compile_release import compile_pack
scratch=ROOT/"build/camera-glass"
extra=("deferred1.fsh","gbuffers_block_translucent.fsh","gbuffers_entities_translucent.fsh","gbuffers_entities_translucent.vsh",
       "gbuffers_hand_water.fsh","gbuffers_particles_translucent.fsh")
for renderer in ("mesa","nvidia"):
    compile_pack(renderer,archive=ROOT/"dist/Aqualumen-Camera-Glass.zip",artifacts=HERE,scratch=scratch,additional_lighting=extra)
