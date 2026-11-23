"""Present the actual before/after views of the two persistent cave lights."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
CAVE = HERE.parent / "2026-11-22-forest-cave/evening-alcove"


def main():
    receipt = json.loads((CAVE / "complete.json").read_text())
    results = receipt["results"]
    assert receipt["cleanExit"] and not results.get("failed")
    assert results["minedStone"] == results["soulInAlcove"]["target"] == [1667,93,1065]
    assert results["placed"]["target"] == [1666,93,1065]
    assert "outside" in results
    sheet = Image.new("RGB", (1440, 620), (27,29,31))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",22)
    shots = (("rain-at-entrance","森から洞窟へ"), ("unlit","手前の岩壁・手ぶら"),
             ("rain-over-torch","暖色の松明を残して入口を見る"), ("before-cut","採掘前・設置した暖色の松明"),
             ("bare-recess","石を一つ掘った直後"), ("mixed-cave-light","掘った場所に魂の松明を設置"))
    for n,(label, caption) in enumerate(shots):
        left, top = 480*(n % 3), 310*(n // 3)
        draw.text((left+8, top+2),caption,font=font,fill="white")
        with Image.open(CAVE / (label+"-ingame.png")) as frame:
            sheet.paste(frame.convert("RGB").resize((480,270),Image.Resampling.LANCZOS),(left,top+36))
    sheet.save(HERE/"forest-cave-lights.jpg",quality=94,subsampling=0)


if __name__ == "__main__":
    main()
