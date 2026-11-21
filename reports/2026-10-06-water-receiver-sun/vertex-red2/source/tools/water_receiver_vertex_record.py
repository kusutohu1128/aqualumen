"""Persist each tiny public-API RED/GREEN increment and its exact source."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/2026-10-06-water-receiver-sun"
GAME = Path("/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(label):
    if label not in ("vertex-red1", "vertex-green1", "vertex-red2", "vertex-green2", "vertex-red3", "vertex-green3", "vertex-final"):
        raise ValueError("Declared exclusive CPU increment required")
    target = OUT / label
    target.mkdir(exist_ok=False)
    paths = [ROOT / "physics-mod/dev/aqualumen/physics/ReceiverVertex.java",
             ROOT / "physics-mod/test/dev/aqualumen/physics/ReceiverVertexTest.java",
             ROOT / "tools/test-receiver-vertex.sh", Path(__file__).resolve()]
    hashes = {}
    for path in paths:
        name = path.relative_to(ROOT)
        copy = target / "source" / name
        copy.parent.mkdir(parents=True, exist_ok=True)
        with copy.open("xb") as stream:
            stream.write(path.read_bytes())
        hashes[str(name)] = sha(path)
    result = subprocess.run(["rtk", "proxy", "bash", "tools/test-receiver-vertex.sh"], cwd=ROOT, capture_output=True, text=True)
    with (target / "test.log").open("x") as stream:
        stream.write(result.stdout + result.stderr)
    receipt = dict(exitCode=result.returncode, sourceSHA256=hashes,
                   actualPinnedSodiumJarSHA256=sha(GAME / "mods/sodium-fabric-0.6.9+mc1.21.1.jar"),
                   actualInstalledLibraryReference=True, inputVerticesAreSynthetic=True,
                   actualMinecraftLightCapture=False, shadedSource=False, fullGoalAchieved=False)
    with (target / "receipt.json").open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
    print(result.stdout + result.stderr, end="")
    if ("red" in label and result.returncode == 0) or ("red" not in label and result.returncode != 0):
        raise SystemExit(1)


if __name__ == "__main__":
    record(sys.argv[1])
