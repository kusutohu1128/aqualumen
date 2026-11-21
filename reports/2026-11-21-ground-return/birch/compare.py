"""Compare fixed-pose Minecraft screenshots and the floor-by-roof interaction."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROLES = {"white": "ground-noon", "red": "ground-evening",
         "white-roof": "air-shadow-backlit", "red-roof": "ground-low-sun"}
REGIONS = {"birch": (775, 760, 818, 811), "farOak": (1282, 595, 1325, 636)}


def measure(folder):
    timing = json.loads((folder / "timing.json").read_text())
    assert timing["worldAndConfigUnchanged"] and "RTX 3080 Ti" in timing["renderer"]
    result, frames = {}, {}
    for role, scene in ROLES.items():
        base = folder / "capture" / scene
        data = json.loads(base.with_suffix(".json").read_text())
        cleanup = json.loads((base.parent / (scene + "-fixture-cleanup.json")).read_text())
        assert cleanup["cleanup_complete"] and cleanup["forest_post_cleanup_validation"]["passed"]
        forest = data["opaque_fixture"]
        assert forest["variant"] == role and forest["actual_server_world_time"] == 6000
        verification = forest["forest_light"]["pre_sample_validation"]
        assert verification["passed"] and forest["camera_eye_match"]
        assert data["actual_camera_rotation"] == [12.7, -2.] and data["actual_camera_position"] == [208.5, 65.61999988555908, 355.5]
        assert data["shader_active"] and not data["shader_fallback"] and data["pack_sha256"] == timing["sha256"]
        image = Image.open(base.with_suffix(".png")).convert("RGB")
        assert image.size == (2560, 1440)
        frames[role] = image
        result[role] = {"displayRGB": {label: np.asarray(image.crop(region)).mean((0,1)).round(3).tolist()
                                      for label,region in REGIONS.items()},
                        "frameSha256": hashlib.sha256(base.with_suffix(".png").read_bytes()).hexdigest(),
                        "timing": timing["samples"][role], "verifiedPlacement": verification}
    return result, frames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    rows, photos = {}, {}
    for name, folder in (("previous", "preview4"), ("candidate", args.candidate)):
        rows[name],photos[name] = measure(HERE/folder)
    contrasts = {}
    for name, modes in rows.items():
        contrasts[name] = {}
        for label in REGIONS:
            def rgb(mode):
                return np.array(modes[mode]["displayRGB"][label])
            contrasts[name][label] = {condition: (rgb("red"+suffix)-rgb("white"+suffix)).round(3).tolist()
                                     for condition,suffix in (("open",""),("roof","-roof"))}
    (args.output/"comparison.json").write_text(json.dumps({"regions":REGIONS,"captures":rows,"redMinusWhite":contrasts,
        "scope":"Mean display RGB over unchanged pixels of the birch and a more distant trunk. Exposure, clouds and foliage animation run during play. No inference of linear HDR energy from display RGB."},indent=2)+"\n")
    sheet = Image.new("RGB",(1488,837),"#19221f")
    pen=ImageDraw.Draw(sheet); font="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    heading=ImageFont.truetype(font,31); body=ImageFont.truetype(font,21); small=ImageFont.truetype(font,18)
    pen.text((20,7),"同じ白樺に地面から返る光",font=heading,fill="white")
    for i,(role,jp) in enumerate(zip(ROLES,("白い床","赤い床","白い床＋石屋根","赤い床＋石屋根"),strict=True)):
        x=372*i
        pen.text((x+12,63),jp,font=body,fill="white")
        for j,label in enumerate(("previous","candidate")):
            y=104+j*366
            im=photos[label][role]
            thumb=im.resize((368,207),Image.Resampling.LANCZOS)
            sheet.paste(thumb,(x,y))
            crop=im.crop((737,723,877,837))
            sheet.paste(crop,(x+3,y+215))
            pen.text((x+152,y+228),"プレビュー4" if j==0 else "地面の反射あり",font=body,fill="white")
            pen.text((x+152,y+264),"左は同じ幹の等倍",font=small,fill="#bccec3")
    sheet.save(args.output/"birch.jpg",quality=94,subsampling=0)
    print(json.dumps(contrasts,indent=2))


if __name__=="__main__":
    main()
