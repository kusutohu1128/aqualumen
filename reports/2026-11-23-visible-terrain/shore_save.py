"""Verify the lowered torch in the saved world and extend its single survival timeline."""
import json
import sys

from PIL import Image, ImageDraw, ImageFont

from visible_pack import HERE, STUDY_SHA

sys.path.insert(0, str(HERE.parent / "2026-11-22-ceiling-return"))
from save_checkpoint import preserve
sys.path.insert(0, str(HERE.parent / "2026-11-23-torch-density"))
from playtime import extend


def main(name):
    wood = HERE.parent / "2026-11-21-animal-light/woodland"
    run = wood / name
    receipt = json.loads((run / "complete.json").read_text())
    previous = "bank-light-at-dawn"
    assert receipt["labFilesUnchanged"] and receipt["modsUnchanged"]
    assert receipt["revisit"]["sourceRun"] == previous
    old = json.loads((wood / previous / "save.json").read_text())
    blocks = {tuple(map(int, key.split(","))): block for key, block in old["verifiedBlocks"].items()}
    assert blocks[(542,64,395)] == "minecraft:dirt" and blocks[(543,64,395)] == "minecraft:wall_torch"
    assert blocks[(542,63,395)] == "minecraft:dirt" and blocks[(541,63,395)] == "minecraft:soul_lantern"
    blocks.update({(542,64,395): "minecraft:torch", (543,64,395): "minecraft:air"})
    ledger = json.loads((HERE.parent / "2026-11-23-torch-penumbra/playtime.json").read_text())
    extend(ledger["chains"], run, 308060, STUDY_SHA, "lower-the-shore-torch")
    preserve(run, "Aqualumen-Low-Shore-Light", blocks)
    ledger["ticks"] = sum(row["lastTick"] - row["firstTick"] for row in ledger["chains"])
    ledger["gameDays"] = ledger["ticks"] / 24000
    ledger["walkedMetres"] = round(sum(row["walkedMetres"] for row in ledger["chains"]), 2)
    (HERE / "playtime.json").write_text(json.dumps(ledger, indent=2) + "\n")

    canvas = Image.new("RGB", (1024,648), "#17211f")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 17)
    stages = [("held-torch-and-wall", "松明を持ち、支えの土を狙う"),
              ("removed-support", "上段の土を掘った直後"),
              ("lowered-shore-torch", "下段の土に松明を立てる"),
              ("lower-post-from-water", "砂州から新しい目印を振り返る")]
    for i, (stage, caption) in enumerate(stages):
        x, y = i%2*512, i//2*324
        with Image.open(run / f"{stage}-ingame.png") as frame:
            assert frame.size == (1600,900)
            canvas.paste(frame.convert("RGB").resize((512,288), Image.Resampling.LANCZOS), (x,y))
        draw.text((x+10,y+292), caption, font=font, fill="white")
    canvas.save(HERE / "lowered-torch.jpg", quality=94)
    print(ledger["ticks"], ledger["gameDays"], ledger["walkedMetres"])


if __name__ == "__main__":
    main(sys.argv[1])
