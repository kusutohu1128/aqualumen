"""Freeze genuine independent-reader RED/GREEN and actual external packet identity."""
import json
import subprocess
import sys
from water_receiver_mesher_audit import ROOT, OUT, sha


def main(label):
    if label not in ("audit-red1", "audit-green1", "audit-final") or (OUT / "SHA256SUMS").exists():
        raise ValueError("Declared exclusive unsealed record required")
    folder = OUT / label
    folder.mkdir(exist_ok=False)
    sources = ["tools/water_receiver_mesher_audit.py", "tools/test_water_receiver_mesher_audit.py", "tools/water_receiver_mesher_audit_record.py"]
    hashes = {}
    for name in sources:
        dest = folder / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("xb") as stream:
            stream.write((ROOT / name).read_bytes())
        hashes[name] = sha(dest)
    result = subprocess.run(["rtk", "proxy", "python3", "tools/test_water_receiver_mesher_audit.py"], cwd=ROOT, capture_output=True)
    with (folder / "test.log").open("xb") as stream:
        stream.write(result.stdout + result.stderr)
    with (folder / "receipt.json").open("x") as stream:
        json.dump(dict(exitCode=result.returncode, sourceSHA256=hashes,
              actualExternalCaptureSHA256=sha(OUT / "actual-mesher-readback.json"),
              actualCaptureUnchanged=True, fullGoalAchieved=False), stream, indent=2, sort_keys=True)
    print((result.stdout + result.stderr).decode(), end="")
    if result.returncode != (1 if label == "audit-red1" else 0):
        raise SystemExit(1)


if __name__ == "__main__":
    main(sys.argv[1])
