"""Compare the registered forest, native GPU intervals, and stable image regions."""
from hashlib import sha256
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from visible_pack import HERE, SOURCE_SHA, STUDY_SHA

DENSITY = HERE.parent / "2026-11-23-torch-density"
sys.path.insert(0, str(DENSITY))
from birch_pixels import REGIONS

PREVIEW_TRIAL = "1b4ef25c23a9948ae0069e201f0de4fb14276e44869647a2215e9c0b26606a85"
STAGE = "birch-4"


def read(file):
    return json.loads(file.read_text())


def load_run(name, checksum, profiled):
    folder = DENSITY / name
    r = read(folder / "complete.json")
    pre = read(folder / "preflight.json")
    assert r["complete"] and not r["failure"] and r["originalWorldAndConfigUnchanged"]
    assert r["packSha256"] == r["sourcePackShaNow"] == checksum and r["shaderpackLogged"]
    assert r["size"] == [2560,1440] and "RTX 3080 Ti" in r["gl"]["renderer"]
    assert r["stages"] == [STAGE] and pre["labBefore"] == pre["labAfter"] and not pre["foreignObservations"]
    assert ("gpuProfilerSha256" in read(folder / "observer.json")) == profiled
    summary = read(folder / "summary.json")["scenes"][STAGE]
    frames = []
    for tag in ("ingame","x11-a","x11-b"):
        path = folder / f"{STAGE}-{tag}.png"
        assert sha256(path.read_bytes()).hexdigest() == r["screenshots"][STAGE][tag]
        with Image.open(path) as im:
            frames.append(np.array(im.convert("RGB"), dtype=np.int16))
    timing = {k:summary[k] for k in ("cpuMeanMs","cpuP99Ms","frames")}
    if profiled:
        timing["gpuMeanMs"] = summary["meanMs"]
    return read(folder / "geometry.json"), timing, frames


def differences(delta, mask):
    d = delta[mask]
    return {"pixels":int(d.size),"exact":int(np.count_nonzero(d==0)),
            "above2":int(np.count_nonzero(d>2)),"above8":int(np.count_nonzero(d>8)),
            "p99":float(np.quantile(d,.99)),"max":int(np.max(d))}


def compare(name, candidate, profiled):
    if profiled:
        ref_name = "gp-density-hand-penumbra-split"
    else:
        ref_name = "gp-density-visible-hand-reverse"
    geometry, ref, first = load_run(ref_name, SOURCE_SHA, profiled)
    other, trial, second = load_run(name, candidate, profiled)
    assert geometry == other
    diff = abs(first[0]-second[0]).max(axis=2)
    valid = np.ones(diff.shape, dtype=bool)
    for captures in (first, second):
        for frame in captures[1:]:
            valid &= abs(captures[0]-frame).max(axis=2)<=1
    boxes = {**REGIONS, "nearGrassAndSoil":(40,650,600,850), "canopy":(120,110,830,315),
             "lowerHalf":(0,720,2560,1440)}
    output = {}
    for region, (x,y,right,bottom) in boxes.items():
        d = diff[y:bottom,x:right]
        m = valid[y:bottom,x:right]
        output[region] = {"all":differences(d,np.ones_like(m)), "stableWithinBothRuns":differences(d,m)}
    return {"reference":ref_name, "trial":name, "referenceTiming":ref,"trialTiming":trial,"regions":output}


if __name__ == "__main__":
    profiled = len(sys.argv)==1
    old = read(DENSITY / "gp-density-umbra-pilot/complete.json")
    assert old["packSha256"] == PREVIEW_TRIAL
    name = "gp-density-visible-terrain" if profiled else "gp-density-visible-terrain-reverse"
    result = compare(name, STUDY_SHA, profiled)
    if profiled:
        result["preview12GpuMeanMs"] = read(DENSITY / "gp-density-umbra-pilot/summary.json")["scenes"][STAGE]["meanMs"]
    (HERE / ("profile.json" if profiled else "intervals.json")).write_text(json.dumps(result,indent=2)+"\n")
    print(result["referenceTiming"]["cpuMeanMs"],result["trialTiming"]["cpuMeanMs"],result["regions"]["shadedBark"])
