"""Compare the same observed patches on the rear wall of the private lantern room."""

from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont
import numpy as np

root = Path(__file__).resolve().parent
roles = [
    "lamp-empty",
    "cow-near",
    "cow-stepped",
    "cow-far",
    "removed",
    "unlit",
    "unlit-cow",
]
datasets = {"verified-baseline": "1.3.0", "verified-entity": "動く影の試作版"}
boxes = {"west wall": (605, 355, 616, 366), "east wall": (815, 285, 826, 296)}
values = {}
for directory in datasets:
    receipt = json.loads((root / directory / "complete.json").read_text())
    assert receipt["images"] == len(roles) and not receipt["shaderFallback"]
    values[directory] = {}
    for name in roles:
        rgb = np.asarray(Image.open(root / directory / (name + ".png")).convert("RGB"))
        assert rgb.shape == (720, 1280, 3)
        values[directory][name] = {
            k: np.round(rgb[y:yy, x:xx].mean(axis=(0, 1)), 2).tolist()
            for k, (x, y, xx, yy) in boxes.items()
        }
    values[directory]["packSha256"] = receipt["sha256"]
out = Image.new("RGB", (3 * 480, 2 * 304), "#162026")
dr = ImageDraw.Draw(out)
font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc", 18)
for j, (directory, title) in enumerate(datasets.items()):
    for i, (role, caption) in enumerate(
        [
            ("cow-near", "牛が光路に入る"),
            ("cow-stepped", "牛が横へ移る"),
            ("removed", "牛がいなくなる"),
        ]
    ):
        im = (
            Image.open(root / directory / (role + ".png"))
            .convert("RGB")
            .resize((480, 270), Image.Resampling.LANCZOS)
        )
        out.paste(im, (i * 480, j * 304))
        dr.text(
            (i * 480 + 8, j * 304 + 273),
            title + "　" + caption,
            fill="white",
            font=font,
        )
out.save(root / "cow-wall.jpg", quality=95, subsampling=0)
for key in ("west wall", "east wall"):
    v = values["verified-entity"]
    b = values["verified-baseline"]
    assert np.max(np.abs(np.array(v["removed"][key]) - v["lamp-empty"][key])) < 3
    assert np.max(np.abs(np.array(b["removed"][key]) - b["lamp-empty"][key])) < 3
assert (
    values["verified-entity"]["cow-near"]["west wall"][0] + 50
    < values["verified-baseline"]["cow-near"]["west wall"][0]
)
assert (
    values["verified-entity"]["cow-stepped"]["east wall"][0] + 50
    < values["verified-baseline"]["cow-stepped"]["east wall"][0]
)
(root / "wall.json").write_text(
    json.dumps(
        dict(
            display="mean 11 x 11 display RGB8, top-left origin",
            boxes=boxes,
            measurements=values,
        ),
        indent=2,
    )
    + "\n"
)
