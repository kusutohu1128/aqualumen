"""Exclusive actual CPU scope test sources/logs; never runs Minecraft or GL."""
import json
from pathlib import Path
import subprocess
import sys
from water_receiver_sun_audit import ROOT, sha

OUT = ROOT / "reports/2026-10-06-water-receiver-mesher"


def main(label):
    if label not in ("scope-red1", "scope-green1", "scope-final"):
        raise ValueError("Declared unique CPU scope record required")
    if (OUT / "SHA256SUMS").exists():
        raise ValueError("Packet already sealed")
    target = OUT / label
    target.mkdir(parents=True, exist_ok=False)
    names = ["physics-mod/dev/aqualumen/physics/ReceiverVertex.java",
             "tools/receiver-mesher-probe/dev/aqualumen/physics/ReceiverMesherScope.java",
             "tools/receiver-mesher-probe/test/dev/aqualumen/physics/ReceiverMesherScopeTest.java",
             "tools/test-receiver-mesher-scope.sh", "tools/water_receiver_mesher_scope_record.py"]
    hashes = {}
    for name in names:
        copy = target / "source" / name
        copy.parent.mkdir(parents=True, exist_ok=True)
        with copy.open("xb") as stream:
            stream.write((ROOT / name).read_bytes())
        hashes[name] = sha(copy)
    result = subprocess.run(["rtk", "proxy", "bash", "tools/test-receiver-mesher-scope.sh"], cwd=ROOT, capture_output=True)
    with (target / "test.log").open("xb") as stream:
        stream.write(result.stdout + result.stderr)
    with (target / "receipt.json").open("x") as stream:
        json.dump(dict(exitCode=result.returncode, sourceSHA256=hashes, syntheticCPUInputs=True,
                       actualMinecraftCapture=False, fullGoalAchieved=False), stream, indent=2, sort_keys=True)
    print((result.stdout + result.stderr).decode(), end="")
    if result.returncode != (1 if label == "scope-red1" else 0):
        raise SystemExit(1)


if __name__ == "__main__":
    main(sys.argv[1])
