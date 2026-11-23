"""Archive the two lanterns and the opened exit on a continuous survival journey."""

import argparse
import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
WOOD = HERE.parent/"2026-11-21-animal-light/woodland"
sys.path.insert(0, str(HERE.parent/"2026-11-22-ceiling-return"))
from save_checkpoint import preserve
sys.path.insert(0, str(HERE.parent/"2026-11-23-torch-density"))
from playtime import extend
sys.path.insert(0, str(WOOD))
import trail


def pictures(folder, shots, output):
    canvas = Image.new("RGB",(1024,660),"#1b221f")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",18)
    for i,(name,label) in enumerate(shots):
        with Image.open(folder/(name+"-ingame.png")) as im:
            assert im.size == (1600,900)
            x,y=(i%2)*512,(i//2)*330
            canvas.paste(im.convert("RGB").resize((512,288),Image.Resampling.LANCZOS),(x,y))
            draw.text((x+12,y+293), label, fill="white",font=font)
    canvas.save(HERE/output,quality=94)


def archive(data, name, parent, sha, activity, title, updates):
    folder = WOOD/name
    receipt = json.loads((folder/"complete.json").read_text())
    assert receipt["results"]["completed"] == [activity] and not receipt["results"].get("failed")
    assert receipt["revisit"]["sourceRun"] == parent and receipt["labFilesUnchanged"] and receipt["modsUnchanged"]
    assert receipt["savedLevel"]["Time"] == receipt["savedLevel"]["DayTime"]
    extend(data["chains"], folder, 308060, sha, activity)
    previous = json.loads((WOOD/parent/"save.json").read_text())
    blocks = {tuple(map(int, key.split(","))): value for key,value in previous["verifiedBlocks"].items()}
    blocks.update(updates)
    preserve(folder, title, blocks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--through-home",action="store_true")
    args = parser.parse_args()
    data = json.loads((HERE.parent/"2026-11-23-wet-oak-motion/playtime.json").read_text())
    trail.world = Path(json.loads((WOOD/"lakeside-to-meadow/identity.json").read_text())["world"])
    roof = trail.name(620,67,377)
    assert roof in ("grass_block", "dirt")
    archive(data,"meadow-shelter","lakeside-to-meadow","1b4ef25c23a9948ae0069e201f0de4fb14276e44869647a2215e9c0b26606a85",
            "dig-and-light-meadow-shelter","Aqualumen-Meadow-Shelter",
            {(621,65,377):"minecraft:soul_lantern",(620,65,378):"minecraft:lantern",
             (621,66,377):"minecraft:dirt",(620,67,377):"minecraft:"+roof})
    pictures(WOOD/"meadow-shelter",
             [("hillside","牧草地から丘を下る"),("earth-before","土の張り出しの下"),
              ("blue-recess","掘り込んだ穴に魂のランタン"),("two-colours","入口に暖色のランタンを加える")],
             "meadow-shelter.jpg")
    if args.through_home:
        archive(data,"meadow-lake-home","meadow-shelter","be935f1b5b30b581e5a3539c2031bd1d0d5fcf26647c28fd4bde42567c954ab2",
                "open-exit-and-follow-lamps-home","Aqualumen-Lake-Homecoming",{(620,65,376):"minecraft:air"})
        pictures(WOOD/"meadow-lake-home",
                 [("outside-shelter","二灯を残して外へ出る"),("meadow-guide","牧草地の入口"),
                  ("ridge-guide","尾根の道しるべ"),("lake-guide","湖畔の灯りに戻る")],
                 "lake-homecoming.jpg")
    data["ticks"] = sum(r["lastTick"]-r["firstTick"] for r in data["chains"])
    data["gameDays"] = data["ticks"]/24000
    data["walkedMetres"] = round(sum(r["walkedMetres"] for r in data["chains"]),2)
    (HERE/"playtime.json").write_text(json.dumps(data, indent=2)+"\n")
    print(data["ticks"], data["gameDays"], data["walkedMetres"])


if __name__ == "__main__":
    main()
