"""Assemble registered ordinary Minecraft F2s at the same camera and exposure settings."""
from PIL import Image,ImageDraw,ImageFont
from results import HERE,PACKS,receipt,photo

def main():
    root=HERE/"grove-cell"
    run=receipt(root,PACKS["cell"][1])
    stages=[("shade","木陰"),("torch","松明を設置"),("trunk","幹を置く"),("trunk-cut","幹を撤去"),
            ("extinguished","松明を撤去"),("walk","牛が光を遮る")]
    board=Image.new("RGB",(1320,3*(371+38)),(21,24,26))
    draw=ImageDraw.Draw(board)
    font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",22,index=0)
    for i,(name,label) in enumerate(stages):
        fx,fy=(i%2)*660,(i//2)*409
        im=Image.fromarray(photo(root,run,name)).resize((660,371),Image.Resampling.LANCZOS)
        board.paste(im,(fx,fy))
        draw.text((fx+12,fy+372),label,font=font,fill=(240,240,236))
    board.save(HERE/"grove-light.jpg",quality=92,subsampling=0)

if __name__=="__main__":
    main()
