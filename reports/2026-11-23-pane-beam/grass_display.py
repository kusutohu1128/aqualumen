"""Compare ordinary F2 grass and wall luminance using fixed physical receiver points."""
import json
import numpy as np
from PIL import Image
from grove_score import extract, reader, HERE

eye=np.array([409.48,152.62,-405.95])
def hidden(p,lo,hi):
    with np.errstate(divide="ignore",invalid="ignore"):
        near=(np.array(lo)-.02-eye)/(p-eye)
        far=(np.array(hi)+.02-eye)/(p-eye)
    return np.maximum(0,np.minimum(near,far).max(2))<np.minimum(1,np.maximum(near,far).min(2))

def run():
    folder=HERE/"grove-edits"
    def marker(s):
        f=folder/(s+"-ingame.png")
        reader.check_record(folder,f)
        return reader.unpack(f,1)[:2]
    l,p=marker("torch"); trunk,q=marker("trunk");cut,t=marker("trunk-cut")
    wall,grass=extract(l,p)
    # Exclude pixels looking THROUGH the pane or the log in ordinary display.
    common=(p==q).all(2)&(p==t).all(2)&~hidden(p,[405,151,-409],[408,153,-408])
    common&=~hidden(p,[406,151,-410],[407,153,-409])
    common&=(l[:,:,0,0]>180)&(cut[:,:,0,0]>180)&(trunk[:,:,2,0]==1)
    masks={}
    for name,m in (("grass",grass),("wall",wall)):
        masks[name+"Lit"]=common&m&(trunk[:,:,0,0]>180)
        masks[name+"Umbra"]=common&m&(trunk[:,:,0,0]<32)
    roles={};stages=("shade","torch","trunk","trunk-cut","extinguished")
    for role in ("control","cells"):
        f=HERE/("grove-"+role+"-ordinary")
        pixels={}
        for s in stages:
            pic=f/(s+"-ingame.png")
            reader.check_record(f,pic)
            pixels[s]=np.asarray(Image.open(pic).convert("RGB"),float)[:-5,::8]@np.array([.2126,.7152,.0722])
        roles[role]={}
        for name,mask in masks.items():
            if not mask.any(): continue
            delta=lambda a,b:float(np.median((pixels[a]-pixels[b])[mask]))
            roles[role][name]=dict(count=int(mask.sum()),level={s:float(np.median(pixels[s][mask])) for s in stages},
                                   lighting=delta("torch","shade"),shadow=delta("trunk","torch"),
                                   afterCut=delta("trunk-cut","trunk"),afterRemovalVsInitial=delta("extinguished","shade"))
    (HERE/"grass-display.json").write_text(json.dumps(roles,indent=2)+"\n")
if __name__=="__main__":run()
