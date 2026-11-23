"""Verify both saved lanterns; advance the survival ledger only for ordinary weather."""
import json
from hashlib import sha256
from pathlib import Path
import sys

import numpy as np
from PIL import Image,ImageDraw,ImageFont
from room import HERE,ROOT,PREVIOUS
from measure import TRIAL_SHA
from release import SHA
sys.path.insert(0,str(HERE.parent/"2026-11-22-ceiling-return"))
from save_checkpoint import preserve, Region, block_at, load_gz
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
from playtime import extend

WOOD=HERE.parent/"2026-11-21-animal-light/woodland"


def read(p):
    return json.loads(p.read_text())


def lamp_colors(folder):
    # Same stone texture in the two F2 images of this outing. The distant
    # right side is clear of the flame, crosshair, hotbar and player's hand.
    box=(1270,565,1360,619)
    crops={}
    sources={}
    for name in ("stone-blue","stone-blue-and-warm"):
        path=folder/f"{name}-ingame.png"
        with Image.open(path) as image:
            assert image.size==(1600,900)
            crops[name]=np.asarray(image.convert("RGB").crop(box))
        sources[path.name]=sha256(path.read_bytes()).hexdigest()
    luminance=np.array([.2126,.7152,.0722])
    textures=[(rgb@luminance).ravel() for rgb in crops.values()]
    return dict(cropXYXY=box,sourceSHA256=sources,
                medianRGB={key:np.median(rgb,axis=(0,1)).tolist() for key,rgb in crops.items()},
                textureCorrelation=float(np.corrcoef(*textures)[0,1]))


def verify(directory, wet):
    run=read(directory/"complete.json")
    assert run["cleanExit"] and not run["logErrors"] and not run["benchmarkSentinelPresent"]
    assert run["previousSaveUnchanged"] and run["worldZipUnchanged"] and run["labFilesUnchanged"] and run["modsUnchanged"]
    assert run["revisit"]["sourceRun"]=="lower-shore-torch" and run["revisit"]["sourceSavedTime"]==97754
    assert run["results"]["completed"]==["light-the-stone-overhang"] and not run["results"].get("failed")
    assert run["packSha256"]==(TRIAL_SHA if wet else SHA)
    world=Path(read(directory/"identity.json")["world"])
    data=load_gz(world/"level.dat")["Data"]
    assert data["GameType"]==data["allowCommands"]==0 and data["WorldGenSettings"]["seed"]==308060
    if wet:
        assert read(directory/"frozen-sky.json")["dayTime"]==data["DayTime"]==114000 and data["raining"]==1
        assert data["GameRules"]["doWeatherCycle"]==data["GameRules"]["doDaylightCycle"]=="false"
    else:
        assert data["Time"]==data["DayTime"] and data["Time"]>97754 and not (directory/"frozen-sky.json").exists()
        assert data["GameRules"]["doWeatherCycle"]==data["GameRules"]["doDaylightCycle"]=="true"
    expected={tuple(map(int,k.split(","))):v for k,v in read(WOOD/"lower-shore-torch/save.json")["verifiedBlocks"].items()}
    expected.update({(600,71,427):"minecraft:soul_lantern",(600,70,427):"minecraft:stone",(599,73,427):"minecraft:stone"})
    for (x,y,z),block in expected.items():
        reg=Region(world/"region"/f"r.{x//512}.{z//512}.mca")
        actual=block_at(reg.chunk(x//16,z//16),x,y,z)["Name"]
        if (x,y,z)==(542,63,395):
            # Exposed dirt supporting the torch can become grass on a random tick.
            assert block=="minecraft:dirt" and actual in (block,"minecraft:grass_block")
            expected[(x,y,z)]=actual
        else:
            assert actual==block,((x,y,z),actual,block)
    return run,expected


def main():
    arm=sys.argv[1]
    assert arm in ("rain","survival")
    wet=arm=="rain"
    folder=WOOD/("lake-to-wet-stone" if wet else "lake-to-stone-camp")
    run,blocks=verify(folder,wet)
    colors=lamp_colors(folder)
    (HERE/(arm+"-lantern.json")).write_text(json.dumps(colors,indent=2)+"\n")
    if not wet:
        ledger=read(PREVIOUS/"playtime.json")
        extend(ledger["chains"],folder,308060,SHA,"light-the-stone-overhang")
        preserve(folder,"Aqualumen-Stone-Camp",blocks)
        ledger["ticks"]=sum(row["lastTick"]-row["firstTick"] for row in ledger["chains"])
        ledger["gameDays"]=ledger["ticks"]/24000
        ledger["walkedMetres"]=round(sum(row["walkedMetres"] for row in ledger["chains"]),2)
        (HERE/"playtime.json").write_text(json.dumps(ledger,indent=2)+"\n")
    canvas=Image.new("RGB",(1080,690),"#142020")
    font=ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",17)
    draw=ImageDraw.Draw(canvas)
    shots=(("from-the-water","湖畔の二つの灯りを出発"),("open-lip","手に松明を持ち、岩の張り出しに向く"),
           ("stone-blue","岩の下に魂のランタンを置く"),("stone-blue-and-warm","同じ視点で暖色の松明を取り出す"))
    for i,(stage,label) in enumerate(shots):
        x,y=i%2*540,i//2*345
        with Image.open(folder/f"{stage}-ingame.png") as im:
            canvas.paste(im.convert("RGB").resize((540,304),Image.Resampling.LANCZOS),(x,y))
        draw.text((x+9,y+309),label,font=font,fill="white")
    canvas.save(HERE/("rain-walk.jpg" if wet else "survival-walk.jpg"),quality=94)
    print(arm,run["walkedAfterReloadMetres"],run["savedLevel"])


if __name__=="__main__":
    main()
