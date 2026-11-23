"""Compare a placed torch's visibility on the reproduced white wall to direct rays."""
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-23-placed-penumbra"))
from score import ROOM_ANCHOR,ROOM_SOURCE,check_record,integral


def frame(folder,name):
    file=folder/(name+"-ingame.png")
    digest=check_record(folder,file)
    with Image.open(file) as image:
        rgb=np.asarray(image.convert("RGB"))
    assert rgb.shape==(721,1281,3)
    assert np.array_equal(rgb[-3,:256],np.repeat(np.arange(256)[:,None],3,axis=1))
    lane=rgb[:-5,:1280].reshape(716,160,8,3)
    assert (lane[:,:,7,1]==183).all() and (lane[:,:,7,2]==1).all()
    pos=ROOM_ANCHOR+(lane[:,:,4:7].astype(np.int32)@np.array([1,256,65536]))/65536.
    return digest,pos,lane[:,:,0]


def compare(old,new):
    result={}
    grid=np.zeros((64,64,64),np.uint8)
    for block in [(403,151,-411),(403,152,-411),(404,151,-410),(405,150,-408)]:
        grid[tuple(np.array(block)-ROOM_ANCHOR)]=1
    for stage in ("minus","aligned","plus"):
        a,p,v=frame(old,stage)
        b,q,w=frame(new,stage)
        pos=p[:,:,0]
        wall=(p[:,:,2]==-414)&(pos>=397)&(pos<403)&(p[:,:,1]>=148)&(p[:,:,1]<154)
        ok=wall&(np.max(abs(p-q),axis=2)<.00015)&(v[:,:,2]>=64)&(w[:,:,2]>=64)&(((v[:,:,2]|w[:,:,2])&12)==0)
        face=np.full(ok.shape,6,np.uint8)
        ref=integral(p,face,ok,ROOM_SOURCE[0],ROOM_ANCHOR,grid)
        soft=ok&(ref>.005)&(ref<.995)
        assert soft.sum()>20
        oldEv=v[:,:,1]/255.;newEv=w[:,:,1]/255.
        diff=abs(oldEv-ref)-abs(newEv-ref)
        data={}
        for label,mask in (("wall",soft),("axis",soft&(np.indices(ok.shape)[1]==80))):
            if not mask.any():continue
            y,x=np.unravel_index(np.argmax(np.where(mask,diff,-np.inf)),ok.shape)
            data[label]=dict(n=int(mask.sum()),improved=int((mask&(diff>2/255)).sum()),worse=int((mask&(diff< -2/255)).sum()),
                maxChange=float(abs(newEv-oldEv)[mask].max()),
                meanOld=float(abs(oldEv-ref)[mask].mean()),meanNew=float(abs(newEv-ref)[mask].mean()),
                **{"bestGain":dict(x=int(x*8),y=int(y),position=p[y,x].tolist(),old=float(oldEv[y,x]),
                new=float(newEv[y,x]),reference=float(ref[y,x]),methods=[int(v[y,x,2]%4),int(w[y,x,2]%4)])})
        data["aim"] = dict(world=p[360,80].tolist(),old=v[360,80].tolist(),new=w[360,80].tolist(),reference=float(ref[360,80]))
        result[stage]=data
    return dict(packs=[a,b],source=ROOM_SOURCE[0].tolist(),frames=result)


if __name__=="__main__":
    result=compare(HERE/"corner-previous",HERE/"corner-contours")
    (HERE/"corner.json").write_text(json.dumps(result,indent=2)+"\n")
