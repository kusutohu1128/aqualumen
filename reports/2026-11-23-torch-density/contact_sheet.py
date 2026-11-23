"""Label the eight lossless F2 captures without applying exposure or colour correction."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

here=Path(__file__).resolve().parent
source=here/"gp-density-p8-a"
font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",20)
sheet=Image.new("RGB",(1440,476),(27,29,31))
draw=ImageDraw.Draw(sheet)
for row,(site,name) in enumerate((("birch","白樺の木陰"),("sand","砂州"))):
    for col,count in enumerate((0,1,2,4)):
        p=(360*col,238*row)
        draw.text((p[0]+10,p[1]+2),f"{name}　松明 {count} 本",font=font,fill="white")
        with Image.open(source/f"{site}-{count}-ingame.png") as original:
            sheet.paste(original.convert("RGB").resize((360,203),Image.Resampling.LANCZOS),(p[0],p[1]+34))
sheet.save(here/"brightness-and-count.jpg",quality=94,subsampling=0)
