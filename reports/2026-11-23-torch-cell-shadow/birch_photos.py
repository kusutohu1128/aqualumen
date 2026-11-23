"""Show the same bark face before removal, after removal and after moving the torch."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).resolve().parent
WOOD=HERE.parent/"2026-11-21-animal-light/woodland"
def main():
    first=WOOD/"cell-shadow-birch-relocation"
    last=WOOD/"cell-shadow-birch-west"
    frames=[(first/"birch-east-lit-ingame.png","東側に松明"),
            (first/"birch-east-extinguished-ingame.png","東側の松明を回収"),
            (last/"birch-east-after-relocation-ingame.png","北西に松明を置き、東側に戻る")]
    paper=Image.new("RGB",(1440,307),"#fcfcfa")
    draw=ImageDraw.Draw(paper)
    font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",18)
    samples={}
    for i,(p,label) in enumerate(frames):
        with Image.open(p) as image:
            assert image.size==(1600,900)
            image=image.convert("RGB")
            paper.paste(image.resize((480,270),Image.Resampling.LANCZOS),(480*i,0))
            # This rectangle lies in the pale bark in these three east views.
            patch=np.asarray(image)[320:590,675:925]
            samples[p.name]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),medianDisplayRGB=np.median(patch,axis=(0,1)).tolist())
        draw.text((480*i+8,275),label,font=font,fill="#182931")
    (HERE/"bark-screen.json").write_text(json.dumps(dict(regionXYXY=[675,320,925,590],samples=samples),indent=2)+"\n")
    paper.save(HERE/"birch.jpg",quality=95)
if __name__=="__main__":
    main()
