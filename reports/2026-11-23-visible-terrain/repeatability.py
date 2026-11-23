"""Bound persistent display differences across both orderings and all six images per pack."""
import json
import numpy as np
from PIL import Image
from forest import DENSITY, HERE


def envelope(runs):
    lo=hi=None
    for label in runs:
        for tag in ("ingame","x11-a","x11-b"):
            with Image.open(DENSITY/label/f"birch-4-{tag}.png") as im:
                a=np.array(im.convert("RGB"),dtype=np.int16)
            lo=a if lo is None else np.minimum(lo,a)
            hi=a if hi is None else np.maximum(hi,a)
    return lo,hi


def main():
    # The per-run analysis verifies projection, images and the fixed scene.
    profile,reverse=[json.loads((HERE/p).read_text()) for p in ("profile.json","intervals.json")]
    cmp=[envelope([r[side] for r in (profile,reverse)]) for side in ("reference","trial")]
    (a,b),(c,d)=cmp
    gap=np.maximum(0,np.maximum(a-d,c-b)).max(axis=2)
    stable=((b-a).max(axis=2)<=1)&((d-c).max(axis=2)<=1)
    rows={}
    for label,selection in [("allScreen",np.ones_like(stable)),("lowerHalf",np.indices(gap.shape)[0]>=720)]:
        for fixed in (False,True):
            mask=selection&stable if fixed else selection
            vals=gap[mask]
            rows[label+("-stable" if fixed else "")]={"samples":int(mask.sum()),
                "maximumGap":int(vals.max()),"above2":int((vals>2).sum()),"above8":int((vals>8).sum())}
    y,x=np.unravel_index(gap.argmax(),gap.shape)
    rows["worst"]={"pixel":[int(x),int(y)],"forwardRange":[a[y,x].tolist(),b[y,x].tolist()],
                   "deferredRange":[c[y,x].tolist(),d[y,x].tolist()]}
    (HERE/"persistent-pixels.json").write_text(json.dumps(rows,indent=2)+"\n")
    print(rows)


if __name__=="__main__":
    main()
