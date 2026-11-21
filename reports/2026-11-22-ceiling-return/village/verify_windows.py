"""Check the remodeled house in its consecutive survival saves and compare its real F2 captures."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parents[1] / "2026-11-21-settlement-light/tools"))
from mcnbt import Region, block_at, load_gz

cells = {
    "rear": (-902, 71, 579), "front": (-901, 71, 576),
    "soulTorch": (-902, 70, 578), "hangingLantern": (-902, 73, 578),
}


def saved(name):
    world = Path(json.loads((here/name/"identity.json").read_text())["world"])
    run = json.loads((here/name/"complete.json").read_text())
    assert (run["cleanExit"] and run["labFilesUnchanged"] and run["previousSaveUnchanged"]
            and not run["benchmarkSentinelPresent"] and not run["logErrors"] and not run["results"].get("failed"))
    level = load_gz(world/"level.dat")["Data"]
    assert level["allowCommands"] == level["GameType"] == 0 and level["WorldGenSettings"]["seed"] == 20261139
    region = Region(world/"region/r.-2.1.mca")
    blocks = {key: block_at(region.chunk(x//16, z//16), x, y, z)["Name"] for key, (x, y, z) in cells.items()}
    assert blocks["soulTorch"] == "minecraft:soul_torch" and blocks["hangingLantern"] == "minecraft:lantern"
    return dict(blocks=blocks, time=level["Time"], rain=bool(level["raining"]), pack=run["packSha256"],
                previous=run["revisit"]["sourceRun"], previousTime=run["revisit"]["sourceSavedTime"])


def main():
    saves = {name: saved(name) for name in ("archive-revisit", "window-move", "porch-window")}
    before, after, outside = saves.values()
    assert before["blocks"]["rear"] == "minecraft:glass_pane" and before["blocks"]["front"] == "minecraft:stripped_spruce_log"
    assert after["blocks"]["rear"] == "minecraft:spruce_planks" and after["blocks"]["front"] == "minecraft:air"
    assert after["blocks"] == outside["blocks"] and after["time"] == outside["previousTime"]
    assert before["time"] == after["previousTime"] and before["pack"] == after["pack"] == outside["pack"]
    photos = [
        ("window-move", "original-beam", "裏の窓があるとき"),
        ("window-move", "closed-beam", "裏の窓を板で塞ぐ"),
        ("window-move", "relocated-beam", "玄関の横に窓を開ける"),
        ("porch-window", "outside-open", "玄関側の窓を外から見る"),
        ("porch-window", "outside-boarded", "同じ窓に板をはめる"),
        ("porch-window", "outside-reopened", "板を外して開け直す"),
    ]
    gallery = Image.new("RGB", (3*480, 2*311), (22, 25, 26))
    pen = ImageDraw.Draw(gallery)
    font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 21)
    samples = {}
    for i, (folder, name, title) in enumerate(photos):
        path = here/folder/f"{name}-ingame.png"
        img = Image.open(path).convert("RGB")
        assert img.size == (1600, 900)
        crop = (1150, 180, 1250, 255) if folder == "window-move" else (780, 430, 820, 470)
        samples[name] = {"file": str(path.relative_to(here)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "roi": crop, "meanDisplayRGB": np.array(img.crop(crop)).mean(axis=(0, 1)).round(3).tolist()}
        x, y = (i%3)*480, (i//3)*311
        gallery.paste(img.resize((480, 270), Image.Resampling.LANCZOS), (x, y))
        pen.text((x+10, y+273), title, font=font, fill="white")
    gallery.save(here/"windows.jpg", quality=94)
    (here/"windows.json").write_text(json.dumps({"saves": saves, "positions": cells, "photos": samples}, indent=2)+"\n")
    print(json.dumps(samples, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
