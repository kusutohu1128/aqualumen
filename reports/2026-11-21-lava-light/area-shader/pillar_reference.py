"""Direct light on the measured wall, integrating a recessed pool through one stone pillar."""

import itertools
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FACES = HERE.parent / "captured-shore-slots/faces.json"
PILLAR_LO = np.array([202.0, 173.0, 364.0])
PILLAR_HI = np.array([203.0, 176.0, 365.0])
NORMAL = np.array([0.0, 0.0, -1.0])


def clip(polygon, plane):
    if not len(polygon):
        return polygon
    distances = polygon @ plane[:3] + plane[3]
    if np.all(distances >= 0):
        return polygon
    vertices = []
    for i, (point, dist) in enumerate(zip(polygon, distances)):
        before = distances[i - 1]
        if (dist > 0 and before < 0) or (dist < 0 and before > 0):
            fraction = before / (before - dist)
            vertices.append(polygon[i - 1] + fraction * (point - polygon[i - 1]))
        if dist >= 0:
            vertices.append(point)
    return np.array(vertices)


def irradiance(polygon):
    if len(polygon) < 3:
        return 0.0
    directions = polygon / np.linalg.norm(polygon, axis=1)[:, None]
    following = np.roll(directions, -1, axis=0)
    cross = np.cross(directions, following)
    sine = np.linalg.norm(cross, axis=1)
    angle = np.arctan2(sine, np.sum(directions * following, axis=1))
    weight = np.divide(angle, sine, out=np.ones_like(angle), where=sine > 1e-15)
    return max(0.0, -0.5 * np.dot(weight, cross @ NORMAL))


def blocked_footprint(polygon, receiver, lo, hi):
    # With the receiver at the origin, p is shadowed exactly when p is in
    # k*[lo, hi] for some k >= 1. Eliminate k between all lower/upper bounds.
    upper, lower = [], [(-1.0, np.array([0.0, 0.0, 0.0, -1.0]))]
    for axis, unit in enumerate(np.eye(4)[:3]):
        for a, plane in (
            (lo[axis] - receiver[axis], unit),
            (receiver[axis] - hi[axis], -unit),
        ):
            if a == 0.0:
                polygon = clip(polygon, plane)
            elif a > 0.0:
                upper.append((a, plane))
            else:
                lower.append((a, plane))
    for (a, u), (b, v) in itertools.product(upper, lower):
        plane = a * v - b * u
        polygon = clip(polygon, plane)
    return polygon


def pool_geometry(samples):
    lit = [s for s in samples if s["path"]]
    codes = {value for cell in lit for value in cell["corners"]}
    assert len(codes) == 1
    height = 172 + (codes.pop() - 1) / 240
    x0, x1 = min(s["x"] for s in lit), max(s["x"] for s in lit) + 1
    z0, z1 = min(s["z"] for s in lit), max(s["z"] for s in lit) + 1
    assert len(lit) == (x1 - x0) * (z1 - z0)
    return np.array(
        [[x0, height, z0], [x0, height, z1], [x1, height, z1], [x1, height, z0]]
    )


def through_rim(surface, receiver):
    polygon = surface - receiver
    t = (173.0 - receiver[1]) / polygon[0, 1]
    for axis in (0, 2):
        low, high = np.min(surface[:, axis]), np.max(surface[:, axis])
        plane = np.zeros(4)
        plane[axis], plane[3] = t, receiver[axis] - low
        polygon = clip(polygon, plane)
        plane[axis], plane[3] = -t, high - receiver[axis]
        polygon = clip(polygon, plane)
    return polygon


def numerical(surface, receiver, count, lo, hi):
    # Independent midpoint surface quadrature and segment-box slab intersection.
    grid = (np.arange(count) + 0.5) / count
    xs, zs = np.meshgrid(grid, grid)
    points = (
        surface[0]
        + xs[..., None] * (surface[3] - surface[0])
        + zs[..., None] * (surface[1] - surface[0])
    )
    ray = points - receiver
    with np.errstate(divide="ignore"):
        t0, t1 = (lo - receiver) / ray, (hi - receiver) / ray
    enter = np.maximum(0.0, np.min([t0, t1], axis=0).max(axis=2))
    leave = np.minimum(1.0, np.max([t0, t1], axis=0).min(axis=2))
    rim = receiver + ray * ((173.0 - receiver[1]) / ray[..., 1])[..., None]
    open_rim = (rim[..., 0] >= surface[0, 0]) & (rim[..., 0] <= surface[2, 0])
    open_rim &= (rim[..., 2] >= surface[0, 2]) & (rim[..., 2] <= surface[2, 2])
    area = (surface[2, 0] - surface[0, 0]) * (surface[2, 2] - surface[0, 2])
    weights = area * (-ray[..., 2]) * (-ray[..., 1]) / np.sum(ray * ray, axis=2) ** 2
    return np.mean(weights * open_rim), np.mean(weights * open_rim * (leave <= enter))


