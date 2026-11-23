"""Record the real shore build after Minecraft saves and closes normally."""
import json
from pathlib import Path
import sys
from PIL import Image,ImageDraw,ImageFont
from pack import HERE
sys.path.insert(0,str(HERE.parent/"2026-11-22-ceiling-return"))
from save_checkpoint import preserve
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
from playtime import extend

wood=HERE.parent/"2026-11-21-animal-light/woodland"
folder=wood/sys.argv[1]
read=lambda p:json.loads(p.read_text())
r=read(folder/"complete.json")
assert r["results"]["completed"]==["build-two-sided-shore-light"] and not r["results"].get("failed")
assert r["labFilesUnchanged"] and r["modsUnchanged"] and r["revisit"]["sourceRun"]=="meadow-lake-home"
old=read(wood/"meadow-lake-home/save.json")
blocks={tuple(map(int,k.split(","))):v for k,v in old["verifiedBlocks"].items()}
blocks.update({(542,63,395):"minecraft:dirt",(542,64,395):"minecraft:dirt",(543,64,395):"minecraft:wall_torch"})
preserve(folder,"Aqualumen-Two-Sided-Shore",blocks)
data=read(HERE.parent/"2026-11-23-torch-umbra/playtime.json")
extend(data["chains"],folder,308060,"4a0c68c66a5ded34e2d46ebe38d24c32177fbee2385271f0f01dd594aa34f096","build-two-sided-shore-light")
data["ticks"]=sum(row["lastTick"]-row["firstTick"] for row in data["chains"])
data["gameDays"]=data["ticks"]/24000
data["walkedMetres"]=round(sum(row["walkedMetres"] for row in data["chains"]),2)
(HERE/"playtime.json").write_text(json.dumps(data,indent=2)+"\n")
canvas=Image.new("RGB",(1024,650),"#17211f")
draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",17)
for i,(name,label) in enumerate([("blue-before-screen","前回の湖畔の魂のランタン"),("landward-torch","陸側の面に松明を追加"),
                                  ("two-sided-marker","砂州から振り返る"),("morning-water","同じ朝の湖面")]):
    with Image.open(folder/(name+"-ingame.png")) as im:
        assert im.size==(1600,900)
        x,y=(i%2)*512,(i//2)*325
        canvas.paste(im.convert("RGB").resize((512,288),Image.Resampling.LANCZOS),(x,y))
        draw.text((x+10,y+291),label,font=font,fill="white")
canvas.save(HERE/"bank.jpg",quality=94)
print(data["ticks"],data["gameDays"],data["walkedMetres"])
