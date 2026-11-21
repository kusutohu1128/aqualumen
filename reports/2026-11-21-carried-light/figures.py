"""Compose native Minecraft frames and measure fixed world receivers at the same view."""

import sys
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

root = Path(__file__).resolve().parent
role = sys.argv[1] if len(sys.argv) > 1 else "natural-delivery"
natural = root / role
prefix = "" if role == "natural-delivery" else role + "-"
font = ImageFont.truetype(
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc", 20, index=0
)


def sheet(name, columns, frames, size=(496, 279)):
    w, h = size
    out = Image.new(
        "RGB",
        (columns * w, ((len(frames) + columns - 1) // columns) * (h + 36)),
        "#162026",
    )
    labels = ImageDraw.Draw(out)
    for index, (title, source, crop) in enumerate(frames):
        x, y = index % columns * w, index // columns * (h + 36)
        with Image.open(source) as im:
            panel = im.crop(crop) if crop else im
            out.paste(
                panel.convert("RGB").resize(size, Image.Resampling.LANCZOS), (x, y)
            )
        labels.text((x + 12, y + h + 1), title, font=font, fill="white")
    out.save(root / (prefix + name), quality=93, subsampling=0)


def natural_sheet(name, columns, rows):
    sheet(
        name, columns, [(title, natural / (key + ".png"), None) for key, title in rows]
    )


natural_sheet(
    "forest.jpg",
    2,
    [
        ("forest-empty", "午後・手ぶら"),
        ("forest-torch", "午後・松明"),
        ("forest-night-empty", "夜・手ぶら"),
        ("forest-night-torch", "夜・松明"),
    ],
)
natural_sheet(
    "mine.jpg",
    3,
    [
        ("mine-empty", "手ぶら"),
        ("mine-torch", "右手の松明"),
        ("mine-offhand", "左手の松明"),
        ("mine-soul", "魂の松明"),
        ("mine-two", "右に松明・左に魂の松明"),
        ("mine-put-away", "両方を収納"),
    ],
)
natural_sheet(
    "exposure.jpg",
    2,
    [
        ("mine-noon", "廃坑・地上は正午"),
        ("mine-midnight", "廃坑・地上は真夜中"),
        ("cave-empty", "光る実のある洞窟・手ぶら"),
        ("cave-torch", "同じ場所・松明を追加"),
    ],
)
natural_sheet(
    "camera.jpg",
    3,
    [
        ("forest-view-first", "一人称"),
        ("forest-view-rear", "三人称・後方"),
        ("forest-view-front", "三人称・正面"),
    ],
)
sheet(
    "torch-detail.jpg",
    3,
    [
        (label, root / directory / "forest-night-torch.png", (1240, 608, 1590, 888))
        for directory, label in [
            ("baseline", "1.2.1"),
            ("natural-1", "初回の候補"),
            (role, "1.3.0"),
        ]
    ],
    (350, 280),
)
roles = [p.stem for p in sorted(natural.glob("*.png"))]
boxes = {
    "foreground-rock": (540, 495, 750, 625),
    "right-wall": (980, 350, 1150, 490),
    "left-rock": (200, 200, 470, 420),
}


def average(rgb, box):
    x, y, xx, yy = box
    return np.round(rgb[y:yy, x:xx].mean(axis=(0, 1)), 2).tolist()


readings = {}
for role in roles:
    rgb = np.asarray(Image.open(natural / (role + ".png")).convert("RGB"))
    readings[role] = {k: average(rgb, box) for k, box in boxes.items()}
(root / (prefix + "natural-pixels.json")).write_text(
    json.dumps(
        {
            "coordinateOrigin": "top left in 1600x900 display RGB8",
            "boxes": boxes,
            "measurements": readings,
        },
        indent=2,
    )
    + "\n"
)
