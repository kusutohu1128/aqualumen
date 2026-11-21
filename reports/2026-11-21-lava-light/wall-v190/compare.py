"""Compare F2 pixels on the same white wall with the source, stone and camera in verified Minecraft states."""

import argparse
import datetime
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent


def ray_box(eye, wall, lo, hi):
    ray = wall - eye
    inv = 1.0 / np.where(np.abs(ray) > 1e-9, ray, 1e-9)
    a = (lo - eye) * inv
    b = (hi - eye) * inv
    return np.maximum(0.0, np.minimum(a, b).max(axis=-1)) < np.minimum(
        1.0, np.maximum(a, b).min(axis=-1)
    )


def wall_pixels(geometry, width, height):
    eye = np.array(geometry["eye"])
    forward = np.array(geometry["target"]) - eye
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0, 1, 0])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    y, x = np.mgrid[:height:2, :width:2]
    factor = 2 * math.tan(math.radians(35)) / height
    ray = (
        forward
        + (x + 0.5 - width / 2)[:, :, None] * right * factor
        + (height / 2 - y - 0.5)[:, :, None] * up * factor
    )
    wall = (
        eye
        + ray
        * ((geometry["wallZ"] - eye[2]) / np.maximum(1e-6, ray[:, :, 2]))[:, :, None]
    )
    lo = np.array([202.0, 173.0, 364.0])
    hi = lo + [1, 3, 1]
    visible = (
        (wall[:, :, 0] > 199.2)
        & (wall[:, :, 0] < 208.8)
        & (wall[:, :, 1] > 173.3)
        & (wall[:, :, 1] < 177.9)
    )
    visible &= ~ray_box(eye, wall, lo - 0.09, hi + 0.09)
    masks = {}
    for count in (1, 9):
        half = math.sqrt(count) / 2.0
        corners = [
            np.array([202.5 + dx * half, 172.0 + 55 / 62, 361.5 + dz * half])
            for dx in (-1, 1)
            for dz in (-1, 1)
        ]

        def crossing(z, corners):
            return np.stack(
                [
                    wall
                    + (s - wall)
                    * ((z - wall[:, :, 2]) / (s[2] - wall[:, :, 2]))[:, :, None]
                    for s in corners
                ]
            )

        middle = crossing(364.5, corners)
        # The bundle from the four extreme corners is inside the same solid
        # cross section, independently of how the shader estimates visibility.
        blocked = (
            visible
            & (middle[:, :, :, 0].min(axis=0) > 202.1)
            & (middle[:, :, :, 0].max(axis=0) < 202.9)
        )
        blocked &= (middle[:, :, :, 1].min(axis=0) > 173.1) & (
            middle[:, :, :, 1].max(axis=0) < 175.9
        )
        both = np.concatenate((crossing(364.0, corners), crossing(365.0, corners)))
        clear = visible & (
            (both[:, :, :, 0].min(axis=0) > 203.2)
            | (both[:, :, :, 0].max(axis=0) < 201.8)
        )
        masks[f"{count}-occluded"] = blocked
        masks[f"{count}-clear"] = clear
    masks["soul-facing-wall"] = (
        visible
        & (wall[:, :, 0] > 203.8)
        & (wall[:, :, 0] < 205.8)
        & (wall[:, :, 1] > 173.9)
        & (wall[:, :, 1] < 175.6)
    )
    return masks


def verify_f2_windows(record, client, directory):
    # Link each archived F2 image back to the original filename that Minecraft
    # reported saving between READY and STILL, even if a slow frame delayed capture.
    folder = Path(record["privateGameDir"]) / "screenshots"
    if not folder.is_dir():
        folder = directory / "f2"
    captures = {}
    stage = None
    pending = []
    for line in client.splitlines():
        mark = re.search(
            r"\[Server\] AQLAVA_(READY|STILL|DRIFT|FAIL|BEGIN)_([a-z0-9-]+)_END", line
        )
        if mark:
            kind, name = mark.groups()
            if kind == "STILL" and name == stage:
                captures.setdefault(name, []).extend(pending)
            stage = name if kind == "READY" else None
            pending = []
        if stage and "/INFO]" in line and "[CHAT]" in line:
            shot = re.search(
                r"([0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9.-]+(?:_[0-9]+)?\.png)", line
            )
            if not shot:
                continue
            source = folder / shot[1]
            if not source.is_file() and not folder.is_dir():
                # The older cleanup kept copy2's source mtime and both X11
                # frames. Require the exact logged second and matching pixels.
                source = directory / (stage + "-ingame.png")
                if not source.is_file():
                    continue
                stamp = datetime.datetime.fromtimestamp(source.stat().st_mtime)
                if stamp.strftime("%Y-%m-%d_%H.%M.%S") + ".png" != shot[1]:
                    continue
                rgb = np.asarray(Image.open(source).convert("RGB"), dtype=float)
                for tag in ("x11-a", "x11-b"):
                    other = directory / (stage + "-" + tag + ".png")
                    assert hashlib.sha256(other.read_bytes()).hexdigest() == record["screenshots"][stage][tag]
                    assert np.abs(rgb - np.asarray(Image.open(other).convert("RGB"))).mean() < 2.0
            if source.is_file():
                pending.append(hashlib.sha256(source.read_bytes()).hexdigest())
    for name, photo in record["screenshots"].items():
        assert photo["ingame"] in captures.get(name, []), (
            f"No timed Minecraft F2 save for {name}"
        )


