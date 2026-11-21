"""Independent saved actual mesh-input/output reader; no live/native GL replay."""
import json
import math
from pathlib import Path
import struct
from water_receiver_sun_audit import ROOT, sha

OUT = ROOT / "reports/2026-10-06-water-receiver-mesher"


def audit(out=OUT):
    raise ValueError("Actual mesher input/output ownership and encoding have not been independently qualified")


if __name__ == "__main__":
    result = audit()
    with (OUT / "independent-mesher-audit.json").open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    print(json.dumps(result, sort_keys=True))
