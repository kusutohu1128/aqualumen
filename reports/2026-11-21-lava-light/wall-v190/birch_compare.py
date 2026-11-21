"""Measure the same birch and grass in three real daylight Minecraft captures."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    scenes = ("ground-noon", "ground-evening", "ground-low-sun")
    roles = ("off", "warm", "soul")
    labels = ("消灯", "松明", "魂の松明")
    boxes = {"birch": (775, 760, 818, 811), "grass": (1118, 1172, 1176, 1224),
             "distantOak": (1282, 595, 1325, 636)}
    sheet = Image.new("RGB", (1440, 774), "#172021")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 22)
    draw.text((12, 6), "昼の白樺　　同じ木・同じ時刻・同じ位置の松明", font=font, fill="white")
    result = {"displayPixelBoxesXYXY": boxes, "captures": {}}
    for row, folder in enumerate((args.baseline, args.candidate)):
        timing = json.loads((folder / "timing.json").read_text())
        assert timing["worldAndConfigUnchanged"] and "3080 Ti" in timing["renderer"]
        observations = {}
        for col, (scene, role) in enumerate(zip(scenes, roles)):
            source = folder / "capture" / (scene + ".png")
            data = json.loads(source.with_suffix(".json").read_text())
            fixture = data["opaque_fixture"]
            assert data["shader_active"] and not data["shader_fallback"] and data["camera_eye_match"]
            assert fixture["variant"] == role and fixture["actual_server_world_time"] == 9800
            assert fixture["forest_light"]["pre_sample_validation"]["passed"]
            assert fixture["torch_cell"] == [207, 64, 359] and data["actual_camera_rotation"] == [12.7, -2.]
            photo = Image.open(source).convert("RGB")
            assert photo.size == (2560, 1440)
            x, y = col*480, 43+row*362
            sheet.paste(photo.resize((476, 268), Image.Resampling.LANCZOS), (x, y))
            detail = photo.crop((741, 727, 867, 806))
            sheet.paste(detail.resize((126, 79)), (x, y+271))
            draw.text((x+139, y+277), ("通常版" if row == 0 else "面光源版")+"　"+labels[col],
                      font=font, fill="white")
            draw.text((x+139, y+313), "左は同じ幹の拡大", font=font, fill="#c6d2d0")
            observations[role] = {
                "pngSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "frames": data["frames"], "fps": data["mean_fps"], "p99Milliseconds": data["p99_ms"],
                "meanDisplayRGB": {name: np.asarray(photo.crop(rect)).mean(axis=(0, 1)).round(2).tolist()
                                   for name, rect in boxes.items()},
            }
        result["captures"][folder.name] = {"packSha256": timing["sha256"], "roles": observations}
    args.output.mkdir(exist_ok=False)
    (args.output / "birch.json").write_text(json.dumps(result, indent=2)+"\n")
    sheet.save(args.output / "birch.jpg", quality=94, subsampling=0)


if __name__ == "__main__":
    main()
