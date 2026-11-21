"""Make two real-game comparisons from the exact release shots."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

here = Path(__file__).resolve().parent
font = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
title_font = ImageFont.truetype(font, 29)
label_font = ImageFont.truetype(font, 22)
small_font = ImageFont.truetype(font, 18)
def sheet(name, title, columns):
    width = 600 if len(columns) == 2 else 473
    canvas = Image.new("RGB", ((width + 20) * len(columns) + 4, 552 if len(columns) == 2 else 485), "#161916")
    draw = ImageDraw.Draw(canvas)
    draw.text((15, 8), title, font=title_font, fill="#eeeae0")
    for i, (label, source) in enumerate(columns):
        pos = 15+i*(width+20)
        frame = Image.open(source).convert("RGB")
        h = round(width*frame.height/frame.width)
        canvas.paste(frame.resize((width,h), Image.Resampling.LANCZOS), (pos,57))
        draw.text((pos,63+h), label, font=label_font,fill="#eeeae0")
        crop = frame.crop((548,286,714,443))
        crop.thumbnail((148,100),Image.Resampling.LANCZOS)
        canvas.paste(crop,(pos,101+h))
        draw.text((pos+crop.width+12,114+h),"壁の影を拡大",font=small_font,fill="#c5c5b9")
    canvas.save(here / name, quality=94, subsampling=0)

variant = sys.argv[1] if len(sys.argv)>1 else "accepted"
comparison = "release-comparison.jpg" if variant=="accepted" else variant+"-comparison.jpg"
species = "species-comparison.jpg" if variant=="accepted" else variant+"-species.jpg"
sheet(comparison, "同じ松明、同じ葉、同じ白い壁",[
    ("1.7.0",here/"before/foliage.png"),("1.8.0",here/variant/"foliage.png")])
sheet(species,"同じシーランタンで照らした三種類の葉の影",[
    (label,here/variant/(tag+"-white.png")) for tag,label in (("oak","オーク"),("birch","シラカバ"),("cherry","サクラ"))])
