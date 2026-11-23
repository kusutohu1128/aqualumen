"""Compare the new cave run with the existing preview 8 daylight/torch recording."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from settled import HERE, decode
from bark import FONT

FOREST = HERE.parent/"2026-11-22-forest-cave"
BASE = FOREST/"cave-iris8b"
RUN = FOREST/"cave-light-response"
NAMES = ("unlit","warm","soul","empty-again","opening","stone-after-opening",
         "opening-again","placed-warm","rain-over-torch","back-in-forest")


def session(directory):
    data = json.loads((directory/"complete.json").read_text())
    assert "RTX 3080 Ti" in data["renderer"] and data["cleanExit"] and not data["results"].get("failed")
    assert not data["logErrors"] and data["modsUnchanged"] and data["labFilesUnchanged"]
    assert data["worldZipUnchanged"] and data["previousSaveUnchanged"]
    assert not data["results"].get("stripFailure") and not data["benchmarkSentinelPresent"]
    output = {}
    for key in NAMES:
        file = directory/(key+"-ingame.png")
        frame = np.array(Image.open(file).convert("RGB"))
        m=decode(frame[860:868,16:144])
        assert m is not None
        output[key]=dict(exposure=m["exposure"],lampGain=m["lampGain"],time=m["worldTime"],rain=m["rain"],
                         meanDisplayRGB=frame[180:255,1150:1250].mean(axis=(0,1)).round(3).tolist(),
                         meanSceneRGB=[m[k] for k in ("sceneR","sceneG","sceneB")])
    return data,output


def main():
    a, old = session(BASE)
    b, new = session(RUN)
    assert a["worldZipSha256"] == b["worldZipSha256"] and a["revisit"]["sourceSavedTime"] == b["revisit"]["sourceSavedTime"]
    assert b["packSha256"] == "aaec7cfc1e7b2b6d29443c087d7ee760795adf44fae4e2191dbda287c84276fb"
    data=dict(baseline=a["packSha256"],test=b["packSha256"],seed=20261123,
              poses={k:[a["results"][k],b["results"][k]] for k in ("inside","opening","stone-after-opening","outside")},
              stages={k:dict(preview8=old[k],test=new[k]) for k in NAMES},
              note="Same starter and route. Weather and time advance naturally. Each capture retains its measured inputs.")
    (HERE/"cave-response.json").write_text(json.dumps(data,indent=2)+"\n")
    sheet=Image.new("RGB",(1120,528),(27,29,31))
    draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype(FONT,18)
    for row,(folder,version) in enumerate(((BASE,"プレビュー8"),(RUN,"露出試作"))):
        for col,(key,label) in enumerate((("warm","手持ち松明"),("opening","雨の入口"),("stone-after-opening","振り返った岩壁"))):
            left,top=col*373,row*264
            draw.text((left+6,top+3),version+"　"+label,font=font,fill="white")
            with Image.open(folder/(key+"-ingame.png")) as src:
                # Use the same crop, staying above the diagnostic readouts.
                sheet.paste(src.crop((250,0,1350,650)).resize((373,220),Image.Resampling.LANCZOS),(left,top+34))
    sheet.save(HERE/"cave-response.jpg",quality=92,subsampling=0)
    for key in NAMES:
        print(key,round(old[key]["exposure"],2),round(new[key]["exposure"],2),old[key]["time"],new[key]["time"])


if __name__=="__main__":
    main()
