"""Exclusive original-MAIN native receiver test recording; Java must be closed."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/2026-10-06-water-occluded-main"


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if subprocess.run(["rtk", "proxy", "pgrep", "-x", "java"], stdout=subprocess.DEVNULL).returncode != 1:
        raise ValueError("Live Java prevents native GPU validation")
    if (OUT / "native-v1").exists() or (OUT / "native-receipt.json").exists():
        raise ValueError("Prior native evidence must not be overwritten")
    frozen = OUT / "frozen-source"
    frozen.mkdir(exist_ok=False)
    sources = [ROOT / "tools/water_occluded_receiver_main.cpp", ROOT / "tools/glcheck.cpp",
               ROOT / "tools/water_occluded_receiver_lifecycle.py", Path(__file__).resolve(),
               *sorted((ROOT / "tools").glob("*probe.h")), *sorted((ROOT / "shaders").rglob("*"))]
    hashes = {}
    for path in sources:
        if not path.is_file(): continue
        name = path.relative_to(ROOT)
        target = frozen / name; target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream: stream.write(path.read_bytes())
        hashes[str(name)] = sha(path)
    binary = ROOT / "build/water_occluded_receiver_main"
    result = subprocess.run(["rtk", "proxy", str(binary), str(ROOT / "shaders"), str(OUT / "native-v1")],
                            cwd=ROOT, capture_output=True, text=True)
    with (OUT / "native.log").open("x") as stream: stream.write(result.stdout + result.stderr)
    receipt = dict(exitCode=result.returncode, rendererReportedByActualGL="RTX 3080 Ti" in result.stdout,
                   shaderSourcesUnchangedDuringRun=all(sha(ROOT / name)==digest for name,digest in hashes.items()),
                   nativeBinarySHA256=sha(binary), sourceSHA256=hashes, newMinecraftRun=False,
                   actualMinecraftFrameTiming=False, fullGoalAchieved=False)
    with (OUT / "native-receipt.json").open("x") as stream: json.dump(receipt, stream, indent=2, sort_keys=True)
    print(result.stdout + result.stderr, end="")
    print("Native exit:", result.returncode, "(2=qualified RED, 1=inconclusive/error, 0=bounded response pass)")
    if result.returncode not in (0, 2): raise SystemExit(1)


if __name__ == "__main__": main()
