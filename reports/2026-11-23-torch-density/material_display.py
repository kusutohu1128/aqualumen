"""Compare two display choices on the same measured HDR bark pixels."""
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from bark import HERE, FONT, ROI
from settled import decode, radiance_grid, quantiles

RUN = HERE.parent / "2026-11-21-animal-light/woodland/oak-material-patch"
WEIGHTS = np.array([.2126,.7152,.0722])


def read_scene(frame):
    packet = frame[651:836,16:646][::-1].astype(int)
    assert packet.shape == (185,630,3)
    assert np.all(packet[:,:,2] == (165 ^ packet[:,:,0] ^ packet[:,:,1]))
    words = (256*packet[:,:,0]+packet[:,:,1]).reshape(185,210,3)
    assert words.max() < 65535
    hdr = 2**(8*words/65535)-1
    grid, _ = radiance_grid(frame)
    indices = ((np.arange(8)+.5)/8)
    check = hdr[(indices*185).astype(int)[:,None], (indices*210).astype(int)[None,:]].reshape(-1,3)
    assert np.array_equal(grid,check), "dense and sparse radiance disagree"
    return hdr


def display(hdr, exposure, highlight_mix=0.):
    incident = hdr*exposure
    base = incident/(1.+incident.max(axis=2,keepdims=True))
    if highlight_mix:
        # Gently recover display luminance by using some of the remaining
        # neutral headroom. The shift increases continuously with saturation.
        y = incident @ WEIGHTS
        base_y = base @ WEIGHTS
        neutral = (y/(1+y)-base_y)/(1-base_y)
        base += highlight_mix*neutral[:,:,None]*(1-base)
    return np.rint(255*base**(1/2.2)).astype(np.uint8)


def metrics(rgb):
    values = rgb @ WEIGHTS
    q = quantiles(values)
    return dict(lumaP10P50P90=q, ratioP90P10=round(q[2]/q[0],4),
                rgbMedian=np.median(rgb,axis=(0,1)).tolist())


def main():
    record = json.loads((RUN/"complete.json").read_text())
    assert record["cleanExit"] and not record["logErrors"] and not record["results"].get("failed")
    assert record["labFilesUnchanged"] and record["previousSaveUnchanged"] and record["modsUnchanged"]
    assert record["packSha256"] == "cd28e244a7340502e012b759edf8aad934814fe36d5ad6e8588c61a3ea4a9e12"
    pose = record["results"]["bark-close"]["pose"]
    assert pose["target"] == [561,65,418]
    labels = ("元の画面・枠が測定位置","元の画面の木目","同じ入力で露出を半分に","明部の彩度を少し抑える")
    sheet = Image.new("RGB", (1200, 728), (28,29,31))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(FONT,18)
    for i,title in enumerate(labels):
        draw.text((i*300+8,4),title,font=font,fill="white")
    samples = {}
    for row, (state, label) in enumerate((("empty","手ぶら"),("warm","松明"),("soul","魂の松明"))):
        filename = f"settled-{row}-{state}-ingame.png"
        with Image.open(RUN/filename) as source:
            frame = np.asarray(source.convert("RGB"))
        meter = decode(frame[860:868,16:144])
        assert meter and abs(meter["worldTime"]-15746)<=1 and meter["rain"]==0
        gain = meter["exposure"]
        hdr = read_scene(frame)
        actual = frame[ROI[1]:ROI[3],ROI[0]:ROI[2]]
        stock, half, softer = display(hdr,gain), display(hdr,.5*gain), display(hdr,gain,.35)
        error = np.abs(stock.astype(float)-actual)
        # The actual screen has neighbouring-pixel AA and glare. Retain their
        # measured difference to the unfiltered per-pixel reconstruction.
        samples[state] = dict(exposure=gain, sceneLumaP10P50P90=quantiles(hdr@WEIGHTS),
                              actual=metrics(actual), model=metrics(stock), half=metrics(half),
                              neutralHighlight35=metrics(softer), medianAbsCodeError=float(np.median(error)),
                              p95AbsCodeError=float(np.percentile(error,95)))
        assert np.percentile(error,95)<=3, samples[state]
        top = 40+row*228
        # The small readout strips encode numbers and do not belong to the scene.
        context = Image.fromarray(frame[:650]).resize((300,122),Image.Resampling.LANCZOS)
        sheet.paste(context,(0,top+40))
        draw.rectangle((ROI[0]*300//1600,top+40+ROI[1]*122//650,
                        ROI[2]*300//1600,top+40+ROI[3]*122//650),outline="#ffff80",width=2)
        draw.text((8,top+6), label, font=font, fill="white")
        for col, image in enumerate((actual,half,softer),1):
            sheet.paste(Image.fromarray(image).resize((239,211),Image.Resampling.NEAREST),(col*300+30,top+4))
    sheet.save(HERE/"bark-display-study.png")
    with (HERE/"bark-display-study.json").open("w") as out:
        json.dump(dict(source="Lossless on-GPU samples of colortex0 before the display transform",
                       size=[210,185], pose=pose, samples=samples),out,indent=2)
        out.write("\n")
    for state,sample in samples.items():
        print(state, sample["actual"], sample["half"]["ratioP90P10"], sample["neutralHighlight35"]["ratioP90P10"])


if __name__ == "__main__":
    main()
