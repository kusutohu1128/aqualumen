"""Verify both guarded crossings and the rock shelter's right-left-right light response."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from camp import HERE,WOOD,Region,block_at,load_gz,read
from release import SHA
from plane_result import SHIPPED_SHA
from hashlib import sha256

NAMES=("right-hand-at-lip","left-hand-at-lip","right-again-at-lip")
CROPS={"besideGrassLedge":(1010,600,1032,622),"distantStone":(1230,200,1252,222)}
FONT="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def main():
    baseline=read(WOOD/"lake-to-stone-camp/save.json")
    rows={}
    canvas=Image.new("RGB",(1200,520),"#142020")
    draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype(FONT,16)
    for row,(label,checksum) in enumerate((("reference",SHA),("wet-plane",SHIPPED_SHA))):
        run=WOOD/("camp-rain-"+label)
        r=read(run/"complete.json")
        assert r["labFilesUnchanged"]
        assert r["previousSaveUnchanged"] and r["worldZipUnchanged"] and r["modsUnchanged"] and not r["benchmarkSentinelPresent"]
        assert "RTX 3080 Ti" in r["renderer"] and r["cleanExit"] and not r["logErrors"]
        assert r["packSha256"]==checksum and r["results"]["completed"]==["cross-the-lit-camp"]
        assert r["revisit"]["sourceSavedTime"]==baseline["time"]==102972
        world=Path(read(run/"identity.json")["world"])
        level=load_gz(world/"level.dat")["Data"]
        assert level["GameType"]==level["allowCommands"]==0 and level["WorldGenSettings"]["seed"]==308060
        assert read(run/"frozen-sky.json")["dayTime"]==level["DayTime"]==114000 and level["raining"]==1
        assert level["GameRules"]["doWeatherCycle"]==level["GameRules"]["doDaylightCycle"]=="false"
        player=load_gz(next((world/"playerdata").glob("*.dat")))
        inventory={str(i["Slot"]):[i["id"],i["count"]] for i in player["Inventory"]}
        assert inventory==baseline["inventory"] and player["SelectedItemSlot"]==1
        blocks={(600,71,427):"soul_lantern",(600,70,427):"stone",(599,73,427):"stone",(542,64,395):"torch"}
        for (x,y,z),block in blocks.items():
            region=Region(world/"region"/f"r.{x//512}.{z//512}.mca")
            assert block_at(region.chunk(x//16,z//16),x,y,z)["Name"]=="minecraft:"+block
        motion=read(HERE/(run.name+"-motion.json"))
        assert motion["pack"]==checksum and motion["rainy"]
        hand=[]
        for col,(stage,caption) in enumerate(zip(NAMES,("松明を右手に持つ","左手に持ち替える","右手に戻す"))):
            photo=run/(stage+"-ingame.png")
            with Image.open(photo) as original:
                image=original.convert("RGB")
                assert image.size==(1600,900)
                med={k:np.median(np.asarray(image.crop(box)),axis=(0,1)).tolist() for k,box in CROPS.items()}
                thumb=image.resize((400,225),Image.Resampling.LANCZOS)
            hand.append(dict(camera=stage,medianRGB=med,sha256=sha256(photo.read_bytes()).hexdigest()))
            x,y=400*col,260*row
            canvas.paste(thumb,(x,y))
            x0,y0,x1,y1=CROPS["besideGrassLedge"]
            draw.rectangle((x+x0//4-2,y+y0//4-2,x+x1//4+2,y+y1//4+2),outline="#fa7394",width=2)
            draw.text((x+7,y+230),("プレビュー13" if row==0 else "水膜補正版")+"　"+caption,font=font,fill="white")
        rows[label]=dict(sha=checksum,pose=r["results"]["stationaryView"],hand=hand,
                         cameraAngles=motion["cameraAngles"],movementStart=motion["start"],movementEnd=motion["end"],
                         walkedMetres=r["walkedAfterReloadMetres"],distinctFrames=motion["distinct"],samples=motion["accepted"],
                         deviations=motion["deviationMedianP95P99"],largest=motion["largest"])
    canvas.save(HERE/"camp-hand-light.jpg",quality=95)
    (HERE/"camp-comparison.json").write_text(json.dumps(dict(sourceSaveSHA=baseline["sha256"],patches=CROPS,runs=rows),indent=2)+"\n")
    for k,v in rows.items():
        print(k,v["walkedMetres"],v["deviations"],[r["medianRGB"]["besideGrassLedge"] for r in v["hand"]])


if __name__=="__main__":
    main()
