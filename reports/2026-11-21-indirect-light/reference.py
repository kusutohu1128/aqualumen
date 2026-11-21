"""Independent, one-bounce area integral for a hooded lantern and two diffuse walls.
Coordinates in metres. The result is irradiance per unit lamp intensity, not a framebuffer or FPS.
"""

import io
import json
import math
import sys
import zipfile
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SOURCE = np.array([9.5, 2.5, 4.5])
RECEIVERS = np.array([[8, 2.5, 0], [9.5, 2.5, 0], [11, 2.5, 0]])
HOOD = [
    ((9, 2, 3), (10, 3, 4)),
    ((9, 2, 5), (10, 3, 6)),
    ((8, 2, 4), (9, 3, 5)),
    ((9, 1, 4), (10, 2, 5)),
    ((9, 3, 4), (10, 4, 5)),
]
WARM = np.array([1.0, 0.49, 0.19])
SOUL = np.array([0.11, 0.65, 1.0])


def blocked(start, targets, boxes):
    delta = targets - start
    hits = np.zeros(delta.shape[:-1], bool)
    for lo, hi in boxes:
        enter = np.zeros_like(hits, float)
        leave = np.ones_like(hits, float)
        valid = np.ones_like(hits, bool)
        for axis in range(3):
            d = delta[..., axis]
            parallel = np.abs(d) < 1e-13
            denom = np.where(parallel, 1.0, d)
            a = (lo[axis] - start[axis]) / denom
            b = (hi[axis] - start[axis]) / denom
            valid &= ~parallel | ((lo[axis] < start[axis]) & (start[axis] < hi[axis]))
            enter = np.maximum(enter, np.where(parallel, -np.inf, np.minimum(a, b)))
            leave = np.minimum(leave, np.where(parallel, np.inf, np.maximum(a, b)))
        hits |= valid & (leave > enter + 1e-10)
    return hits


def transport(samples, boxes):
    y, z = np.meshgrid(
        (np.arange(7 * samples) + 0.5) / samples,
        (np.arange(10 * samples) + 0.5) / samples,
        indexing="ij",
    )
    face = np.stack((np.full(y.shape, 12.0), y, z), axis=-1)
    toLamp = SOURCE - face
    dist = np.linalg.norm(toLamp, axis=-1)
    direct = np.maximum(-toLamp[..., 0], 0) / dist**3
    direct[blocked(SOURCE, face, boxes)] = 0
    result = []
    for receiver in RECEIVERS:
        toReceiver = receiver - face
        d2 = np.sum(toReceiver**2, axis=-1)
        geom = (
            np.maximum(-toReceiver[..., 0], 0)
            * np.maximum(-toReceiver[..., 2], 0)
            / d2**2
        )
        geom[blocked(receiver, face, boxes)] = 0
        result.append(float(np.sum(direct * geom) / (math.pi * samples * samples)))
    return np.array(result)


def spectrum(jar):
    out = {}
    with zipfile.ZipFile(jar) as z:
        for name in [
            "red_concrete",
            "black_concrete",
            "gray_concrete",
            "light_gray_concrete",
            "white_concrete",
            "smooth_stone",
            "stone",
            "andesite",
            "polished_deepslate",
            "deepslate",
        ]:
            raw = z.read("assets/minecraft/textures/block/" + name + ".png")
            im = np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"), float) / 255
            out[name] = (im**2.2).mean(axis=(0, 1))
    return out


if __name__ == "__main__":
    pigments = spectrum(sys.argv[1])
    luma = np.array([0.2126, 0.7152, 0.0722])
    gray = min(
        (n for n in pigments if n not in ("red_concrete", "black_concrete")),
        key=lambda n: abs((pigments[n] - pigments["red_concrete"]) @ luma),
    )
    assert np.all(blocked(SOURCE, RECEIVERS, HOOD))
    for dx in (-0.13, 0, 0.13):
        for dz in (-0.13, 0, 0.13):
            assert blocked(SOURCE + [dx, 0, dz], RECEIVERS, HOOD).all()
    coarse = transport(24, HOOD)
    fine = transport(64, HOOD)
    first = transport(24, HOOD + [((10, 0, 1), (11, 7, 9))])
    second = transport(24, HOOD + [((6, 0, 1), (12, 7, 2))])
    assert np.all(fine > 0) and np.max(np.abs(coarse / fine - 1)) < 0.015
    assert np.all(first == 0) and np.all(second == 0)

    def bounced(rho, color):
        return (fine[:, None] * rho * color).round(8).tolist()

    result = dict(
        type="offline first-bounce irradiance integral; no game or GPU rendering",
        lamp=SOURCE.tolist(),
        receivers=RECEIVERS.tolist(),
        neutral=gray,
        meanLinearDiffuse={n: p.tolist() for n, p in pigments.items()},
        lightOff=bounced(pigments["red_concrete"], 0),
        redWarm=bounced(pigments["red_concrete"], WARM),
        neutralWarm=bounced(pigments[gray], WARM),
        redSoul=bounced(pigments["red_concrete"], SOUL),
        redBoth=bounced(pigments["red_concrete"], WARM + SOUL),
        blackWarm=bounced(pigments["black_concrete"], WARM),
        directBlocked=True,
        firstLegBlocked=first.tolist(),
        secondLegBlocked=second.tolist(),
        quadrature24=coarse.tolist(),
        quadrature64=fine.tolist(),
        nominalSpectra="normalized emitter RGB, mean atlas reflectance using pack gamma 2.2; no measured material or unit calibration",
    )
    (HERE / "transport.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "neutral:",
        gray,
        "relative convergence:",
        np.max(np.abs(coarse / fine - 1)),
        "fully blocked:",
        first.tolist(),
        second.tolist(),
    )
