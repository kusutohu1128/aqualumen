"""Measure the same central bark patch in each of four normal-play F2 captures."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / "2026-11-21-animal-light/woodland/two-flames-oak-r2"
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
ROI = (700, 365, 910, 550)
HANDS = (("empty", "手ぶら"), ("torch", "松明"), ("soul-torch", "魂の松明"), ("empty-restored", "手ぶらに戻す"))


def patch_stats(image):
    pixels = np.asarray(image.crop(ROI).convert("RGB"), dtype=float)
    channels = pixels.reshape(-1, 3)
    luma = pixels @ np.array([0.2126, 0.7152, 0.0722])
    return dict(rgbMedian=np.median(channels, axis=0).tolist(),
                rgbMax=channels.max(axis=0).tolist(),
                lumaCodeP10P50P90=np.percentile(luma, [10, 50, 90]).round(2).tolist(),
                anyChannel255Fraction=float((channels == 255).any(axis=1).mean()),
                anyChannel250Fraction=float((channels >= 250).any(axis=1).mean()))


def main():
    record = json.loads((RUN / "complete.json").read_text())
    assert record["cleanExit"] and not record["logErrors"] and not record["results"].get("failed")
    assert "separate-placed-and-held-light" in record["results"]["completed"]
    assert record["results"]["restoredSoul"]["target"] == [565, 64, 425]
    assert record["results"]["warmStillStanding"]["target"] == [561, 63, 422]
    font = ImageFont.truetype(FONT, 20)
    sheet = Image.new("RGB", (1440, 2 * 248 + 248), (26, 28, 30))
    draw = ImageDraw.Draw(sheet)
    measurements = {}
    for row, series in enumerate(("bark-far", "bark-close")):
        obs = record["results"][series]
        assert obs["pose"]["target"] == [561, 65, 418]
        perpendicular = obs["pose"]["xyz"][0] - 562
        table = {}
        for col, ((name, label), capture) in enumerate(zip(HANDS, obs["photos"], strict=True)):
            filename = f"{series}-{name}-ingame.png"
            assert filename == capture["file"]
            with Image.open(RUN / filename) as frame:
                assert frame.size == (1600, 900)
                table[name] = patch_stats(frame)
                x, y = col * 360, row * 248
                draw.text((x+8, y+4), f"幹まで {perpendicular:.2f} m　{label}", font=font, fill="white")
                sheet.paste(frame.resize((360, 203), Image.Resampling.LANCZOS), (x, y+37))
        measurements[series] = dict(perpendicularToBarkMetres=perpendicular, pose=obs["pose"], hands=table)
    for col, (name, label) in enumerate((("both-placed", "設置済みの松明と魂の松明"),
                                         ("warm-only", "魂の松明を回収"),
                                         ("both-restored", "同じ場所に再設置"))):
        with Image.open(RUN / f"south-{name}-ingame.png") as frame:
            x = col * 360
            draw.text((x+8, 500), label, font=font, fill="white")
            sheet.paste(frame.resize((360, 203), Image.Resampling.LANCZOS), (x, 533))
    draw.multiline_text((1090, 545), "木陰のオーク\nプレビュー8・通常サバイバル\n上の2列は設置した魂の松明を\n回収してから撮影", font=font, fill="white", spacing=7)
    sheet.save(HERE / "oak-light-sources.jpg", quality=94, subsampling=0)
    (HERE / "bark.json").write_text(json.dumps(dict(roiXYXY=ROI, screenshotSize=[1600, 900],
        luma="Weighted display RGB codes, 0-255. The F2 file contains tone-mapped output.",
        series=measurements), indent=2) + "\n")


if __name__ == "__main__":
    main()
