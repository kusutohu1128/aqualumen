"""Measure interleaved production, mesh and radiance rows in the two-room house."""
import json
from pathlib import Path

import numpy as np
from PIL import Image


def patch_values(pixels, patch):
    x0, y0, x1, y1 = patch
    crop = pixels[y0:y1, x0:x1]
    row = (pixels.shape[0] - 1 - np.arange(y0, y1)) % 5

    def read(index, square=False):
        values = crop[row == index] / 255.0
        return np.mean(values**2 if square else values, axis=(0, 1))

    block, sky, ao = read(1)
    terrain, opaque, scene = read(2, square=True)
    ambient, sun, local = read(3, square=True)
    albedo = read(4, square=True)[0]
    _, exposure, tag = read(4)
    return dict(displayRGB8=(255 * read(0)).round(3).tolist(),
                block=block, sky=sky, ao=ao, albedoY=albedo,
                terrainY=terrain, opaqueY=opaque, sceneY=scene,
                ambientY=ambient, sunY=sun, localY=local,
                exposure=4 * exposure, tagged=tag)


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    run = base / "receiver-readback"
    done = json.loads((run / "complete.json").read_text())
    roles = {}
    for role in json.loads((run / "plan.json").read_text())["roles"]:
        with Image.open(run / (role["name"] + ".png")) as shot:
            pixels = np.asarray(shot.convert("RGB"), dtype=float)
        roles[role["name"]] = {s["name"]: patch_values(pixels, s["patch"]) for s in role["samples"]}
    result = dict(renderer=done["renderer"], sha256=done["sha256"],
                  measurement="Adjacent rows; decode square-root radiance per pixel before averaging. First row retains production display.",
                  roles=roles)
    (base / "receiver-stage-results.json").write_text(json.dumps(result, indent=2) + "\n")
