"""Check the torch, trunk, dirt, and animal after editing the private test world."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-23-mixed-occluders"))
from room_score import score
from score import unpack,np

if __name__=="__main__":
    label,name=sys.argv[1:]
    folder=HERE/label
    data=score(folder)
    lamps,_,_=unpack(folder/"extinguished-ingame.png",1)
    data["evaluationsAfterRemoval"]=int((lamps[:,:,0,2]>=64).sum())
    assert data["evaluationsAfterRemoval"]==0
    if "trunk-cut" in data:
        views=[unpack(folder/(s+"-ingame.png"),1) for s in ("cut-step","trunk-cut","replanted")]
        lights=[tex[:,:,0] for tex,_,_ in views]
        _,p,_=views[0]
        wall=(abs(p[:,:,2]+412)<.006)&(p[:,:,1]>151)&(p[:,:,1]<155)&(p[:,:,0]>404)&(p[:,:,0]<410)
        for (tex,q,_),light in zip(views,lights,strict=True):
            wall&=(np.max(abs(p-q),axis=2)<.001)&(light[:,:,2]>=64)
        affected=wall&(lights[0][:,:,1]<251)&(lights[1][:,:,1]==255)
        restored=affected&(lights[0][:,:,1]==lights[2][:,:,1])
        data["trunkEdit"]=dict(fullyLitAfterCut=int(affected.sum()),restoredAfterReplant=int(restored.sum()))
    (HERE/name).write_text(json.dumps(data,indent=2)+"\n")
