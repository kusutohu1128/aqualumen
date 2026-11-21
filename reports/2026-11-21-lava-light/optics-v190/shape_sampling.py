"""Evaluate finite-area visibility on the real basin geometry using independent double-precision polygons."""

import json
import sys
from pathlib import Path

import numpy as np

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent / "area-shader"))
from pillar_reference import (
    FACES,
    PILLAR_HI,
    PILLAR_LO,
    blocked_footprint,
    irradiance,
    pool_geometry,
    through_rim,
)


def shot(surface, receivers, uv):
    # Relative contribution of each emitting sample to a white Z-facing wall.
    origin = receivers.copy()
    origin[:, 2] -= 0.012
    target = (
        surface[0]
        + uv[:, 0, None] * (surface[1] - surface[0])
        + uv[:, 1, None] * (surface[3] - surface[0])
    )
    delta = target[None, :, :] - receivers[:, None, :]
    weight = (
        np.maximum(-delta[:, :, 1], 0)
        * np.maximum(-delta[:, :, 2], 0)
        / np.sum(delta**2, axis=2) ** 2
    )
    target[:, 1] += 0.001
    ray = target[None, :, :] - origin[:, None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        a = (PILLAR_LO - origin[:, None, :]) / ray
        b = (PILLAR_HI - origin[:, None, :]) / ray
    hit = np.maximum(0, np.minimum(a, b).max(axis=2)) < np.minimum(
        1, np.maximum(a, b).min(axis=2)
    )
    t = (173 - origin[:, 1, None]) / ray[:, :, 1]
    edge = origin[:, None, :] + t[:, :, None] * ray
    rim = (
        (edge[:, :, 0] >= surface[0, 0])
        & (edge[:, :, 0] <= surface[2, 0])
        & (edge[:, :, 2] >= surface[0, 2])
        & (edge[:, :, 2] <= surface[2, 2])
    )
    return weight, (~hit) & rim


def main():
    data = json.loads(FACES.read_text())["samples"]
    x, y = np.meshgrid(np.linspace(199.4, 205.8, 100), np.linspace(177.3, 173.7, 38))
    rec = np.stack([x, y, np.full_like(x, 366.0)], axis=-1).reshape(-1, 3)
    pilot = np.array([(u, v) for v in (0.25, 0.75) for u in (0.25, 0.75)])
    k = np.arange(16)
    jitter = np.stack(
        [(k * 0.61803399 + 0.21) % 1, (k * 0.41421356 + 0.39) % 1], axis=-1
    )
    fine = (np.stack([k % 4, k // 4], axis=-1) + 0.17 + 0.66 * jitter) / 4.0
    doc = {}
    for name in ("one-pillar", "nine-pillar"):
        surface = pool_geometry(data[name])
        w0, t0 = shot(surface, rec, pilot)
        w1, t1 = shot(surface, rec, fine)
        mixed = t0.any(axis=1) & ~t0.all(axis=1)
        estimate = np.where(
            mixed,
            np.sum(w1 * t1, axis=1) / w1.sum(axis=1),
            np.sum(w0 * t0, axis=1) / w0.sum(axis=1),
        )
        refs = []
        for receiver in rec:
            all_energy = irradiance(surface - receiver)
            lit = through_rim(surface, receiver)
            refs.append(
                (
                    irradiance(lit)
                    - irradiance(blocked_footprint(lit, receiver, PILLAR_LO, PILLAR_HI))
                )
                / all_energy
            )
        truth = np.array(refs)
        e = np.abs(truth - estimate)
        pen = (truth > 0.015) & (truth < 0.985)
        doc[name] = {
            "pixels": len(rec),
            "penumbraPixels": int(pen.sum()),
            "p95AbsVisibilityError": float(np.quantile(e, 0.95)),
            "p95Penumbra": float(np.quantile(e[pen], 0.95)),
            "max": float(e.max()),
            "mean": float(e.mean()),
            "missedByUniformPilots": int(((~mixed) & (e > 0.10)).sum()),
            "scope": "CPU reconstruction of preview1 stratified footprint, one horizontal emitter patch and a recessed rim, without exposure or bounce",
        }
    (here / "preview1-visibility.json").write_text(json.dumps(doc, indent=2) + "\n")
    print(doc)


if __name__ == "__main__":
    main()
