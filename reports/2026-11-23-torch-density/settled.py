"""Register the fixed-time canopy exposure strip against the seven captured Minecraft frames."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from bark import HERE, patch_stats

sys.path.insert(0, str(HERE.parent / "2026-11-22-eye-adaptation"))
from read_meter import decode


def quantiles(values):
    return np.percentile(values,[10,50,90]).round(5).tolist()


def radiance_grid(frame):
    hdr = []
    display = []
    for row in range(8):
        y = 365 + int((row+.5)*185/8)
        for col in range(8):
            x = 700 + int((col+.5)*210/8)
            pixels = frame[900-1-48-row, 16+3*col:19+3*col].astype(int)
            assert np.all(pixels[:,2] == (165 ^ pixels[:,0] ^ pixels[:,1]))
            words = pixels[:,0]*256 + pixels[:,1]
            assert np.all(words < 65535), "diagnostic radiance out of range"
            hdr.append(2**(words*8/65535)-1)
            display.append(frame[y,x])
    return np.asarray(hdr), np.asarray(display)


def main():
    directory = HERE.parent / "2026-11-21-animal-light/woodland/oak-fixed-adaptation"
    result = json.loads((directory / "complete.json").read_text())
    clock = json.loads((directory / "frozen-sky.json").read_text())
    assert result["cleanExit"] and not result["logErrors"] and not result["results"].get("failed")
    assert result["previousSaveUnchanged"] and result["labFilesUnchanged"] and result["modsUnchanged"]
    assert result["savedLevel"]["DayTime"] == clock["dayTime"] and not clock["rain"]
    assert result["results"]["bark-close"]["pose"]["target"] == [561, 65, 418]
    assert result["results"]["removedSoul"]["target"] == [565, 63, 425]
    assert not result["results"].get("stripFailure")
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(directory / "meter.mkv"),
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"])
    strip = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 8, 128, 3)
    samples = []
    for i, image in enumerate(strip):
        fields = decode(image)
        if fields:
            samples.append(dict(t=i/12, **fields))
    assert len(samples) > 0.7*len(strip)
    states = []
    weights = np.array([.2126,.7152,.0722])
    fixed_gain = None
    for photo in result["results"]["bark-close"]["photos"]:
        name = photo["file"]
        with Image.open(directory / name) as image:
            frame = np.asarray(image.convert("RGB"))
            meter = decode(frame[860:868, 16:144])
            assert meter and abs(meter["worldTime"] - clock["dayTime"] % 24000) <= 1
            assert meter["rain"] == 0
            if fixed_gain is None:
                fixed_gain = meter["exposure"]
            hdr, display = radiance_grid(frame)
            # Apply the production shared-peak shoulder at a single gain.
            # The F2 measurement below also contains real shader AA and glare.
            c = hdr*fixed_gain
            fixed_rgb = (c/(1+c.max(axis=1,keepdims=True)))**(1/2.2)
            near = min(samples, key=lambda val:abs(meter["frame"]-val["frame"]))
            assert abs(near["frame"]-meter["frame"]) < 10
            last = [s["exposure"] for s in samples if near["t"]-1 <= s["t"] <= near["t"]]
            assert len(last) >= 10
            states.append(dict(file=name, held=photo["held"], meter=meter, centre=patch_stats(image),
                               linearSceneLumaP10P50P90=quantiles(hdr @ weights),
                               fixedGainDisplayLumaP10P50P90=quantiles(255*fixed_rgb @ weights),
                               actualDisplayLumaP10P50P90=quantiles(display @ weights),
                               exposureRangeInLastSecond=[min(last), max(last)],
                               stripSeconds=near["t"], stripNearestFrameDifference=near["frame"]-meter["frame"]))
    assert len(states) == 7
    data = dict(dayTime=clock["dayTime"], pose=result["results"]["bark-close"]["pose"],
                samples=len(samples), captured=len(strip), states=states,
                commonGainForShoulder=fixed_gain, grid=[8,8],
                meterSceneRect=[1150, 180, 1250, 255], centralPatchRect=[700, 365, 910, 550])
    (HERE / "settled-bark.json").write_text(json.dumps(data, indent=2)+"\n")
    for item in states:
        print(item["file"], round(item["meter"]["exposure"], 3), item["centre"]["lumaCodeP10P50P90"],
              item["exposureRangeInLastSecond"])


if __name__ == "__main__":
    main()
