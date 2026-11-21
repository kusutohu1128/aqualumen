"""Run the real source/voxel classifier on both GL drivers; compare full, partial and absent stone to an independent integral."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent / "area-shader"))
from pillar_reference import (
    FACES,
    NORMAL,
    PILLAR_HI,
    PILLAR_LO,
    blocked_footprint,
    irradiance,
    pool_geometry,
    through_rim,
)

BASE = np.array([176, 144, 336])
HEIGHT_CODE = 56
SY = 172 + (HEIGHT_CODE - 1) / 62


def set_cell(field, x, y, z, word, height=None):
    x, y, z = np.array([x, y, z]) - BASE
    idx = x + 64 * (z + 64 * y)
    field[idx // 512, idx % 512] = word
    if height is not None:
        field[512 + idx // 512, idx % 512] = height


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shaders", type=Path)
    parser.add_argument("binary", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    lib = args.shaders / "lib"
    sources = {
        k: (lib / (k + ".glsl")).read_text()
        for k in [
            "local_light_grid",
            "lava_grid",
            "lava_intersection",
            "lava_silhouette",
        ]
    }
    source = (
        "#version 430 core\nuniform sampler2D aqualumenLightField;\n"
        + "\n".join(
            v.replace('#include "/lib/lava_grid.glsl"', "") for v in sources.values()
        )
        + """
layout(local_size_x=64) in;
layout(std430,binding=0) readonly buffer Q { vec4 points[]; };
layout(std430,binding=1) writeonly buffer R { vec2 results[]; };
void main() {
    uint i=gl_GlobalInvocationID.x;
    if(i>=uint(results.length())) return;
    vec4 r=points[3u*i],n=points[3u*i+1u],limits=points[3u*i+2u];
    float irradiance=0.;
    bool simple=lavaSimpleShadow(r.xyz,n.xyz,limits.xy,limits.zw,r.w,irradiance);
    // A rejected shape goes through the colored ray tracer in production.
    // The analytic helper only defines its irradiance output on success.
    results[i]=vec2(simple?1.:0.,simple?irradiance:0.);
}
"""
    )
    captures = json.loads(FACES.read_text())["samples"]
    xs, ys = np.meshgrid(
        np.linspace(199.41, 205.81, 80), np.linspace(177.29, 173.71, 30)
    )
    receivers = np.stack([xs, ys, np.full_like(xs, 366.0)], axis=-1).reshape(-1, 3)
    doc = {
        "sourceHashes": {
            k: hashlib.sha256(v.encode()).hexdigest() for k, v in sources.items()
        },
        "drivers": {},
    }
    with tempfile.TemporaryDirectory() as work:
        tmp = Path(work)
        shader = tmp / "source.csh"
        shader.write_text(source)
        for width, key in [(1, "one-pillar"), (3, "nine-pillar")]:
            surface = pool_geometry(captures[key])
            surface[:, 1] = SY
            groups = [("open", None), ("pillar", 1), ("glass", 16), ("cutout", 2)]
            for scene, material in groups:
                field = np.zeros((1024, 512), dtype="f4")

                for x in range(198, 210):
                    for z in range(359, 368):
                        for y in range(172, 181):
                            if (
                                x in (198, 209)
                                or z in (359, 366, 367)
                                or y in (172, 180)
                            ):
                                set_cell(field, x, y, z, 1)
                for v in captures[key]:
                    if v["path"]:
                        set_cell(
                            field,
                            v["x"],
                            172,
                            v["z"],
                            10 | (1 << 6),
                            266305 * HEIGHT_CODE,
                        )
                if material is not None:
                    for y in range(173, 176):
                        set_cell(field, 202, y, 364, material)
                field.tofile(tmp / "field.bin")
                lo = surface[0, [0, 2]] - BASE[[0, 2]]
                hi = surface[2, [0, 2]] - BASE[[0, 2]]
                queries = np.empty((len(receivers), 12), dtype="f4")
                queries[:, :3] = receivers - BASE
                queries[:, 3] = SY - BASE[1]
                queries[:, 4:7] = NORMAL
                queries[:, 7] = 0.0
                queries[:, 8:10] = lo
                queries[:, 10:12] = hi
                queries.tofile(tmp / "q.bin")
                truth = []
                unblocked = []
                for r in receivers:
                    lit = through_rim(surface, r)
                    light = irradiance(lit)
                    shadow = irradiance(blocked_footprint(lit, r, PILLAR_LO, PILLAR_HI))
                    truth.append(light if material is None else light - shadow)
                    unblocked.append(irradiance(surface - r))
                truth = np.array(truth)
                unblocked = np.array(unblocked)
                for label, vendor in [
                    ("nvidia", "10_nvidia.json"),
                    ("mesa", "50_mesa.json"),
                ]:
                    env = dict(
                        os.environ,
                        __EGL_VENDOR_LIBRARY_FILENAMES="/usr/share/glvnd/egl_vendor.d/"
                        + vendor,
                        EGL_PLATFORM="surfaceless",
                        LP_NUM_THREADS="2",
                    )
                    if label == "mesa":
                        env["LIBGL_ALWAYS_SOFTWARE"] = "1"
                    run = subprocess.run(
                        [
                            str(args.binary.resolve()),
                            str(shader),
                            str(tmp / "field.bin"),
                            str(tmp / "q.bin"),
                            str(tmp / "out.bin"),
                        ],
                        env=env,
                        capture_output=True,
                        check=False,
                        text=True,
                    )
                    if run.returncode:
                        raise RuntimeError(run.stderr)
                    flag, result = (
                        np.fromfile(tmp / "out.bin", dtype="f4").reshape(-1, 2).T
                    )
                    assert np.isfinite(result).all() and np.all(
                        (flag == 1) | (flag == 0)
                    )
                    valid = flag == 1
                    d = doc["drivers"].setdefault(
                        label,
                        {"renderer": run.stderr.strip().splitlines()[-1], "scenes": {}},
                    )
                    entry = {
                        "sampled": len(result),
                        "analytic": int(valid.sum()),
                        "segmentFallback": int((~valid).sum()),
                    }
                    if material in (None, 1):
                        error = np.abs(result - truth) / unblocked
                        assert valid.mean() > 0.94, (label, width, scene, entry)
                        entry.update(
                            p95=float(np.quantile(error[valid], 0.95)),
                            max=float(error[valid].max()),
                        )
                        assert entry["max"] < 0.001, (label, width, scene, entry)
                    else:
                        columnStripe = (abs(receivers[:, 0] - 202.5) < 0.15) & (
                            receivers[:, 1] < 175.5
                        )
                        entry["coveredControlFallback"] = int(
                            (~valid & columnStripe).sum()
                        )
                        assert not np.any(valid & columnStripe), (
                            label,
                            width,
                            scene,
                            entry,
                        )
                    d["scenes"][f"{width}x{width}-{scene}"] = entry
    doc["scope"] = (
        "Production silhouette library on an actual GL field texture with synthetic chamber occupancy matching fixed block coordinates. Independent CPU polygon integral. Full-capture and Minecraft images are separate."
    )
    args.output.write_text(json.dumps(doc, indent=2) + "\n")
    for k, d in doc["drivers"].items():
        print(k, d["renderer"], d["scenes"])


if __name__ == "__main__":
    main()
