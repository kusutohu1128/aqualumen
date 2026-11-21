"""Run retained native gates in an exclusive frozen tree, never old build evidence."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/2026-10-06-water-receiver-main/retained-regressions"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    if subprocess.run(["rtk", "proxy", "pgrep", "-x", "java"], stdout=subprocess.DEVNULL).returncode != 1:
        raise ValueError("Live Java prevents native GPU validation")
    OUT.mkdir(exist_ok=False)
    frozen = OUT / "source"
    paths = [ROOT / "Makefile", ROOT / "tools/glcheck.cpp", Path(__file__).resolve(),
             *sorted((ROOT / "tools").glob("*probe.h")), *sorted((ROOT / "shaders").rglob("*"))]
    hashes = {}
    for path in paths:
        if not path.is_file():
            continue
        name = path.relative_to(ROOT)
        target = frozen / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(path.read_bytes())
        hashes[str(name)] = sha(path)
    commands = [
        ("make-check", ["rtk", "proxy", "make", "check"]),
        ("water-radiance", ["rtk", "proxy", "build/glcheck", "shaders", "--water-radiance-only", str(OUT / "water-radiance")]),
        ("first-visible-bed-waves", ["rtk", "proxy", "build/glcheck", "shaders", "--first-visible-bed-waves-only", str(OUT / "first-visible-bed-waves")]),
    ]
    results = []
    for label, command in commands:
        actual = subprocess.run(command, cwd=frozen, capture_output=True, text=True)
        with (OUT / (label + ".log")).open("x") as stream:
            stream.write(actual.stdout + actual.stderr)
        results.append(dict(name=label, command=command, exitCode=actual.returncode,
                            actualNvidiaRenderer="RTX 3080 Ti" in actual.stdout))
        print(label, "exit", actual.returncode, flush=True)
        print(actual.stdout + actual.stderr, end="", flush=True)
        if actual.returncode != 0:
            break
    receipt = dict(runs=results, sourceSHA256=hashes, nativeBinarySHA256=sha(frozen / "build/glcheck"),
                   sourceUnchangedDuringRun=all(sha(ROOT / name) == digest for name, digest in hashes.items()),
                   actualMinecraftTimings=False, fullGoalAchieved=False)
    with (OUT / "receipt.json").open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
    if len(results) != len(commands) or any(r["exitCode"] != 0 or not r["actualNvidiaRenderer"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    run()
