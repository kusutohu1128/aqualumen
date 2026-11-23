"""Compare ordinary F2 pixels where only the lamp-to-wall path traverses a pane."""
import json
import numpy as np
from PIL import Image
from score import HERE, reader, rectangles

eye=np.array([409.48,152.62,-405.95])
geo=json.loads((HERE/"pane/geometry.json").read_text())
def see_pane(points,boxes):
    # Pad the silhouette to exclude screen filtering and the glass texture border.
    hits=np.zeros(points.shape[:2],bool)
    for x,y,z,X,Y,Z,_ in boxes:
        ray=points-eye
        with np.errstate(divide="ignore",invalid="ignore"):
            a=(np.array([x,y,z])-.03-eye)/ray
            b=(np.array([X,Y,Z])+.03-eye)/ray
        hits|=np.maximum(0,np.minimum(a,b).max(axis=2))<np.minimum(1,np.maximum(a,b).min(axis=2))
    return hits
def normal(stage):
    f=HERE/"appearance"/(stage+"-ingame.png")
    reader.check_record(f.parent,f)
    return np.array(Image.open(f).convert("RGB"),int)[:-5,::8]
base=normal("air")
results={}
compare_masks={}
for stage in ("red-ew","blue-ew","two-colours","thick"):
    meter=HERE/"pane"/(stage+"-ingame.png")
    reader.check_record(meter.parent,meter)
    lamps,p,_=reader.unpack(meter,1)
    wall=(reader.face_from_geometry(p,eye)==6)&(abs(p[:,:,2]+412)<.0005)
    wall&=(p[:,:,0]>404.05)&(p[:,:,0]<409.95)&(p[:,:,1]>151.05)&(p[:,:,1]<154.95)&(lamps[:,:,2,0]==1)
    wall&=~see_pane(p,rectangles(geo["columns"][stage]))
    tr=lamps[:,:,0].astype(float)
    target=wall & (tr.min(axis=2)<211)
    clear=wall & (tr.min(axis=2)==255)
    if stage in ("red-ew","blue-ew"):
        compare_masks[stage]=(target,clear)
    ordinary=normal(stage)
    result={}
    for key,mask in (("tinted",target),("unattenuated",clear)):
        if not mask.any():continue
        delta=ordinary[mask]-base[mask]
        result[key]=dict(count=int(mask.sum()),airMedian=np.median(base[mask],axis=0).tolist(),
                         paneMedian=np.median(ordinary[mask],axis=0).tolist(),
                         pairedMedianDelta=np.median(delta,axis=0).tolist(),
                         redMinusBlueMedianDelta=float(np.median(delta[:,0]-delta[:,2])))
    results[stage]=result
red=normal("red-ew")
blue=normal("blue-ew")
paired={}
for index,name in enumerate(("tinted","unattenuated")):
    common=compare_masks["red-ew"][index] & compare_masks["blue-ew"][index]
    delta=red[common]-blue[common]
    paired[name]=dict(count=int(common.sum()),medianRedPaneMinusBluePaneRGB=np.median(delta,axis=0).tolist(),
                      medianRedMinusBlueChannelDifference=float(np.median(delta[:,0]-delta[:,2])))
results["redVsBlueSameWall"]=paired
(HERE/"display.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps(results,ensure_ascii=False))
