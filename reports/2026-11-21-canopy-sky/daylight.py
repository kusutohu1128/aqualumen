"""Registered forest frames on the original and new full shader packages."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FOREST = HERE.parent / "2026-11-21-lava-light/wall-v190"
SCENES = ("ground-noon", "ground-evening", "ground-low-sun")
ROLES = ("off", "warm", "soul")
REGIONS = {"birchBark": (775, 760, 818, 811), "grassByTorch": (1118, 1172, 1176, 1224),
           "bankUnderOverhang": (544, 1052, 673, 1118), "farOak": (1282, 595, 1325, 636)}


def compare(candidate, out):
    rows = {}
    pictures = {}
    for label, folder in (("preview3", FOREST / "birch-preview3-final"), ("candidate", candidate)):
        timing = json.loads((folder / "timing.json").read_text())
        assert timing["worldAndConfigUnchanged"] and "RTX 3080 Ti" in timing["renderer"]
        rows[label] = {"pack": timing["pack"], "sha256": timing["sha256"], "scenes": {}}
        for scene, role in zip(SCENES, ROLES, strict=True):
            pic = folder / "capture" / (scene + ".png")
            receipt = json.loads(pic.with_suffix(".json").read_text())
            assert receipt["shader_active"] and not receipt["shader_fallback"]
            f = receipt["opaque_fixture"]
            assert f["variant"] == role and f["actual_server_world_time"] == 9800
            assert f["forest_light"]["pre_sample_validation"]["passed"] and f["camera_eye_match"]
            assert receipt["actual_camera_position"] == [208.5, 65.61999988555908, 355.5]
            assert receipt["actual_camera_rotation"] == [12.7, -2.] and receipt["pack_sha256"] == timing["sha256"]
            image = Image.open(pic).convert("RGB")
            assert image.size == (2560, 1440)
            pictures[label, role] = image
            rows[label]["scenes"][role] = {
                "png": str(pic.relative_to(HERE.parent.parent)), "sha256": hashlib.sha256(pic.read_bytes()).hexdigest(),
                "meanDisplayRGB": {k: np.asarray(image.crop(box)).mean((0, 1)).round(2).tolist() for k,box in REGIONS.items()},
                "timing": timing["samples"][role]}
    font = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    heading, small = ImageFont.truetype(font, 26), ImageFont.truetype(font, 20)
    sheet = Image.new("RGB", (1536, 838), "#17201d")
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 4), "同じ白樺に、同じ時刻に松明を置く", font=heading, fill="white")
    for row, label in enumerate(("preview3", "candidate")):
        for col, (role, jp) in enumerate(zip(ROLES, ("消灯", "松明", "魂の松明"))):
            img = pictures[label, role]
            x, y = col*512, 48+row*392
            sheet.paste(img.resize((510, 287), Image.Resampling.LANCZOS), (x, y))
            sheet.paste(img.crop((730, 735, 879, 814)), (x, y+290))
            draw.text((x+164, y+298), ("プレビュー3" if not row else "天空光の候補版")+"　"+jp, font=small, fill="white")
            draw.text((x+164, y+332), "左は幹の等倍切り出し", font=small, fill="#becdc3")
    out.mkdir(exist_ok=True)
    sheet.save(out / "birch.jpg", quality=94, subsampling=0)
    detail = Image.new("RGB",(1440, 562), "#17201d")
    pen = ImageDraw.Draw(detail)
    for i,(label, jp) in enumerate((("preview3", "プレビュー3"), ("candidate", "天空光の候補版"))):
        pen.text((i*720+8, 3),jp+"　消灯",font=heading,fill="white")
        photo = pictures[label, "off"].crop((380, 580, 1410, 1310)).resize((720,510),Image.Resampling.LANCZOS)
        detail.paste(photo,(i*720,48))
    detail.save(out/"shade.jpg",quality=96,subsampling=0)
    (out/"comparison.json").write_text(json.dumps({"regions": REGIONS, "measurements": rows,
       "scope":"Display RGB on the same real forest camera, not linear radiance. 10 s game-frame timing per role."},indent=2)+"\n")


if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("candidate",type=Path);p.add_argument("output",type=Path)
    args=p.parse_args()
    compare(args.candidate.resolve(),args.output)
