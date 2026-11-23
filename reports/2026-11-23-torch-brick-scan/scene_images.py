"""Contact sheet of original F2 photographs taken while walking the private survival world."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

here=Path(__file__).resolve().parent
run=here.parent/"2026-11-21-animal-light/woodland/row-scan-camp-walk"
stages=(("birch-at-departure","Birch at departure"),("entrance-light","New torch on the path"),
        ("niche-empty-hand","Stone niche / empty hand"),("niche-held-torch","Stone niche / torch in hand"))
canvas=Image.new("RGB",(1024,630),(23,25,26))
draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",16)
for i,(name,title) in enumerate(stages):
    with Image.open(run/(name+"-ingame.png")) as frame:
        frame=frame.convert("RGB").resize((504,284),Image.Resampling.LANCZOS)
    x=4+512*(i%2); y=4+315*(i//2)
    canvas.paste(frame,(x,y))
    draw.text((x+2,y+287),title,font=font,fill="white")
canvas.save(here/"walk.jpg",quality=93)
