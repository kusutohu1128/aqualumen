"""Compare calibrated F2 transmission, across ordinary, mixed and shifted scenes."""
import json
import sys
import ctypes
import numpy as np
from window_room import HERE, PREV, EXISTING, EXTENDED, ROOT
from score import reader, rectangles, WORK

def read(path):
    return json.loads(path.read_text())

def sample(folder, stage):
    image = folder / (stage + "-ingame.png")
    reader.check_record(folder,image)
    lanes, pos, _ = reader.unpack(image,1)
    x,y,z = np.moveaxis(pos,-1,0)
    wall = (abs(z+412)<.0005)&(x>404.04)&(x<409.96)&(y>151.04)&(y<154.96)&(lanes[:,:,2,0]==1)
    camera_x = {"near-west":409.45,"near-east":409.51}.get(stage,409.48)
    wall &= reader.face_from_geometry(pos,np.array([camera_x,152.62,-405.95]))==6
    return lanes, pos, wall

def reference(delta, geom, stage, rgb, p):
    integrate = ctypes.CDLL(str(WORK / "reference.so")).integrate
    integrate.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p]
    points=np.ascontiguousarray(p[::4])
    boxes=rectangles(geom["columns"][stage])
    expected=np.empty_like(points)
    integrate(len(expected),points.ctypes.data,len(boxes),boxes.ctypes.data,1536,expected.ctypes.data)
    errors=abs(rgb[::4].astype(float)-255*expected).max(axis=1)
    tinted=expected.min(axis=1)<.985
    delta.update(referenceReceivers=len(points), tintedReferenceReceivers=int(tinted.sum()),
                 tintedErrorP95Bytes=float(np.quantile(errors[tinted],.95)) if tinted.any() else None,
                 maxReferenceErrorBytes=float(errors.max()))

def compare(role="candidate"):
    folder=HERE/(role+"-rgb")
    geo=read(folder/"geometry.json")
    rows={}
    for s in EXISTING+EXTENDED:
        c, p, w = sample(folder,s)
        b, q, v = sample(PREV/"pane" if s in EXISTING else HERE/"control-extra",s)
        paired=w&v&(p==q).all(axis=2)
        assert paired.sum()>.97*max(w.sum(),v.sum()) and paired.sum()>5000,(s,paired.sum())
        rgb=c[:,:,0][paired]
        diff=abs(rgb.astype(int)-b[:,:,0][paired]).max(axis=1)
        used=c[:,:,3,0][paired]==1
        tinted=rgb.min(axis=1)<251
        r=dict(wall=int(w.sum()),controlWall=int(v.sum()),onlyCandidate=int((w&~v).sum()),
               onlyControl=int((v&~w).sum()),paired=int(len(diff)),fastRaysReceivers=int(used.sum()),
               tintedReceivers=int(tinted.sum()),fastTinted=int((used&tinted).sum()),
               differing=int((diff>0).sum()),moreThanOneByte=int((diff>1).sum()),
               differenceP99Bytes=float(np.quantile(diff,.99)),maximumBytes=int(diff.max()))
        if s not in ("opaque-edge","red-cow"):
            reference(r,geo,s,rgb,p[paired])
        if s in ("opaque-edge","red-cow","split"):
            a,ap,aw=sample(folder,"red-ew")
            overlap = paired&aw&(p==ap).all(axis=2)
            change=c[:,:,0].astype(int)-a[:,:,0].astype(int)
            occluded=overlap&(change.min(axis=2)<-8)
            r.update(darkerThanIntactPane=int(occluded.sum()),fastOnDarker=int((occluded&(c[:,:,3,0]==1)).sum()),
                     brighterThanIntactPane=int((overlap&(change.max(axis=2)>8)).sum()))
        rows[s]=r
    result={"stages":rows,"quantization":"RGB transmission 0–255; flat rear wall matched by exact decoded world position"}
    for run_name,folder in (("candidate", HERE/(role+"-night")),("control", PREV/"timing-sun-at-night")):
        result[run_name]=read(folder/"summary.json")
        for s in ("air","red-ew"):
            reader.check_record(folder,folder/(s+"-ingame.png"))
    (HERE/("comparison.json" if role=="candidate" else role+"-comparison.json")).write_text(json.dumps(result,indent=2)+"\n")
    for s,r in rows.items(): print(s,r['paired'],r['fastTinted'],r['maximumBytes'],r.get('tintedErrorP95Bytes'))
    return result

if __name__=="__main__": compare(*sys.argv[1:])
