"""Native-only receiver regression lifecycle: fresh baseline and private normal relaunch."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/2026-10-06-water-occluded-main"
GAME = Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft")


def closed():
    if subprocess.run(["rtk", "proxy", "pgrep", "-x", "java"], stdout=subprocess.DEVNULL).returncode != 1:
        raise ValueError("Native validation requires a closed client")


def baseline():
    closed()
    if "All dimensions are saved" not in (GAME / "logs/latest.log").read_text():
        raise ValueError("Clean ordinary Save/Quit not proven")
    OUT.mkdir(exist_ok=False)
    cache = Path(tempfile.mkdtemp(prefix="aqualumen-legacy-branch-host-occluded-main-", dir="/home/kusutohu/.cache"))
    for name in ("options.txt", "config/iris.properties", "config/aqualumen-benchmark.properties"):
        target = cache / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(GAME / name, target)
    value = subprocess.check_output(["rtk", "proxy", "python3", "tools/water_legacy_branch_snapshot.py", str(cache)], cwd=ROOT)
    with (OUT / "fresh-normal-baseline.json").open("xb") as stream: stream.write(value)
    shutil.copy2(GAME / "logs/latest.log", OUT / "normal-clean-save-exit.log")
    for stamp in ("15.01.41", "15.01.47", "15.02.16"):
        shutil.copy2(GAME / "screenshots" / f"2026-10-06_{stamp}.png", OUT / f"2026-10-06_{stamp}.png")
    print("Fresh clean post-save baseline:", cache)


def normal():
    closed()
    baseline = json.loads((OUT / "fresh-normal-baseline.json").read_text())
    cache = Path(baseline["backup"])
    observed = json.loads(subprocess.check_output(["rtk", "proxy", "python3", "tools/water_legacy_branch_snapshot.py", str(cache)], cwd=ROOT))
    if observed != baseline: raise ValueError("Native-only workflow modified ordinary state")
    with (OUT / "normal-unchanged-before-reopening.json").open("x") as stream: json.dump(observed, stream, indent=2)
    descriptor = os.open(cache / "launcher-private.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    print("NORMAL launch; native-only workflow, original config/JAR/save bytes exact", flush=True)
    with os.fdopen(descriptor, "wb") as log:
        result = subprocess.run(["rtk", "proxy", "flatpak", "run", "--command=prismrun", "org.prismlauncher.PrismLauncher",
                                 "--launch", "Aqualumen Lab", "--world", "新規ワールド"], cwd=ROOT,
                                env=dict(os.environ, DISPLAY=":1"), stdout=log, stderr=subprocess.STDOUT)
    print("NORMAL LAUNCHER EXIT", result.returncode, flush=True)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    import sys
    {"baseline": baseline, "normal": normal}[sys.argv[1]]()
