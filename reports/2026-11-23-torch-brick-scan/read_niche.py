"""Decode checksummed HDR, emissive and exposure samples from the same frame as the display pixels."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

from niche_pixels import HERE, WOOD, REGIONS

LUMA=np.array([.2126,.7152,.0722])

def stats(y):
    p10,median,p90=np.quantile(y,[.1,.5,.9])
    return dict(p10=float(p10),median=float(median),p90=float(p90),
                contrast=float(p90/p10) if p10>0 else None)

def tone(hdr,exposure):
    linear=hdr*exposure
    return linear/(1+linear.max(axis=-1,keepdims=True))

def decode(path):
    with Image.open(path) as image:
        rgb=np.array(image.convert("RGB"))
    assert rgb.shape==(900,1600,3)
    raw=rgb[-17:-25:-1,16:592].reshape(8,6,12,8,3).astype(int)
    hi,lo,check=np.moveaxis(raw,-1,0)
    assert np.array_equal(hi^lo^165,check), path
    word=(hi*256+lo)/65535.
    assert np.unique(word[:,:,:,6]).size==1
    exposure=float(word[0,0,0,6]*32)
    assert .1<exposure<32 and np.max(word[:,:,:,:6])<1
    return rgb,word,exposure

def summary(path,reference):
    rgb,word,ev=decode(path)
    regions={}
    for i,(name,(x0,y0,x1,y1)) in enumerate(REGIONS.items()):
        hdr=2**(word[:,i,:,:3]*8)-1
        emission=2**(word[:,i,:,3:6]*8)-1
        flag=word[:,i,:,7]
        assert np.max(np.minimum(abs(flag-.25),abs(flag-.75)))<.00002
        assert np.max(emission-hdr)<.001
        ys=y0+((np.arange(8)+.5)*(y1-y0)/8).astype(int)
        xs=x0+((np.arange(12)+.5)*(x1-x0)/12).astype(int)
        screen=rgb[ys[:,None],xs[None,:]].astype(float)/255.
        display=tone(hdr,ev)
        error=np.max(abs(255*(display**(1./2.2)-screen)),axis=-1)
        regions[name]=dict(n=96,emitterFlagSamples=int((flag>.5).sum()),hdr=stats(hdr@LUMA),
           emission=stats(emission@LUMA),screen=stats(screen**2.2@LUMA),
           estimatedAtReferenceExposure=stats(tone(hdr,reference)@LUMA),
           toneReconstructionErrorCodeP95=float(np.quantile(error,.95)),saturatedSamples=int(np.any(screen==1,axis=-1).sum()))
    return dict(exposure=ev,regions=regions)

if __name__=="__main__":
    run=WOOD/"niche-hand-repeats"
    record=json.loads((run/"complete.json").read_text())
    assert record["cleanExit"] and not record["logErrors"] and record["worldZipUnchanged"] and record["previousSaveUnchanged"]
    assert record["labFilesUnchanged"] and record["modsUnchanged"] and not record["benchmarkSentinelPresent"]
    assert record["results"]["completed"]==["same-niche-hand-cycle"] and not record["results"].get("failed")
    files=sorted(run.glob("sample-*-ingame.png"))
    assert len(files)==9
    ev=decode(files[0])[2]
    data={p.name:summary(p,ev) for p in files}
    groups={}
    for phase in ("0-empty","1-held","2-empty"):
        frames=[v for k,v in data.items() if phase in k]
        assert len(frames)==3
        groups[phase]=dict(exposureRange=[min(f["exposure"] for f in frames),max(f["exposure"] for f in frames)],
             regions={name:{key:[min(vals),max(vals)] for key,vals in (
               ("hdrMedian",[f["regions"][name]["hdr"]["median"] for f in frames]),
               ("screenMedian",[f["regions"][name]["screen"]["median"] for f in frames]),
               ("hdrContrast",[f["regions"][name]["hdr"]["contrast"] for f in frames]),
               ("screenContrast",[f["regions"][name]["screen"]["contrast"] for f in frames]),
               ("contrastAtReferenceExposure",[f["regions"][name]["estimatedAtReferenceExposure"]["contrast"] for f in frames]),
               ("emitterFlagSamples",[f["regions"][name]["emitterFlagSamples"] for f in frames]),
               ("reconstructionP95",[f["regions"][name]["toneReconstructionErrorCodeP95"] for f in frames]),
             )} for name in REGIONS})
    (HERE/"niche-radiometry.json").write_text(json.dumps(dict(regions=REGIONS,referenceExposure=ev,groups=groups,frames=data),indent=2)+"\n")
