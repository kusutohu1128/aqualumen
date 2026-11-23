"""Audit measured exposure and material detail in the private peak-aware exposure trial."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from material_display import HERE, RUN as BASE, ROI, FONT, WEIGHTS, read_scene, display, decode, metrics

RUN = BASE.parent / "oak-light-response"


def captures(folder):
    receipt = json.loads((folder/"complete.json").read_text())
    assert receipt["cleanExit"] and not receipt["logErrors"] and not receipt["results"].get("failed")
    assert receipt["previousSaveUnchanged"] and receipt["labFilesUnchanged"] and receipt["modsUnchanged"]
    assert receipt["results"]["bark-close"]["pose"]["target"] == [561,65,418]
    assert receipt["savedLevel"]["DayTime"] == 63746 and not receipt["results"].get("stripFailure")
    images = {}
    for photo in receipt["results"]["bark-close"]["photos"]:
        path = folder/photo["file"]
        with Image.open(path) as image:
            pixels = np.asarray(image.convert("RGB"))
        meter = decode(pixels[860:868,16:144])
        assert meter and meter["worldTime"]==15746 and meter["rain"]==0
        images[path.name.split("-")[1]] = (meter,pixels)
    return receipt, images


def main():
    _, baseline = captures(BASE)
    receipt, trial = captures(RUN)
    assert receipt["packSha256"]=="aaec7cfc1e7b2b6d29443c087d7ee760795adf44fae4e2191dbda287c84276fb"
    rows = {}
    sheet = Image.new("RGB",(1000,680),(27,29,31))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(FONT,19)
    draw.text((12,2),"試作の実画面　枠は採取した樹皮",font=font,fill="white")
    draw.text((450,2),"元の露出で同じ樹皮を再現",font=font,fill="white")
    draw.text((744,2),"試作の木目（実画面）",font=font,fill="white")
    for j,(i,name,jp) in enumerate((("0","empty","手ぶら"),("1","warm","暖色の松明"),("2","soul","魂の松明"),
                                     ("3","empty","手ぶら"),("4","soul","魂の松明"),("5","warm","暖色の松明"),
                                     ("6","empty","手ぶら"))):
        reference = baseline[{"empty":"0","warm":"1","soul":"2"}[name]][0]["exposure"]
        meter, pixels = trial[i]
        hdr = read_scene(pixels)
        exp = meter["exposure"]
        stock, simulated = display(hdr, reference), display(hdr, exp)
        actual = pixels[ROI[1]:ROI[3],ROI[0]:ROI[2]]
        error = np.abs(actual.astype(float)-simulated)
        assert np.percentile(error,95)<=3
        rows[i] = dict(hand=name,actualExposure=exp,measuredReferenceExposure=reference,
                       sceneLumaMedian=float(np.median(hdr@WEIGHTS)),
                       stockAtTrialPose=metrics(stock),trialF2=metrics(actual),
                       reconstructedTrialP95Error=float(np.percentile(error,95)))
        if j>=3:
            continue
        top=39+j*212
        # The instrument writes diagnostic strips below this view.
        context=Image.fromarray(pixels[:650]).resize((416,169),Image.Resampling.LANCZOS)
        sheet.paste(context,(8,top+30))
        draw.text((8,top),jp,font=font,fill="white")
        draw.rectangle((8+ROI[0]*416//1600,top+30+ROI[1]*169//650,
                        8+ROI[2]*416//1600,top+30+ROI[3]*169//650),outline="#fff080",width=2)
        for x,patch in ((459,stock),(753,actual)):
            sheet.paste(Image.fromarray(patch).resize((218,192),Image.Resampling.NEAREST),(x,top+8))
    sheet.save(HERE/"bark-response.png")
    (HERE/"bark-response.json").write_text(json.dumps(dict(states=rows, pose=receipt["results"]["bark-close"]["pose"],
        note="Each stock reconstruction uses the trial frame's own HDR pixels and the corresponding settled gain "
             "measured on preview 8. The trial column is the lossless F2 display."),indent=2)+"\n")
    for i,s in rows.items():
        print(i,s["hand"],round(s["actualExposure"],3),s["stockAtTrialPose"]["ratioP90P10"],s["trialF2"]["ratioP90P10"])


if __name__ == "__main__":
    main()
