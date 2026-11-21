"""Compare the shipped ZIP to preview 3 at the same camera, tick and fixture."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SCENES = (
    ("ground-noon", 9800, "雨の午後"),
    ("ground-evening", 12400, "晴れの日没"),
    ("ground-low-sun", 12400, "雨の日没"),
)
REGIONS = {"bark": (775, 760, 818, 811), "bank": (544, 1052, 673, 1118)}


def read(path):
    return json.loads(path.read_text())


def compare():
    sheet = Image.new("RGB", (1500, 3 * 445), "#18211f")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 20)
    measurements = {}
    for col, (label, folder, filename) in enumerate((
        ("プレビュー3", "baseline-preview3", "Aqualumen-1.9.0-preview.3.zip"),
        ("プレビュー4", "preview4", "Aqualumen-1.9.0-preview.4.zip"),
    )):
        source = HERE / folder
        run = read(source / "timing.json")
        digest = hashlib.sha256((ROOT / "dist" / filename).read_bytes()).hexdigest()
        assert run["sha256"] == digest and run["worldAndConfigUnchanged"]
        assert "RTX 3080 Ti" in run["renderer"] and run["framebuffer"] == [2560, 1440]
        records = measurements[filename] = {}
        for row, (scene, tick, weather) in enumerate(SCENES):
            path = source / "capture" / (scene + ".png")
            receipt = read(path.with_suffix(".json"))
            fixture = receipt["opaque_fixture"]
            assert receipt["shader_active"] and not receipt["shader_fallback"]
            assert receipt["pack_sha256"] == digest and fixture["seed"] == 308060
            assert fixture["actual_server_world_time"] == tick and fixture["variant"] == "off"
            assert fixture["forest_light"]["pre_sample_validation"]["passed"] and fixture["camera_eye_match"]
            assert receipt["actual_camera_position"] == [208.5, 65.61999988555908, 355.5]
            assert receipt["actual_camera_rotation"] == [12.7, -2.0]
            pic = Image.open(path).convert("RGB")
            assert pic.size == (2560, 1440)
            records[scene] = {
                "packSha256": digest, "imageSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "image": str(path.relative_to(ROOT)), "serverTickOfDay": tick,
                "weatherCommand": "clear" if scene == "ground-evening" else "rain",
                "frames": receipt["frames"], "meanFps": receipt["mean_fps"], "p99Ms": receipt["p99_ms"],
                "meanDisplayRGB": {k: np.asarray(pic.crop(box)).mean((0, 1)).round(2).tolist() for k, box in REGIONS.items()},
            }
            x, y = 750 * col, 445 * row
            draw.text((x + 5, y), f"{label}　{weather}　時刻 {tick}", font=font, fill="white")
            sheet.paste(pic.resize((748, 421), Image.Resampling.LANCZOS), (x, y + 24))
    sheet.save(HERE / "release-comparison.jpg", quality=93, subsampling=0)
    (HERE / "release-comparison.json").write_text(json.dumps(measurements, indent=2) + "\n")


if __name__ == "__main__":
    compare()
