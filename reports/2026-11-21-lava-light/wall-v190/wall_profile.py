"""Compare the matched white wall by predicted visibility, using original F2 display values."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from compare import ray_box
from PIL import Image


def normalized(vec):
    return vec / np.linalg.norm(vec)


def samples(geometry, width, height):
    eye = np.array(geometry["eye"])
    forward = normalized(np.array(geometry["target"]) - eye)
    right = normalized(np.cross(forward, [0, 1, 0]))
    up = np.cross(right, forward)
    x, y = np.meshgrid(
        np.linspace(199.35, 207.85, 116), np.linspace(173.35, 177.85, 64)
    )
    wall = np.stack([x, y, np.full_like(x, geometry["wallZ"])], axis=-1)
    rays = wall - eye
    scale = height / (2 * np.tan(np.deg2rad(35)) * (rays @ forward))
    col = np.floor(width / 2 + scale * (rays @ right)).astype(int)
    row = np.floor(height / 2 - scale * (rays @ up)).astype(int)
    within = (col >= 0) & (col < width) & (row >= 0) & (row < height)
    lo, hi = np.asarray(geometry["pillar"], dtype=float)
    # Restrict analysis to the wall visible in both images, away from silhouette edges.
    seen = within & ~ray_box(eye, wall, lo - 0.06, hi + 1.06)
    return wall[seen], row[seen], col[seen], lo, hi + 1


def source_fraction(wall, half, lo, hi):
    step = ((np.arange(64) + 0.5) / 64 * 2 - 1) * half
    x, z = np.meshgrid(202.5 + step, 361.5 + step)
    lamps = np.stack([x, np.full_like(x, 172 + 55 / 62), z], axis=-1).reshape(-1, 3)
    fractions = []
    for start in range(0, len(wall), 32):
        p = wall[start : start + 32, None, :]
        ray = lamps - p
        rim = p + ray * ((173 - p[..., 1]) / ray[..., 1])[..., None]
        mouth = (np.abs(rim[..., 0] - 202.5) <= half) & (
            np.abs(rim[..., 2] - 361.5) <= half
        )
        energy = mouth * (ray[..., 1] * ray[..., 2]) / (ray**2).sum(axis=-1) ** 2
        full = energy.sum(axis=1)
        lit = (energy * (~ray_box(p, lamps, lo, hi))).sum(axis=1)
        fractions.append(
            np.divide(lit, full, out=np.full_like(lit, np.nan), where=full > 0)
        )
    return np.concatenate(fractions)


def profile(directory, baseline):
    evidence = json.loads((directory / "complete.json").read_text())
    g = json.loads((directory / "geometry.json").read_text())
    if baseline:
        g["pillar"] = [[202, 173, 364], [202, 175, 364]]
    else:
        assert evidence["complete"] and evidence["originalWorldAndConfigUnchanged"]
    data = {}
    for stage in (
        "dark",
        "dark-pillar",
        "lava1-open",
        "lava1-pillar",
        "lava9-open",
        "lava9-pillar",
    ):
        key = (
            stage.replace("lava1", "one").replace("lava9", "nine")
            if baseline
            else stage
        )
        file = directory / (key + (".png" if baseline else "-ingame.png"))
        expected = evidence["screenshots"][key]
        if not baseline:
            expected = expected["ingame"]
        assert hashlib.sha256(file.read_bytes()).hexdigest() == expected
        with Image.open(file) as im:
            if not data:
                wall, row, col, lo, hi = samples(g, *im.size)
            data[stage] = np.asarray(im.convert("RGB"), dtype="f4")[row, col]
    output = {}
    for n in (1, 9):
        f = source_fraction(wall, n**0.5 / 2, lo, hi)
        on_open = data[f"lava{n}-open"] - data["dark"]
        on_pillar = data[f"lava{n}-pillar"] - data["dark-pillar"]
        contrast = on_pillar - on_open
        bins = [
            (-0.01, 0.01),
            (0.01, 0.25),
            (0.25, 0.50),
            (0.50, 0.75),
            (0.75, 0.99),
            (0.99, 1.01),
        ]
        results = []
        for a, b in bins:
            keep = (f >= a) & (f < b)
            if keep.any():
                results.append(
                    {
                        "visibleFraction": [max(0, a), min(1, b)],
                        "points": int(keep.sum()),
                        "addingLavaOpenRGB": np.median(on_open[keep], axis=0).tolist(),
                        "addingLavaBehindPillarRGB": np.median(
                            on_pillar[keep], axis=0
                        ).tolist(),
                        "differenceOfDifferencesRGB": np.median(
                            contrast[keep], axis=0
                        ).tolist(),
                    }
                )
        output[str(n)] = results
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--baseline", action="store_true")
    args = p.parse_args()
    values = profile(args.directory, args.baseline)
    with args.output.open("x") as f:
        json.dump(
            {
                "scope": "Uniform samples of the screen-visible white wall in world space. Bins use 4096 area samples, stone pillar and recessed lip. Channel values are display RGB; the camera adaptation and indirect illumination remain active.",
                "samples": values,
            },
            f,
            indent=2,
        )
        f.write("\n")


if __name__ == "__main__":
    main()
