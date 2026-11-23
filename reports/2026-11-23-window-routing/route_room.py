"""Measure the exact two-draw pack in the existing private rooms."""
import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BEAM = HERE.parent / "2026-11-23-pane-beam"
sys.path.insert(0, str(BEAM))
from window_room import ChallengeRoom, guarded, gpu
from measure_density import TorchCounts, analyze

PACK = ROOT / "build/window-routing/first/Aqualumen-Window-Routing.zip"
DIGEST = "c4516dd7bc8fe8a6ccf06c2070d92fe213b5d4c4eabb48c9d1a782fd63a69334"

def run(label, forest=False, profile=False, reverse=False):
    assert guarded.sha(PACK) == DIGEST
    assert not (HERE / label).exists()
    if profile: assert label.startswith("gp-")
    stages = ["birch-0", "birch-4"] if forest else ["air", "red-ew"]
    if reverse: stages.reverse()
    options = dict(backend="vgl", size="2560x1440", settle="1", stages=",".join(stages),
                   glcache=str(guarded.BUILD / "driver-cache"),
                   **{"period-ticks": "700" if profile else ("620" if forest else "550"),
                      "shot-gap": ".15", "compiler-mod": str(ROOT / "dist/aqualumen-lighting-compiler-0.3.0.jar")})
    try:
        guarded.launch(PACK, label, "on" if profile else "off", options, HERE, TorchCounts if forest else ChallengeRoom)
    except SystemExit as exc:
        if exc.code: raise
    required = gpu.EXPECTED | {"dispatch/shadowcomp5", "dispatch/shadowcomp6", "dispatch/shadowcomp7", "quad/deferred1"}
    analyze(HERE / label, PACK, profile, min_frames=50, required_passes=required)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    for flag in ("forest", "profile", "reverse"): parser.add_argument("--"+flag, action="store_true")
    args = parser.parse_args()
    run(args.label, args.forest, args.profile, args.reverse)
