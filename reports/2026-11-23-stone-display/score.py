"""Compare measured F2 display pixels, checksummed HDR samples, and stored oak HDR data."""
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw

from curves import HERE, LUMA, candidate, diffuse, reference, validate_rays
from read_niche import REGIONS, WOOD, decode, stats

sys.path.insert(0, str(HERE.parent / "2026-11-23-torch-density"))
import material_display as oak

OLD = WOOD / "niche-hand-repeats"
NEW = WOOD / "stone-display-hand-cycle"


def bark(curve):
    output = {}
    for i, state in enumerate(("empty", "warm", "soul")):
        frame = np.array(Image.open(oak.RUN / f"settled-{i}-{state}-ingame.png").convert("RGB"))
        gain = oak.decode(frame[860:868,16:144])["exposure"]
        c = oak.read_scene(frame) * gain
        output[state] = dict(exposure=gain, reference=stats(reference(c) @ LUMA),
                             candidate=stats(curve(c) @ LUMA), sampleCount=c.shape[0] * c.shape[1])
    return output


def measure(run,curve):
    record = json.loads((run / "complete.json").read_text())
    assert all(record[k] for k in ("cleanExit", "worldZipUnchanged", "previousSaveUnchanged", "labFilesUnchanged", "modsUnchanged"))
    assert not record["logErrors"] and not record["results"].get("failed") and not record["benchmarkSentinelPresent"]
    assert "RTX 3080 Ti" in record["renderer"]
    entries = []
    for new in sorted(run.glob("sample-*-ingame.png")):
        frame, word, gain = decode(new)
        previous, old_word, old_gain = decode(OLD / new.name)
        assert gain == old_gain
        regions = {}
        for i, (region, (x0, y0, x1, y1)) in enumerate(REGIONS.items()):
            y = y0 + ((np.arange(8)+.5) * (y1-y0) / 8).astype(int)
            x = x0 + ((np.arange(12)+.5) * (x1-x0) / 12).astype(int)
            actual = frame[y[:,None], x].astype(float)/255.
            baseline = previous[y[:,None], x].astype(float)/255.
            c = (2**(word[:,i,:,:3]*8)-1) * gain
            same = np.all(word[:,i] == old_word[:,i], axis=-1)
            regions[region] = dict(sameHDRAndMetadata=int(same.sum()), samples=96,
                old=stats(baseline**2.2 @ LUMA), new=stats(actual**2.2 @ LUMA),
                oldRGB=np.median(baseline*255,axis=(0,1)).tolist(), newRGB=np.median(actual*255,axis=(0,1)).tolist(),
                modelCodeErrorP95=float(np.quantile(abs(actual - curve(c)**(1/2.2)).max(axis=-1)*255, .95)),
                maxCodeHits=int((actual.max(axis=-1)==1).sum()))
        entries.append(dict(frame=new.name, exposure=gain, regions=regions))
    assert len(entries)==9
    return dict(numerical=validate_rays(curve), renderer=record["renderer"], camera=record["results"]["camera"],
                realStone=entries, storedBarkHDR=bark(curve))


def sheet(run,output):
    canvas=Image.new("RGB",(1120,674),(26,28,32))
    draw=ImageDraw.Draw(canvas)
    for j,(label,folder) in enumerate((("Previous display",OLD),("Candidate display",run))):
        draw.text((j*560+8,8),label,fill="white")
        for i,(phase,caption) in enumerate((("0-empty","Empty hand"),("1-held","Holding a torch"))):
            with Image.open(folder/f"sample-{phase}-0-ingame.png") as original:
                scene=original.crop((0,0,1600,866)).resize((560,303),Image.Resampling.LANCZOS)
            canvas.paste(scene,(j*560,32+i*322))
            draw.text((j*560+8,337+i*322),caption,fill="white")
    canvas.save(output,quality=94)


if __name__=="__main__":
    for run,curve,results,photo in ((NEW,candidate,"stone-and-bark.json","stone-comparison.jpg"),
                                  (WOOD/"diffuse-display-hand-cycle",diffuse,"diffuse-and-bark.json","diffuse-comparison.jpg"),
                                  (WOOD/"midtones-display-hand-cycle",lambda c: diffuse(c,.4),"default-and-bark.json","default-comparison.jpg")):
        output=measure(run,curve)
        (HERE/results).write_text(json.dumps(output,indent=2)+"\n")
        sheet(run,HERE/photo)