def main():
    samples = json.loads(FACES.read_text())["samples"]
    pools = [pool_geometry(samples[key]) for key in ("one-pillar", "nine-pillar")]
    checks = []
    for surface in pools:
        for x, y in [
            (202.5, 174.0),
            (201.53, 175.5),
            (203.19, 176.05),
            (200.5, 174.2),
            (204.0, 173.6),
            (203.53, 177.4),
        ]:
            receiver = np.array([x, y, 366.0])
            lit = through_rim(surface, receiver)
            clear = irradiance(lit)
            for label, offset in [
                ("pillar", 0.0),
                ("past-pool", -10.0),
                ("behind-wall", 8.0),
            ]:
                shift = np.array([0.0, 0.0, offset])
                lo, hi = PILLAR_LO + shift, PILLAR_HI + shift
                remaining = clear - irradiance(blocked_footprint(lit, receiver, lo, hi))
                ref_clear, ref_remaining = numerical(surface, receiver, 384, lo, hi)
                err = max(abs(clear - ref_clear), abs(remaining - ref_remaining)) / max(
                    clear, 1e-10
                )
                assert err < 0.01, (label, receiver, remaining, ref_remaining, err)
                if offset:
                    assert abs(remaining - clear) < 1e-12
                checks.append(
                    {
                        "poolWidth": int(surface[2, 0] - surface[0, 0]),
                        "wall": [x, y],
                        "box": label,
                        "direct": remaining,
                        "open": clear,
                        "quadrature": float(ref_remaining),
                        "errorRelativeToOpen": float(err),
                    }
                )

    # Orthographic strip of the receiver wall. Each panel shows the fraction of
    # that same emitter's unblocked direct irradiance, using one shared scale.
    font = ImageFont.truetype(
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 19
    )
    sheet = Image.new("RGB", (1000, 380), "#161819")
    draw = ImageDraw.Draw(sheet)
    for index, surface in enumerate(pools):
        fractions = np.zeros((50, 88))
        for j in range(50):
            for i in range(88):
                receiver = np.array(
                    [199.25 + (i + 0.5) * 6.5 / 88, 177.6 - (j + 0.5) * 4.4 / 50, 366.0]
                )
                lit = through_rim(surface, receiver)
                clear = irradiance(lit)
                fractions[j, i] = (
                    max(
                        0.0,
                        1.0
                        - irradiance(
                            blocked_footprint(lit, receiver, PILLAR_LO, PILLAR_HI)
                        )
                        / clear,
                    )
                    if clear > 0.0
                    else np.nan
                )
        palette = np.array([[26, 24, 32], [245, 153, 60]], dtype=float)
        values = np.nan_to_num(fractions)[..., None]
        rgb = np.rint(palette[0] * (1 - values) + palette[1] * values).astype("uint8")
        rgb[~np.isfinite(fractions)] = [94, 97, 103]
        sheet.paste(
            Image.fromarray(rgb).resize((484, 275), Image.Resampling.NEAREST),
            (8 + index * 500, 49),
        )
        draw.text(
            (12 + index * 500, 9),
            ("溶岩一マス", "溶岩九マス")[index],
            font=font,
            fill="white",
        )
        sample = next(
            c
            for c in checks
            if c["box"] == "pillar"
            and c["poolWidth"] == (1, 3)[index]
            and c["wall"] == [203.19, 176.05]
        )
        wall_x, wall_y = sample["wall"]
        px = 8 + index * 500 + (wall_x - 199.25) / 6.5 * 484
        py = 49 + (177.6 - wall_y) / 4.4 * 275
        draw.ellipse((px - 4, py - 4, px + 4, py + 4), outline="white", width=2)
        draw.line(
            (px + 4, py - 3, px + 18, py - 16, px + 25, py - 16), fill="white", width=2
        )
        draw.text(
            (px + 28, py - 32),
            f"{sample['direct'] / sample['open']:.0%}",
            font=font,
            fill="white",
            stroke_width=2,
            stroke_fill="#35291f",
        )
    draw.text(
        (13, 337),
        "石柱の奥の白壁に届く直射光の割合　　黒 0%　　 橙 100%　　 灰色は床の縁による遮光",
        font=font,
        fill="white",
    )
    sheet.save(HERE / "pillar-visibility.png")
    result = {
        "method": "CPU polygon irradiance of measured horizontal source geometry; one solid pillar and recessed opening. No Minecraft postprocessing, indirect light or gameplay FPS.",
        "samplesPerIndependentEstimate": 384**2,
        "cases": len(checks),
        "maxErrorRelativeToOpen": max(c["errorRelativeToOpen"] for c in checks),
        "checks": checks,
    }
    (HERE / "pillar-results.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
