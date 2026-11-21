"""Summarize ordinary-game F2 captures of the same oak before and after a screen."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
RUN = HERE / "lamp-screen"
ROLES = (("off", "消灯"), ("warm", "松明"), ("warm-wall", "松明と土の壁"),
         ("warm-reopened", "壁を撤去"), ("off-again", "松明を回収"), ("soul", "魂の松明"))


def main():
    run = json.loads((RUN / "complete.json").read_text())
    assert run["cleanExit"] and not run["logErrors"] and run["previousSaveUnchanged"]
    assert not run["benchmarkSentinelPresent"] and run["labFilesUnchanged"] and run["modsUnchanged"]
    assert run["results"]["yawProof"][-1]["deg"] > 5
    font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 22)
    captures = {k: run["results"][k] for k, _ in ROLES if k in run["results"]}
    assert "off" in captures and "warm" in captures and "soul" in captures
    sheet = Image.new("RGB", (1536, ((len(captures)+2)//3)*326), "#1b2120")
    draw = ImageDraw.Draw(sheet)
    detail = {}
    for i, (k, label) in enumerate((k,t) for k,t in ROLES if k in captures):
        origin = (i%3*512, i//3*326)
        shot = Image.open(RUN / (k+"-ingame.png")).convert("RGB")
        assert shot.size == (1600, 900) and captures[k]["selectedSlot"] == 8
        pose = captures[k]["pose"]
        draw.text((origin[0]+8, origin[1]+2), label, font=font, fill="white")
        sheet.paste(shot.resize((512,288),Image.Resampling.LANCZOS), (origin[0],origin[1]+34))
        rgb = np.asarray(shot.crop((782,439,818,461))).mean((0,1)).round(2).tolist()
        detail[k] = {"target": pose["target"], "eyeYawPitchDegrees": pose["angle"],
                     "playerPosition": pose["xyz"], "centerMeanDisplayRGB": rgb}
    sheet.save(HERE/"oak.jpg", quality=94, subsampling=0)
    (HERE/"pixels.json").write_text(json.dumps({"scope":"Ordinary survival; the Sun moves between frames. Selected slot 8 (wooden shovel). The fixed central 36 by 22 pixels sample the same line of sight only for frames whose F3 target and pose agree. F3 identifies the first targetable block; cutout leaves may show other surfaces through their texture.",
            "centerBoxExclusive":[782,439,818,461], "frames":detail},indent=2)+"\n")


if __name__ == "__main__":
    main()
