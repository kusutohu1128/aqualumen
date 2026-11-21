"""Read mesh inputs and radiance from alternating raw diagnostic rows in the same patch."""
from pathlib import Path
import json
import re

import numpy as np
from PIL import Image


here = Path(__file__).resolve().parent
folder = here / "mesh-readback"
plan = json.loads((folder / "plan.json").read_text())
log = (folder / "client.log").read_text()
renderer = re.search(r"OpenGL Renderer: ([^\n]+)", log).group(1)
assert renderer.startswith("NVIDIA GeForce RTX 3080 Ti") and "Using shaderpack: " + plan["pack"] in log
assert not any(flag in log for flag in ("AQD_DRIFT_", "AQD_FAIL_", "AQD_ABORT_", "Reverting to default"))
def clock(stamp):
    return sum(int(i)*n for i,n in zip(stamp.split(":"),(3600,60,1)))

ready = re.search(r"^\[(\d\d:\d\d:\d\d)\] \[Render thread/INFO\]: Started [1-9]\d* worker threads", log[log.index("Creating pipeline for dimension minecraft:overworld"):], re.M)
since = clock(ready.group(1))
events = [(clock(h), kind, role) for h,kind,role in re.findall(
    r"^\[(\d\d:\d\d:\d\d)\].*?AQD_(BEGIN|READY)_([a-z-]+)_END", log, re.M)]
candidates = {}
for frame in json.loads((folder / "timeline/timeline.json").read_text()):
    t = clock(frame["clock"])
    if t < since + 10:
        continue
    earlier = [e for e in events if e[0] <= t]
    if earlier:
        at, kind, role = earlier[-1]
        if kind == "READY" and 1 <= t-at <= 5 and frame["size"] == [1280,720]:
            candidates.setdefault(role,[]).append(frame["file"])
assert set(candidates)=={r["name"] for r in plan["roles"]}
shots = {role: names[-1] for role,names in candidates.items()}

by_role = {}
for row in plan["roles"]:
    with Image.open(folder / "timeline" / shots[row["name"]]) as im:
        rgb = np.asarray(im.convert("RGB")).astype(float) / 255.0
    patches = {}
    for sample in row["samples"]:
        x0, y0, x1, y1 = sample["patch"]
        rect = rgb[y0:y1, x0:x1, :]
        raw_rows = (rgb.shape[0] - 1 - np.arange(y0, y1)) % 2 == 0
        mesh = rect[raw_rows].mean(axis=(0, 1))
        # Decode each pixel prior to averaging. Energies >=1 saturate in the diagnostic.
        hdr = np.square(rect[~raw_rows]).mean(axis=(0, 1))
        patches[sample["name"]] = dict(zip(
            ("blockLight", "skyLight", "vertexAO", "localLightY", "directSunY", "remainingY"),
            [round(float(val), 6) for val in [*mesh, *hdr]]))
    by_role[row["name"]] = patches
with (here / "mesh-light-results.json").open("x") as f:
    json.dump(dict(diagnosticSHA=plan["packSha256"], renderer=renderer, roles=by_role, photos=shots,
                   frameSelection="native private Minecraft window 1..5 s after server-verified READY and 10+ s after worker startup; final shader displays raw values",
                   channels="even GL rows: mesh inputs (block, sky, AO); odd rows: sqrt of placed/held plus bounced light, direct Sun, remaining opaque radiance; JPEG-free 8-bit readback"),
              f, ensure_ascii=False, indent=2)
for role, patches in by_role.items():
    print(role, patches["soul"])
