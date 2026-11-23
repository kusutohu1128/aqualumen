"""Show the identical static stone patch at its native pixel size for all three settings."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from score import HERE, OLD, WOOD

def main():
    columns=[("元の表示",OLD),("中間調 0.4",WOOD/"midtones-display-hand-cycle"),("中間調 1.0",WOOD/"diffuse-display-hand-cycle")]
    board=Image.new("RGB",(1500,510),(25,27,30))
    draw=ImageDraw.Draw(board)
    font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",20)
    for i,(title,folder) in enumerate(columns):
        frame=Image.open(folder/"sample-1-held-0-ingame.png").convert("RGB")
        left=500*i
        draw.text((left+12,4),title,font=font,fill="white")
        thumb=frame.crop((0,0,1600,864)).resize((500,270),Image.Resampling.LANCZOS)
        board.paste(thumb,(left,40))
        box=(290,420,650,565)
        coords=(left+box[0]*500//1600,40+box[1]*270//864,left+box[2]*500//1600,40+box[3]*270//864)
        draw.rectangle(coords,outline="#ffdb70",width=2)
        board.paste(frame.crop(box),(left+70,335))
    board.save(HERE/"torch-stone.jpg",quality=96)
if __name__=="__main__":
    main()
