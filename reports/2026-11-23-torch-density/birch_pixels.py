"""Sample registered F2 regions from the same daylight camera at each source count."""
import json
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
# Inside the white trunk and inside the far sunlit grass. Both avoid flames and sky.
REGIONS = {"shadedBark": (770, 390, 925, 760), "distantGrass": (1580, 895, 1740, 960)}


def main():
    captures = {}
    for run in ("gp-density-p8-a", "gp-density-tiles-a-retry1"):
        folder = HERE / run
        receipt = json.loads((folder / "complete.json").read_text())
        results = {}
        for name in receipt["stages"]:
            if not name.startswith("birch-"):
                continue
            with Image.open(folder / f"{name}-ingame.png") as frame:
                assert frame.size == (2560, 1440)
                regions = {}
                for region, box in REGIONS.items():
                    rgb = np.asarray(frame.crop(box).convert("RGB")).reshape(-1, 3)
                    regions[region] = {"median":np.median(rgb, axis=0).tolist(),
                                       "mean":np.mean(rgb, axis=0).round(2).tolist()}
                results[name] = regions
        captures[run] = {"pack":receipt["packSha256"],"scenes":results}
    (HERE / "birch-pixels.json").write_text(json.dumps(dict(boxes=REGIONS,captures=captures),indent=2)+"\n")
    for run, group in captures.items():
        print(run, {s:[r[v]["median"] for v in REGIONS] for s,r in group["scenes"].items()})


if __name__ == "__main__":
    main()
