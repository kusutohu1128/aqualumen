"""Matched Minecraft screenshots. Crop bounds are in the recorded 2560 x 1440 image."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent
font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"


def font(px):
    return ImageFont.truetype(font_path, px, index=0)


def sheet(file, panels, frame, width, columns):
    left, top, right, bottom = frame
    height = round(width * (bottom - top) / (right - left))
    pad, label = 12, 40
    rows = (len(panels) + columns - 1) // columns
    board = Image.new("RGB", (columns * (width + pad) + pad, rows * (height + label + pad) + pad), "#162028")
    draw = ImageDraw.Draw(board)
    for i, (role, scene, caption) in enumerate(panels):
        folder = root / role / "capture"
        row = json.loads((folder / (scene + ".json")).read_text())
        assert row["framebuffer_resolution"] == [2560, 1440] and row["shader_active"] and not row["shader_fallback"]
        assert row["camera_follows_local_player"] and row["camera_eye_match"]
        img = Image.open(folder / (scene + ".png")).convert("RGB").crop(frame)
        x = pad + (i % columns) * (width + pad)
        y = pad + (i // columns) * (height + label + pad)
        draw.text((x, y), caption, fill="#edf4f4", font=font(20))
        board.paste(img.resize((width, height), Image.Resampling.LANCZOS), (x, y + label))
    board.save(root / file, quality=94, subsampling=0)


if __name__ == "__main__":
    import sys
    role = sys.argv[1] if len(sys.argv) > 1 else "delivery"
    assert role in ("delivery", "final")
    suffix = "-final.jpg" if role == "final" else ".jpg"
    version = "Aqualumen 1.2.1" if role == "final" else "Aqualumen 1.2.0"

    sheet("canopy" + suffix, [(role, "lamp-day-off", "木陰・消灯"), (role, "lamp-day-canopy", "同じ木陰・松明を点灯")],
          (450, 410, 1070, 885), 650, 2)
    sheet("placed-lights" + suffix, [(role, s, label) for s, label in [
        ("lamp-night-off", "消灯"), ("lamp-night-torch", "通常の松明"), ("lamp-night-soul", "魂の松明"),
        ("lamp-night-wall", "石の仕切り"), ("lamp-night-glass", "赤いガラスの仕切り"), ("lamp-night-both", "通常の松明＋魂の松明")]],
          (865, 476, 1675, 915), 470, 3)
    sheet("water" + suffix, [(role,"lamp-night-off","消灯"),(role,"lamp-night-water","水際のランタン")],
          (855, 735, 1620, 1160), 550, 2)
    sheet("reference" + suffix, [(pack_role, scene, name + "　" + cap) for scene, cap in [
        ("lamp-night-torch","松明"),("lamp-night-soul","魂の松明")] for pack_role, name in [
        ("old-baseline","Aqualumen 1.1"),("photon-default","Photon v1.1 標準設定"),(role,version)]],
          (865, 476, 1675, 915), 470, 3)

    if role == "final":
        sheet("exposure.jpg", [
            ("delivery", "lamp-night-torch", "1.2.0　夜の松明"),
            (role, "lamp-night-torch", "1.2.1　夜の松明"),
            ("delivery", "lamp-night-both", "1.2.0　暖色＋寒色"),
            (role, "lamp-night-both", "1.2.1　暖色＋寒色")],
            (865, 476, 1675, 915), 560, 2)
