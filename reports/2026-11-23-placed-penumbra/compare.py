"""Score both releases on the very same adjacent forest pixels, including old seams."""
import numpy as np
from score import (DENSITY,HERE,WORK,FOREST_ANCHOR,FOREST_SOURCES,face_from_geometry,worldgrid,
                   unpack,integral,check_record,moments)
import json
import sys

def data(run):
    path=DENSITY/run/"birch-4-ingame.png"
    return check_record(path.parent,path),unpack(path,2)

def compare(first,second,residuals=False):
    h1,(base,p,n1)=data(first);h2,(trial,q,engineFace)=data(second)
    face=face_from_geometry(p,np.array([208.5,65.62,355.5]))
    nextFace=face_from_geometry(q,np.array([208.5,65.62,355.5]))
    grid=worldgrid()
    axes=np.stack([(face==2*a+2).astype(float)-(face==2*a+1) for a in range(3)],axis=2)
    inside=np.floor(p-.005*axes).astype(int)-FOREST_ANCHOR
    isCube=grid[tuple(np.moveaxis(np.clip(inside,0,63),-1,0))]==1
    faceOk=face==nextFace
    directNormal=(engineFace==face)&(face!=0)
    registered=faceOk&isCube&(face>0)&(np.max(abs(q-p),axis=2)<.001)
    registered&=(engineFace==0)|directNormal
    result=[]
    for i,src in enumerate(FOREST_SOURCES):
        a,b=base[:,:,i],trial[:,:,i]
        flags1,flags2=a[:,:,2],b[:,:,2]
        mask=registered&(flags1>=64)&(flags2>=64)&((flags1&12)==0)&((flags2&12)==0)
        ref=integral(p,face,mask,src,FOREST_ANCHOR,grid)
        usable=(ref>=0)
        values=[a[:,:,0]/255.,a[:,:,1]/255.,b[:,:,1]/255.]
        partial=(ref>.005)&(ref<.995)
        if residuals:
            absolute = abs(values[-1] - ref)
            methods = flags2 % 4
            per_method = {}
            for method, name in enumerate(("ordinaryRayTrace", "certifiedClear", "cuboid")):
                errors = absolute[partial & (methods == method)]
                per_method[name] = dict(count=int(errors.size),
                                        totalAbsoluteError=float(errors.sum()))
            assert sum(row["count"] for row in per_method.values()) == int(partial.sum())
            result.append(per_method)
            continue
        dpos=np.diff(p,axis=0)
        samePlane=abs((axes[:-1]*dpos).sum(axis=2))<.00025
        pair=usable[:-1]&usable[1:]&(face[:-1]==face[1:])&samePlane&(np.linalg.norm(dpos,axis=2)<.09)
        switches=[pair&np.diff(f%4==2,axis=0) for f in (flags1,flags2)]
        union=switches[0]|switches[1]
        ds=[abs(np.diff(v,axis=0)-np.diff(ref,axis=0)) for v in values]
        report=dict(registered=int(mask.sum()),reference=int(usable.sum()),partial=int(partial.sum()),
                    partialErrors=[moments(abs(v-ref)[partial]) for v in values],
                    baselineBytesDifferent=int((mask&(a[:,:,0]!=b[:,:,0])).sum()))
        for tag,sel in zip(("initialMixed","revisedMixed","unionMixed","allPartialAdjacent"),
                           [*switches,union,pair&(partial[:-1]|partial[1:])]):
            report[tag]=dict(pairs=int(sel.sum()),errors=[moments(d[sel]) for d in ds],
                             worseOverTwoBytes=[int((sel&(d-ds[0]>2/255.)).sum()) for d in ds[1:]],
                             maxIncrease=[float(np.max((d-ds[0])[sel],initial=0)) for d in ds[1:]])
        yp,xp=((1003,1440) if i==1 else (1156,824))
        report["witness"]=dict(eligible=bool(pair[yp,xp//8]),ref=ref[yp:yp+2,xp//8].tolist(),
                               values=[v[yp:yp+2,xp//8].tolist() for v in values])
        result.append(report)
    return dict(hashes=[h1,h2],measuredAxisNormals=int((engineFace>0).sum()),agreedAxisNormals=int(directNormal.sum()),lights=result)

if __name__=="__main__":
    result=compare(*sys.argv[1:3],residuals="--residuals" in sys.argv[4:])
    (HERE/(sys.argv[3]+".json")).write_text(json.dumps(result,indent=2)+"\n")
