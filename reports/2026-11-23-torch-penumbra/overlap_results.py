"""Decode three independent paths on the same frozen room and moving-light controls."""
from hashlib import sha256
import json
import sys
import numpy as np
from PIL import Image
from pack import HERE
from overlap import FOLIAGE, POSES


def frozen(folder,partial=False):
    receipt=json.loads((folder/"complete.json").read_text())
    pre=json.loads((folder/"preflight.json").read_text())
    assert receipt["originalWorldAndConfigUnchanged"] and receipt["packSha256"]==receipt["sourcePackShaNow"]
    if partial:
        assert not receipt["complete"] and receipt["failure"]=="RuntimeError: client exited early rc=143"
        assert set(receipt["stages"])-receipt["screenshots"].keys()=={"mixed-centre","mixed-shift"}
    else:
        assert receipt["complete"] and not receipt["failure"]
    assert pre["labBefore"]==pre["labAfter"] and not pre["foreignObservations"]
    assert set(receipt["stages"])<=(POSES.keys()|FOLIAGE.keys()) and "RTX 3080 Ti" in receipt["gl"]["renderer"]
    values={}
    for stage in receipt["screenshots"]:
        file=folder/(stage+"-ingame.png")
        assert sha256(file.read_bytes()).hexdigest()==receipt["screenshots"][stage]["ingame"]
        with Image.open(file) as im:
            first=np.array(im.convert("RGB"))[16:64,16:144]
        assert first.shape==(48,128,3)
        trial,disk=np.split(first,2)
        assert np.all(disk[:,:,2]==173), (stage,np.unique(disk[:,:,2],return_counts=True))
        assert np.isin(trial[:,:,2],(0,255)).all()
        values[stage]={"stock":trial[:,:,0]/255.,"study":trial[:,:,1]/255.,
                       "visible":trial[:,:,2]==255,"disk":disk[:,:,:2].mean(axis=2)/255.,
                       "spread":abs(disk[:,:,0].astype(float)-disk[:,:,1])/255.}
    return receipt,values


def describe(x):
    return {"mean":float(x.mean()),"p95":float(np.quantile(x,.95)),"max":float(x.max())}


def region(data,name,mask):
    obs=data[name]
    result={"points":int(mask.sum())}
    if mask.any():
        for key in ("stock","study"):
            result[key]=describe(abs(obs[key][mask]-obs["disk"][mask]))
        result["referencePhaseDifference"]=describe(obs["spread"][mask])
    return result


def main():
    folder=HERE/sys.argv[1]
    partial=folder.name=="penumbra-overlap"
    receipt,data=frozen(folder,partial)
    details={}
    for stage in data:
        q=data[stage]
        details[stage]=region(data,stage,q["visible"]&(q["disk"]>.02)&(q["disk"]<.98))
    blends={}
    for label,column,animal in [("mixed-west","column","cow-west"),("mixed-centre","column","cow-centre"),
                                 ("mixed-shift","column-shift","cow-shift"),("column-leaf","column","leaf")]:
        if label not in data: continue
        a,b,m=[data[n] for n in (column,animal,label)]
        visible=a["visible"]&b["visible"]&m["visible"]
        # Where both objects hide some of the same source area and each hides
        # a different part as well. Enforce independent phase agreement.
        part=visible&(1.-a["disk"]-b["disk"]+m["disk"]>.035)&(a["disk"]-m["disk"]>.035)&(b["disk"]-m["disk"]>.035)&(m["disk"]>.02)
        oak=visible&(a["disk"]>.02)&(a["disk"]<.98)&(b["disk"]>.995)&(abs(m["disk"]-a["disk"])<.012)
        row={"overlappingSilhouettes":region(data,label,part),"uncoveredColumnEdge":region(data,label,oak)}
        if oak.any():
            for k in ("stock","study"):
                row["uncoveredColumnEdge"][k+"Jump"]=describe(abs((m[k]-a[k])-(m["disk"]-a["disk"]))[oak])
        blends[label]=row
    open_region=data["open"]["visible"]&data["open-again"]["visible"]
    assert open_region.any()
    result={"partialRun":partial,"pack":receipt["packSha256"],"driver":receipt["gl"]["renderer"],"size":receipt["size"],
            "worldSamples":[128,24],"independentDiskPhases":2,"raysPerPhase":96,"quantization":"8-bit per channel",
            "observations":details,"comparison":blends,
            "restoredOpenDifference":float(np.max(abs(data["open-again"]["study"]-data["open"]["study"])[open_region]))}
    (HERE/(folder.name+"-results.json")).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(blends,indent=2))


if __name__=="__main__":
    main()
