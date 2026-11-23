"""Compile the uninstrumented installable ZIP with both GLSL drivers."""
import sys
from window_room import HERE, ROOT, PACKS, guarded
from compile_release import compile_pack

role=sys.argv[1] if len(sys.argv)>1 else "candidate"
name, digest = PACKS[role]
archive = ROOT / "dist" / f"Aqualumen-{name}.zip"
assert guarded.sha(archive) == digest
out=HERE if role=="candidate" else HERE/"cells-compile"
out.mkdir(exist_ok=True)
(ROOT/"build/pane-beam"/role).mkdir(exist_ok=True)
for vendor in ("mesa", "nvidia"):
    compile_pack(vendor, archive=archive, artifacts=out, scratch=ROOT/"build/pane-beam"/role)
