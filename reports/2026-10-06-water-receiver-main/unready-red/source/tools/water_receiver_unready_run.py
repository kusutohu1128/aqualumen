"""One external-data-only control: first geometry known, first source unavailable.

Keep the original closed-box oracle, pixels, shader options and pass/fail code.
The only fixture edit makes near-bed source alpha unready; the far bed is ready.
Every run has an exclusive frozen source tree and synchronously built binary.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/2026-10-06-water-receiver-main"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(label):
    if label not in ("unready-red", "unready-green"):
        raise ValueError("Exclusive declared run label required")
    if subprocess.run(["rtk", "proxy", "pgrep", "-x", "java"], stdout=subprocess.DEVNULL).returncode != 1:
        raise ValueError("Live Java prevents native validation")
    target = OUT / label
    target.mkdir(exist_ok=False)
    frozen = target / "source"
    paths = [ROOT / "tools/water_occluded_receiver_main.cpp", ROOT / "tools/glcheck.cpp",
             Path(__file__).resolve(), *sorted((ROOT / "tools").glob("*probe.h")),
             *sorted((ROOT / "shaders").rglob("*"))]
    hashes = {}
    for path in paths:
        if not path.is_file():
            continue
        name = path.relative_to(ROOT)
        copy = frozen / name
        copy.parent.mkdir(parents=True, exist_ok=True)
        with copy.open("xb") as stream:
            stream.write(path.read_bytes())
        hashes[str(name)] = sha(path)
    original = (frozen / "tools/water_occluded_receiver_main.cpp").read_text()
    before = "source[q+3]=opaque?1:0;"
    after = "source[q+3]=(opaque && center[2]<-4)?1:0;"
    if original.count(before) != 1:
        raise ValueError("External source-readiness fixture seam changed")
    fixture = frozen / "tools/water_receiver_unready_fixture.cpp"
    with fixture.open("x") as stream:
        stream.write(original.replace(before, after))
    binary = target / "probe"
    compile = subprocess.run(["rtk", "proxy", "g++", "-std=c++17", "-O2", "-Wall", "-Wextra",
                              str(fixture), "-o", str(binary), "-lepoxy", "-lEGL"],
                             cwd=ROOT, capture_output=True, text=True)
    with (target / "compile.log").open("x") as stream:
        stream.write(compile.stdout + compile.stderr)
    if compile.returncode != 0:
        raise ValueError("Compiler failed: never execute an old binary")
    result = subprocess.run(["rtk", "proxy", str(binary), str(frozen / "shaders"), str(target / "raw")],
                            cwd=ROOT, capture_output=True, text=True)
    with (target / "native.log").open("x") as stream:
        stream.write(result.stdout + result.stderr)
    receipt = dict(exitCode=result.returncode, compilerExitCode=compile.returncode,
                   synchronousExclusiveBinaryBuild=True, nativeBinarySHA256=sha(binary),
                   externalFixtureChange=dict(before=before, after=after),
                   externalFixtureSHA256=sha(fixture), sourceSHA256=hashes,
                   sourceUnchangedDuringRun=all(sha(ROOT / name) == digest for name, digest in hashes.items()),
                   newMinecraftRun=False, liveMinecraftProducer=False, fullGoalAchieved=False)
    with (target / "receipt.json").open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
    print(result.stdout + result.stderr, end="")
    print("Native exit:", result.returncode, "(2=qualified first-source RED, 0=bounded response pass)")
    if result.returncode not in (0, 2):
        raise SystemExit(1)


if __name__ == "__main__":
    run(sys.argv[1])
