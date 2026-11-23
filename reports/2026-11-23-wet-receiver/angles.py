"""Read the normal representation at lighting time, independently of the final pass."""
from collections import Counter
import json
import numpy as np
from measure import HERE,PREVIOUS,CAL,STAGES,receipt,frame,read,panels

NORM_SHA="f2cd2deb86523c61a1e1bb3886a0e0b5b3b75dbb944c6d3b5f9c240c9c180734"
SURFACE_SHA="8af2045ff7794264142f86bf46d98fdde9a35c5fd683227b0430e0ea58327600"


def code(panel):
    a=panel.astype("uint32")
    return a[:,:,0]+256*a[:,:,1]+65536*a[:,:,2]


def read_normals(im):
    assert np.array_equal(im[2,8:264],CAL)
    flags=code(im[450:,800:])
    wet=flags>=8
    wet[2,8:264]=False
    assert wet.sum()>10000 and flags[wet].max()<32
    tag=(flags[wet]&7).astype(int)
    vectors={}
    for k,panel in (("interpolated",im[:450,:800]),("decoded",im[:450,800:]),("triangle",im[450:,:800])):
        packed=code(panel)[wet].astype("int32")
        vec=(np.column_stack((packed%4096,packed//4096))-2048)/32768.
        vectors[k]=dict(minXZ=vec.min(axis=0).tolist(),medianXZ=np.median(vec,axis=0).tolist(),maxXZ=vec.max(axis=0).tolist())
    return dict(samples=int(wet.sum()),tags={str(k):int(n) for k,n in Counter(tag).items()},
                saturated=int(np.sum(flags[wet]>=24)),normals=vectors)


def main():
    geo=dict(read(PREVIOUS/"wet-ownership/geometry.json"),middleCamera=[409.48,151,-405.95,143.8,18.])
    normal=receipt("normals-at-two-angles",NORM_SHA,geo)
    surf=receipt("surface",SURFACE_SHA)
    result={}
    for stage in STAGES:
        result[stage]={}
        for k in normal["screenshots"][stage]:
            a=frame("normals-at-two-angles",normal,stage,k)
            row=read_normals(a)
            b=frame("surface",surf,stage,k)
            valid,owner,*_=panels(b)
            t=b[450:,800:,0][valid & (owner==4)]
            row["finalStageTagsAtOriginalCamera"]={str(tag):int(n) for tag,n in Counter(t).items()}
            result[stage][k]=row
        print(stage,result[stage]["ingame"])
    (HERE/"normals.json").write_text(json.dumps(result,indent=2)+"\n")


if __name__=="__main__":
    main()
