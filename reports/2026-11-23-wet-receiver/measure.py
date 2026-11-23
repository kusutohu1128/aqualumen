"""Compare the two encodings at matching geometry, time, rain, lights and exposure."""
from collections import deque
from hashlib import sha256
import json
import numpy as np
from PIL import Image
from room import HERE, PREVIOUS, STAGES, SOURCE_SHA, STUDY_SHA
from analyze_meter import CAL, summarize

PAIR_SHA = "e8edba69cf96b12c9106814c68d1a1eda590515793fe1018fd6d09691d1d34b0"
TRIAL_SHA = "3e5608f94c0c53abe141f6e8ecc504d20143f13f39d8695844b3f6a86b2c5dcf"


def read(path):
    return json.loads(path.read_text())


def receipt(label, expected, geometry=None):
    folder=HERE/label
    r=read(folder/"complete.json")
    g=read(folder/"preflight.json")
    assert r["complete"] and not r["failure"] and r["shaderpackLogged"] and r["originalWorldAndConfigUnchanged"]
    assert r["packSha256"]==r["sourcePackShaNow"]==expected and r["size"]==[1600,900]
    assert r["stages"]==list(STAGES) and "RTX 3080 Ti" in r["gl"]["renderer"]
    assert g["labBefore"]==g["labAfter"] and not g["foreignObservations"]
    if geometry is None:
        geometry=read(PREVIOUS/"wet-ownership/geometry.json")
    assert read(folder/"geometry.json")==geometry
    return r


def frame(label, r, stage, name):
    path=HERE/label/f"{stage}-{name}.png"
    assert sha256(path.read_bytes()).hexdigest()==r["screenshots"][stage][name]
    with Image.open(path) as im: return np.asarray(im.convert("RGB"))


def largest_cluster(mask):
    remaining=set(zip(*np.where(mask)))
    biggest=0
    while remaining:
        queue=deque([remaining.pop()])
        n=0
        while queue:
            y,x=queue.popleft()
            n+=1
            for pt in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                if pt in remaining:
                    remaining.remove(pt)
                    queue.append(pt)
        biggest=max(biggest,n)
    return biggest


def panels(image):
    assert np.array_equal(image[2,8:264],CAL)
    old,new,display=image[:450,:800],image[:450,800:],image[450:,:800]
    valid=np.ones((450,800),dtype=bool)
    valid[2,8:264]=False
    flags=old[:,:,2]
    assert np.array_equal(flags[valid],new[:,:,2][valid]) and np.array_equal(flags[valid],display[:,:,2][valid])
    assert not (flags[valid]&128).any()
    owner=flags&15
    eligible=(owner>=2)&(owner<=5)
    added=(flags&32)!=0
    removed=(flags&16)!=0
    assert not (valid & (added ^ removed)).any()
    assert not (valid & (eligible!=added) & (owner!=6)).any()
    scalar=lambda p:p[:,:,0].astype('uint16')+(p[:,:,1].astype('uint16')<<8)
    return valid,owner,scalar(old),scalar(new),display[:,:,:2]


def metrics(mask,codes,steps):
    assert mask.any()
    b=codes[mask]
    hdr=summarize(np.bincount(b,minlength=65536))
    y,x=np.unravel_index(np.where(mask,codes,0).argmax(),mask.shape)
    d=steps[mask]
    return dict(samples=int(mask.sum()),linear=hdr,peakSceneXY=[int(2*x+1),int(2*y+1)],
                maxDisplayCodes=int(d.max()),oneCode=int(np.sum(d==1)),aboveOne=int(np.sum(d>1)),
                largestIslandAboveOne=largest_cluster(mask & (steps>1)))


def main():
    r=receipt("paired",PAIR_SHA)
    results={}
    for stage in STAGES:
        results[stage]={}
        for name in r["screenshots"][stage]:
            im=frame("paired",r,stage,name)
            valid,owner,old,new,display=panels(im)
            wet=valid & ((owner==4)|(owner==5))
            assert wet.sum()>50000
            dry=valid & ((owner==2)|(owner==3))
            assert np.array_equal(old[dry],new[dry]) and np.array_equal(display[:,:,0][dry],display[:,:,1][dry])
            results[stage][name]=dict(original=metrics(wet,old,display[:,:,0]),
                trial=metrics(wet,new,display[:,:,1]),dryControls=int(dry.sum()),
                reducedHdr=int((old[wet]>new[wet]).sum()),increasedHdr=int((new[wet]>old[wet]).sum()))
    output=dict(renderer=r["gl"]["renderer"],pack=PAIR_SHA,stages=results)
    (HERE/"same-frame.json").write_text(json.dumps(output,indent=2)+"\n")
    for s,v in results.items():
        f=v["ingame"]
        print(s, [(k,f[k]["linear"]["p99"],f[k]["linear"]["max"],f[k]["maxDisplayCodes"],f[k]["aboveOne"]) for k in ("original","trial")])


if __name__=="__main__":
    main()
