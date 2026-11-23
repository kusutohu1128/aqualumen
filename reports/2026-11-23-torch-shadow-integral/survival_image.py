"""Show the two light sources and both sides of the saved survival birch."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).resolve().parent
record=HERE.parent/"2026-11-21-animal-light/woodland/raised-soul-torch"
panels=[("one-light","Warm torch beside the birch"),("two-lights","Soul torch added on the dirt step"),
        ("blue-flame","From the north"),("east-flame","From the east")]
canvas=Image.new("RGB",(1024,628),(25,28,30))
draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",15)
for i,(name,caption) in enumerate(panels):
    with Image.open(record/(name+"-ingame.png")) as im:
        im=im.convert("RGB");im.thumbnail((504,283),Image.Resampling.LANCZOS)
    x=4+(i%2)*512;y=4+(i//2)*314
    canvas.paste(im,(x,y));draw.text((x+2,y+285),caption,fill="white",font=font)
canvas.save(HERE/"survival.jpg",quality=92)
