"""Measure camera-visible wall patches and hand state in native Minecraft captures."""

from pathlib import Path
import json
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent
folder = root / sys.argv[1] / "capture"
rows = {}
sources = {}
patches = {
    "front-wall-west": [405.20, 152.62, -410.999],
    "side-pillar-shadow": [407.25, 152.62, -410.999],
    "back-wall-west": [404.5, 152.5, -410.999],
    "back-wall-east": [408.5, 152.5, -410.999],
}
for path in sorted(folder.glob("lamp-hand-*.png")):
    role = path.stem
    meta = json.loads(path.with_suffix(".json").read_text())
    fixture = meta["local_light_fixture"]
    physical = fixture["hand_light"]
    assert (
        meta["shader_active"]
        and not meta["shader_fallback"]
        and meta["camera_eye_match"]
        and physical["settled_at_capture"]
    )
    clean = json.loads((folder / (role + "-hand-cleanup.json")).read_text())
    assert clean["cleanup_complete"] and not clean["conflicts_preserved"]
    assert json.loads((folder / (role + "-fixture-cleanup.json")).read_text())[
        "cleanup_complete"
    ]
    mat = fixture["render_projection"]
    vp = (
        np.array(mat["projection"]).reshape(4, 4).T
        @ np.array(mat["model_view"]).reshape(4, 4).T
    )
    im = Image.open(path).convert("RGB")
    a = np.asarray(im)
    means = {}
    for key, xyz in patches.items():
        v = vp @ np.r_[np.array(xyz) - mat["eye"], 1.0]
        x, y = np.rint(
            (v[:2] / v[3] * [1, -1] + 1) * np.array(mat["framebuffer"]) / 2
        ).astype(int)
        means[key] = {
            "pixel": [int(x), int(y)],
            "rgb8": np.round(a[y - 4 : y + 5, x - 4 : x + 5].mean((0, 1)), 2).tolist(),
        }
    src = physical["actual_client_hands_at_capture"]
    rows[role] = {
        "sha": meta["pack_sha256"],
        "hands": [src["client_main"], src["client_off"]],
        "eye": mat["eye"],
        "fps": meta["mean_fps"],
        "p99ms": meta["p99_ms"],
        "worstMs": meta["max_ms"],
        "frames": meta["frames"],
        "size": mat["framebuffer"],
        "wall": means,
    }
    sources[role[10:]] = im
summary = {
    "worldCoordinates": patches,
    "patchSize": "9x9",
    "dataset": sys.argv[1],
    "scenes": rows,
}
(root / (sys.argv[1] + "-receivers.json")).write_text(
    json.dumps(summary, indent=2) + "\n"
)
# Each column is the same view. Mark the wall point on the image without covering measured pixels.
variants = [
    ("hidden", "右手の松明"),
    ("hidden-off", "左手の松明"),
    ("hidden-empty", "手ぶら"),
]
if all(k in sources for k, _ in variants):
    font = ImageFont.truetype(
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc", 21, index=0
    )
    sheet = Image.new("RGB", (1440, 420), "#162026")
    d = ImageDraw.Draw(sheet)
    for i, (key, label) in enumerate(variants):
        img = sources[key]
        m = rows["lamp-hand-" + key]["wall"]["side-pillar-shadow"]
        x, y = m["pixel"]
        view = img.resize((480, 270), Image.Resampling.LANCZOS)
        vx, vy = round(x * 480 / img.width), round(y * 270 / img.height)
        vd = ImageDraw.Draw(view)
        vd.ellipse((vx - 7, vy - 7, vx + 7, vy + 7), outline="#f8e562", width=1)
        sheet.paste(view, (i * 480, 0))
        d.text((i * 480 + 12, 272), label, font=font, fill="white")
        detail = img.crop((x - 132, y - 30, x + 132, y + 30)).resize(
            (480, 110), Image.Resampling.NEAREST
        )
        sheet.paste(detail, (i * 480, 309))
    sheet.save(root / (sys.argv[1] + "-pillar.jpg"), quality=93, subsampling=0)