def run(directory, baseline=False):
    record = json.loads((directory / "complete.json").read_text())
    geometry = json.loads((directory / "geometry.json").read_text())
    if not baseline:
        assert (
            record["complete"]
            and record["originalWorldAndConfigUnchanged"]
            and record["shaderpackLogged"]
        )
        if record["backend"] == "vgl":
            assert "RTX 3080 Ti" in record["gl"]["renderer"]
        else:
            assert (
                record["backend"] == "llvmpipe"
                and "llvmpipe" in record["gl"]["renderer"]
            )
        client = (directory / "client.log").read_text(errors="replace")
        assert (
            "Error encountered when linking program" not in client
            and "assembly compile error" not in client
        )
        verify_f2_windows(record, client, directory)
    else:
        assert record["renderer"] == "NVIDIA GeForce RTX 3080 Ti"
    aliases = {
        "one-open": "lava1-open",
        "one-pillar": "lava1-pillar",
        "nine-open": "lava9-open",
        "nine-pillar": "lava9-pillar",
        "dark-again": "restored-dark",
    }
    photos = {}
    for name, entry in record["screenshots"].items():
        fname = name + ".png" if baseline else name + "-ingame.png"
        expected = entry if baseline else entry["ingame"]
        pic = directory / fname
        assert hashlib.sha256(pic.read_bytes()).hexdigest() == expected
        photos[aliases.get(name, name)] = pic
    with Image.open(photos["dark"]) as img:
        masks = wall_pixels(geometry, *img.size)
    data = {
        k: np.asarray(Image.open(v).convert("RGB"), dtype="f4")[::2, ::2]
        for k, v in photos.items()
    }
    contrasts = {}
    for a, b in [
        ("lava1-open", "dark"),
        ("lava1-pillar", "dark-pillar"),
        ("lava9-pillar", "dark-pillar"),
        ("soul-pillar", "dark-pillar"),
        ("lava1-pillar", "lava1-open"),
        ("lava9-pillar", "lava1-pillar"),
        ("lava9-pillar", "lava9-open"),
        ("soul-lava9-pillar", "lava9-pillar"),
        ("soul-lava9-pillar", "soul-pillar"),
        ("torch-lava1-open", "torch"),
        ("torch-lava1-pillar", "torch-lava1-open"),
        ("restored-dark", "dark"),
    ]:
        if a not in data or b not in data:
            continue
        row = {}
        for region, mask in masks.items():
            if mask.any():
                delta = data[a][mask] - data[b][mask]
                row[region] = {
                    "pixels": int(mask.sum()),
                    "medianRGB": np.median(delta, axis=0).round(2).tolist(),
                    "meanRGB": np.mean(delta, axis=0).round(2).tolist(),
                }
        contrasts[f"{a} minus {b}"] = row
    return photos, {
        "shader": record["pack"],
        "renderer": record["renderer"] if baseline else record["gl"]["renderer"],
        "hash": record.get("sha256", record.get("packSha256")),
        "contrasts": contrasts,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("candidate", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    baseline = HERE.parent / "baseline-180"
    old, a = run(baseline, True)
    new, b = run(args.candidate)
    args.output.mkdir(exist_ok=True)
    mode = "Display RGB differences on the same face and within each build. Tone mapping, adaptation and indirect bounce contribute; not radiometric flux."
    (args.output / "wall-colors.json").write_text(
        json.dumps({"scope": mode, "baseline": a, "candidate": b}, indent=2) + "\n"
    )
    font = ImageFont.truetype(
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 20
    )
    stages = [
        ("lava1-open", "溶岩一マス"),
        ("lava1-pillar", "一マスと石柱"),
        ("lava9-pillar", "九マスと石柱"),
    ]
    sheet = Image.new("RGB", (1440, 632), "#171918")
    draw = ImageDraw.Draw(sheet)
    for y, (name, pack) in enumerate(
        [
            ("1.8.0 RTX", old),
            ("開発版 " + ("RTX" if "NVIDIA" in b["renderer"] else "llvmpipe"), new),
        ]
    ):
        for x, (stage, description) in enumerate(stages):
            img = (
                Image.open(pack[stage])
                .convert("RGB")
                .resize((480, 270), Image.Resampling.LANCZOS)
            )
            sheet.paste(img, (480 * x, 316 * y))
            draw.text(
                (480 * x + 12, 316 * y + 275),
                name + "　" + description,
                font=font,
                fill="white",
            )
    sheet.save(args.output / "old-and-new.jpg", quality=94)
    if "soul-lava9-pillar" in new and "soul-pillar" in new:
        sheet = Image.new("RGB", (1440, 312), "#171918")
        draw = ImageDraw.Draw(sheet)
        for x, (stage, description) in enumerate(
            [
                ("lava9-pillar", "溶岩と石柱"),
                ("soul-lava9-pillar", "壁側に魂の松明を追加"),
                ("soul-pillar", "溶岩をふさぎ、松明を残す"),
            ]
        ):
            img = (
                Image.open(new[stage])
                .convert("RGB")
                .resize((480, 270), Image.Resampling.LANCZOS)
            )
            sheet.paste(img, (480 * x, 0))
            draw.text((480 * x + 10, 275), description, font=font, fill="white")
        sheet.save(args.output / "torch-with-lava.jpg", quality=94)
    print(b["shader"], b["hash"], list(b["contrasts"]))


if __name__ == "__main__":
    main()
