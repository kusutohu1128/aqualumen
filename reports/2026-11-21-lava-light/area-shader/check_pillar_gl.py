"""Check the candidate fragment library off screen against analytic and area-sampled values."""

import argparse
import hashlib
import json
import os
import subprocess

import numpy as np
from pillar_reference import (
    FACES,
    HERE,
    NORMAL,
    PILLAR_HI,
    PILLAR_LO,
    blocked_footprint,
    irradiance,
    pool_geometry,
    through_rim,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("probe", help="gl_probe.cpp compiled with libepoxy")
    parser.add_argument("--mesa", action="store_true")
    args = parser.parse_args()
    measurement = json.loads((HERE / "pillar-results.json").read_text())
    captures = json.loads(FACES.read_text())["samples"]
    pools = {
        width: pool_geometry(captures[stage])
        for width, stage in [(1, "one-pillar"), (3, "nine-pillar")]
    }
    samples = [
        (row["poolWidth"], row["wall"], row["box"], row["quadrature"])
        for row in measurement["checks"]
    ]
    # Face- and edge-aligned receiver positions exercise exact zero bounds.
    for x in (201.8, 202.0, 202.5, 203.0, 203.2):
        for y in (173.2, 175.9, 176.0, 176.1):
            samples.append((3, (x, y), "pillar", None))
    samples.append((3, (202.5, 175.0), "receiver-inside", None))
    transforms = [
        np.eye(3),
        np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]]),
        np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]),
    ]
    inputs, expected = [], []
    for width, (x, y), box, reference in samples:
        receiver = np.array([x, y, 366.0])
        polygon = through_rim(pools[width], receiver)
        if len(polygon) < 3:
            continue
        offset = {
            "pillar": 0.0,
            "behind-wall": 8.0,
            "past-pool": -10.0,
            "receiver-inside": 1.5,
        }[box]
        lo, hi = PILLAR_LO - receiver, PILLAR_HI - receiver
        lo[2] += offset
        hi[2] += offset
        clear = irradiance(polygon)
        direct = clear - irradiance(blocked_footprint(polygon, np.zeros(3), lo, hi))
        if box == "receiver-inside":
            assert abs(direct) < 1e-12
        if box in ("past-pool", "behind-wall"):
            assert abs(direct - clear) < 1e-12
        for matrix in transforms:
            rotated_box = np.stack([matrix @ lo, matrix @ hi])
            begin = len(inputs)
            for i in range(1, len(polygon) - 1):
                triangle = polygon[[0, i, i + 1]] @ matrix.T
                data = np.vstack(
                    [
                        triangle,
                        matrix @ NORMAL,
                        rotated_box.min(axis=0),
                        rotated_box.max(axis=0),
                    ]
                )
                inputs.append(" ".join(f"{v:.12g}" for v in data.flat))
            expected.append((begin, len(inputs), direct, clear, reference))

    vendor = "50_mesa.json" if args.mesa else "10_nvidia.json"
    env = dict(
        os.environ,
        __EGL_VENDOR_LIBRARY_FILENAMES="/usr/share/glvnd/egl_vendor.d/" + vendor,
        EGL_PLATFORM="surfaceless",
        LP_NUM_THREADS="2",
    )
    if args.mesa:
        env["LIBGL_ALWAYS_SOFTWARE"] = "1"
    base, pillar = HERE / "lava_irradiance.glsl", HERE / "lava_pillar.glsl"
    run = subprocess.run(
        [args.probe, str(base), str(pillar)],
        input="\n".join(inputs) + "\n",
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    values = np.fromstring(run.stdout, sep=" ")
    assert len(values) == len(inputs) and np.isfinite(values).all()
    analytic_errors, quadrature_errors = [], []
    for begin, end, direct, clear, quadrature in expected:
        observed = values[begin:end].sum()
        analytic_errors.append(float(abs(observed - direct) / clear))
        if quadrature is not None:
            quadrature_errors.append(float(abs(observed - quadrature) / clear))
    assert max(analytic_errors) < 0.0002 and max(quadrature_errors) < 0.01
    record = {
        "renderer": run.stderr.strip(),
        "sceneOrientations": len(transforms),
        "cases": len(expected),
        "triangles": len(inputs),
        "quadratureComparisons": len(quadrature_errors),
        "maxDifferenceFromClippedPolygonRelativeToOpen": max(analytic_errors),
        "maxDifferenceFromAreaQuadratureRelativeToOpen": max(quadrature_errors),
        "sources": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [base, pillar]
        },
        "scope": "Standalone OpenGL integral; actual observed lava top, one pillar, pool rim. No Minecraft integration.",
    }
    print(json.dumps(record, indent=2))
    suffix = "mesa" if args.mesa else "nvidia"
    (HERE / f"pillar-{suffix}.json").write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
