"""Compare the native receiver in the window, frame, and removed-door controls."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
args = argparse.ArgumentParser(description=__doc__)
args.add_argument("--after", choices=("projection-final", "area", "coplanar"), default="projection-final")
opts = args.parse_args()
prefix = {"projection-final": "projection", "area": "final-projection", "coplanar": "shipped-projection"}[opts.after]

before = json.loads((HERE / "baseline/complete.json").read_text())
after = json.loads((HERE / opts.after / "complete.json").read_text())
labels = ("left opening", "central stile", "right opening", "bottom rail")


def patches(receipt):
    return {role: {label: data["meanSRGB8"] for label, data in zip(labels, image["patches"])}
            for role, image in receipt["images"].items()}


data = {"camera": "both packs have camera in front of door; door remains outside field of view",
        "before": patches(before), "after": patches(after), "renderer": after["renderer"], "afterSHA256": after["sha256"], "beforeSHA256": before["sha256"]}
out = HERE / (prefix + ".json")
assert not out.exists()
out.write_text(json.dumps(data, indent=2))
font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 18)
rows = [("baseline", "oak", "1.5.0　オーク・閉"), (opts.after, "oak", "1.6　オーク・閉"),
        (opts.after, "dark", "ダークオーク・閉"), (opts.after, "acacia", "アカシア・閉"),
        (opts.after, "open", "オーク・開"), (opts.after, "empty", "扉を撤去")]
sheet = Image.new("RGB", (960, 3*303), (22, 25, 28))
pen = ImageDraw.Draw(sheet)
for i, (run, role, label) in enumerate(rows):
    im = Image.open(HERE / run / (role + ".png")).convert("RGB")
    x, y = (i % 2)*480, (i//2)*303
    sheet.paste(im.resize((480, 270), Image.Resampling.LANCZOS), (x, y))
    pen.text((x+10, y+271), label, (245, 245, 245), font)
sheet.save(HERE / (prefix + ".jpg"), quality=91)
print(json.dumps(data["after"], ensure_ascii=False))
