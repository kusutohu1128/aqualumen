"""Exclusive original-MAIN native receiver test recording; Java must be closed."""
import hashlib
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/2026-10-06-water-occluded-main"


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--revision",choices=("v1","v2","v3"),default="v3")
    revision=parser.parse_args().revision
    artifact=OUT / ("native-"+revision)
    receipt_path=OUT / ("native-receipt.json" if revision=="v1" else "native-"+revision+"-receipt.json")
    if subprocess.run(["rtk", "proxy", "pgrep", "-x", "java"], stdout=subprocess.DEVNULL).returncode != 1:
        raise ValueError("Live Java prevents native GPU validation")
    if artifact.exists() or receipt_path.exists():
        raise ValueError("Prior native evidence must not be overwritten")
    frozen = OUT / ("frozen-source" if revision=="v1" else "frozen-source-"+revision)
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
    binary = OUT / ("native-"+revision+"-probe")
    if binary.exists(): raise ValueError("Exclusive native binary already exists")
    build = subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra",
                            str(ROOT / "tools/water_occluded_receiver_main.cpp"), "-o", str(binary), "-lepoxy", "-lEGL"],
                           cwd=ROOT, capture_output=True, text=True)
    with (OUT / ("native-"+revision+"-compile.log")).open("x") as stream: stream.write(build.stdout+build.stderr)
    if build.returncode != 0: raise ValueError("Native compiler failed; do not execute")
    result = subprocess.run(["rtk", "proxy", str(binary), str(ROOT / "shaders"), str(artifact)],
                            cwd=ROOT, capture_output=True, text=True)
    with (OUT / ("native.log" if revision=="v1" else "native-"+revision+".log")).open("x") as stream: stream.write(result.stdout + result.stderr)
    receipt = dict(exitCode=result.returncode, rendererReportedByActualGL="RTX 3080 Ti" in result.stdout,
                   shaderSourcesUnchangedDuringRun=all(sha(ROOT / name)==digest for name,digest in hashes.items()),
                   nativeBinarySHA256=sha(binary), compilerExitCode=build.returncode,
                   synchronousExclusiveBinaryBuild=True, sourceSHA256=hashes, newMinecraftRun=False,
                   actualMinecraftFrameTiming=False, fullGoalAchieved=False)
    with receipt_path.open("x") as stream: json.dump(receipt, stream, indent=2, sort_keys=True)
    print(result.stdout + result.stderr, end="")
    print("Native exit:", result.returncode, "(2=qualified RED, 1=inconclusive/error, 0=bounded response pass)")
    if result.returncode not in (0, 2): raise SystemExit(1)


if __name__ == "__main__": main()
