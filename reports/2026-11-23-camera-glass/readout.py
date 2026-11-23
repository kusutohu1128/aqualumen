"""Measure the final framebuffer response to adjacent known background radiances."""
from pathlib import Path
import json
import math
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent
RED=np.array([.85,.20,.16])
BLUE=np.array([.19,.36,.86])
def reference():
    t=1/8
    one=RED**t
    blue=BLUE**t
    return dict(none=np.ones(3),one=one,blue=blue,twice=one**2,mix=one*blue,reverse=one*blue,
                oblique=RED**(t/math.cos(math.radians(30))),inside=RED**(t/2),front=np.ones(3),removed=np.ones(3))
def measure(path):
    frame=np.asarray(Image.open(path).convert("RGB"),dtype=float)
    h,w,_=frame.shape
    # The sample is centred horizontally; two bands avoid the crosshair.
    bands=[frame[h//2+i:h//2+i+8,w//2-8:w//2+8] for i in (-22,14)]
    band=np.concatenate(bands,axis=0)
    differences=(band[:,::2]-band[:,1::2])/(255*.5)
    return {k:np.round(np.percentile(differences,p,axis=(0,1)),5).tolist()
            for k,p in (("p10",10),("median",50),("p90",90))}
def results():
    expect=reference()
    data={}
    for name in ("study-meter","base-meter"):
        folder=HERE/name
        data[name]={}
        for path in sorted(folder.glob("*-ingame.png")):
            stage=path.name.removesuffix("-ingame.png")
            m=measure(path)
            m.update(expected=np.round(expect[stage],5).tolist(),
                     maxAbsMedianError=round(float(np.max(np.abs(m["median"]-expect[stage]))),5))
            data[name][stage]=m
    return data
if __name__=="__main__":
    import argparse
    cli=argparse.ArgumentParser();cli.add_argument("--save",action="store_true");args=cli.parse_args()
    data=results()
    for name,stages in data.items():
        for stage,m in stages.items(): print(name,stage,m["median"],m["maxAbsMedianError"])
    if args.save:
        expected=reference()
        assert set(data["study-meter"])==set(expected)
        assert set(data["base-meter"])=={"none","one","twice","front"}
        for name in data:
            assert (HERE/name/"complete.json").is_file()
        (HERE/"transmission.json").write_text(json.dumps(data,indent=2)+"\n")
