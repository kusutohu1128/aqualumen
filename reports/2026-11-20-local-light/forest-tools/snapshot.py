"""Copy the benchmark-mod sources named by tools/build-benchmark-mod.sh into private scratch dirs (read-only on the repo).

jar-src-orig/ = pristine snapshot (never edited); jar-src/ = the patched scratch copy (edited by hand/patch).
Refuses to overwrite either directory. Records HEAD and SHA-256 of every source in snapshot-original-sha256.txt.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SRC = REPO / "tools/benchmark-mod"
JAVA = ["ScreenshotCompletion", "NativeMotionCapture", "GroundShadowClip", "FrameMixin", "CameraMixin", "Recorder",
        "OcclusionFixture", "LocalLightFixture", "UnderwaterScene", "RenderTargetSnapshot", "BathymetrySnapshot",
        "BathymetryMixin", "ShoreSamplerSnapshot", "ShoreRuntimeObserver", "ShoreFinalMixin", "SolarCacheSnapshot"]
EXTRA = ["fabric.mod.json", "aqualumen-benchmark.mixins.json"]


def main():
    orig, work = HERE / "jar-src-orig", HERE / "jar-src"
    if orig.exists() or work.exists():
        sys.exit("refusing to overwrite an existing snapshot")
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    lines = [f"# pinned HEAD {head}; working-tree copy (Recorder/OcclusionFixture carry uncommitted edits at copy time)"]
    for name in [f"dev/aqualumen/bench/{n}.java" for n in JAVA] + EXTRA:
        data = (SRC / name).read_bytes()
        for root in (orig, work):
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        lines.append(f"{hashlib.sha256(data).hexdigest()}  {name}")
    (HERE / "snapshot-original-sha256.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
