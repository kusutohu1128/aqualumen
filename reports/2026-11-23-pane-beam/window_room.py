"""Run a hash-pinned pack in the isolated, UUID-guarded nighttime test room."""
from pathlib import Path
import argparse
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREV = HERE.parent / "2026-11-23-stained-panes"
sys.path.insert(0, str(PREV))
from glass_room import Room, LAYOUT, guarded
from frame_times import analyze as analyze_frames
from measure_density import gpu
from beam_versions import PACKS

EXISTING = tuple(LAYOUT)
EXTENDED = ("split", "opaque-edge", "red-cow", "near-east", "near-west")
for stage in EXTENDED:
    LAYOUT[stage] = dict(LAYOUT["red-ew"])
del LAYOUT["split"][406, -410]
LAYOUT["opaque-edge"][406, -409] = "stone"

class ChallengeRoom(Room):
    def __init__(self, base):
        super().__init__(base)
        base.STAGE_TABLE["red-cow"] = (False, False, (406.55,151,-408.9), "white_concrete", True, 18000)

    def geometry(self, names):
        description = super().geometry(names)
        description["stageCameras"] = {s:{"near-east":"409.51","near-west":"409.45"}.get(s,"409.48") +
                                       " 151 -405.95 153.8 7" for s in names}
        return description

    def datapack(self, names):
        functions = super().datapack(names)
        for name, x in (("near-east","409.51"), ("near-west","409.45")):
            if name not in names: continue
            i = names.index(name)
            for phase in "sve":
                k = f"data/animal/function/{phase}{i}.mcfunction"
                assert functions[k].count("409.48 151 -405.95") == 1
                functions[k] = functions[k].replace("409.48 151 -405.95", x + " 151 -405.95")
        return functions


def analyze(folder, pack, profile, *, min_frames):
    # Both current packs run the two persistent-light compute passes after shadowcomp4.
    required = gpu.EXPECTED | {"dispatch/shadowcomp5","dispatch/shadowcomp6"}
    analyze_frames(folder,pack,profile,min_frames=min_frames,required_passes=required)

def capture(label, mode, role):
    name, digest = PACKS[mode]
    pack = ROOT / "dist" / f"Aqualumen-{name}.zip"
    assert guarded.sha(pack) == digest
    profile = role == "gpu-profile"
    if profile and not label.startswith("gp-"):
        raise ValueError("The private GPU profiler requires a gp- run label")
    timing = role.startswith("timing") or profile
    stages = ("air", "red-ew") if timing else (EXISTING + EXTENDED if mode != "control" else EXTENDED)
    if role == "timing-reverse": stages = tuple(reversed(stages))
    if not timing:
        from beam_pack import meter
        pack = meter(pack, mode)
    folder = HERE / label
    assert not folder.exists(), folder
    fixed = dict(backend="vgl", size="2560x1440" if timing else "1280x720", settle="1",
                 stages=",".join(stages), glcache=str(guarded.BUILD / "driver-cache"),
                 **{"period-ticks":"700" if profile else ("550" if timing else "180"), "shot-gap":".15",
                    "compiler-mod":str(ROOT / "dist/aqualumen-lighting-compiler-0.3.0.jar")})
    try:
        guarded.launch(pack, label, "on" if profile else "off", fixed, HERE, ChallengeRoom)
    except SystemExit as exc:
        if exc.code: raise
    if timing:
        analyze(folder, pack, profile, min_frames=50)

if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("label")
    cli.add_argument("mode", choices=PACKS)
    cli.add_argument("role", choices=("timing","timing-reverse","meter","gpu-profile"))
    args = cli.parse_args()
    capture(args.label, args.mode, args.role)
