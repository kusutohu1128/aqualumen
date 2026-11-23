"""Compare registered in-game torch visibility and changes along a five-position sweep."""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-23-placed-penumbra"))
from score import FOREST_ANCHOR, FOREST_SOURCES, check_record, face_from_geometry, integral, unpack, worldgrid

POSES = {"left-far":208.96,"left":208.98,"centre":209.,"right":209.02,"right-far":209.04}


def measure(previous,trial,witness=None):
    grid=worldgrid()
    accumulation={key:[] for key in ("visible","oldError","newError","jump","oldJump","newJump")}
    details={}
    prior=None
    transitions={}
    worst=[]
    sides={}
    for stage,x in POSES.items():
        receipt=[]
        photos=[]
        for folder in ((previous,trial,witness) if witness else (previous,trial)):
            path=folder/(stage+"-ingame.png")
            receipt.append(check_record(folder,path))
            photos.append(unpack(path,2))
            assert json.loads((folder/"geometry.json").read_text())["cameraX"][stage]==x
        (a,p,na),(b,q,nb)=photos[:2]
        eye=np.array([x,65.62,355.5])
        face=face_from_geometry(p,eye)
        normals=np.stack([(face==2*j+2).astype(float)-(face==2*j+1) for j in range(3)],axis=2)
        cell=np.floor(p-.005*normals).astype(int)-FOREST_ANCHOR
        indices=tuple(np.moveaxis(np.clip(cell,0,63),-1,0))
        comparable=((face>0)&(face==face_from_geometry(q,eye))&(np.max(abs(p-q),axis=2)<.001)
                    &((na==0)|(na==face))&((nb==0)|(nb==face))&(grid[indices]==1))
        if witness:
            companion,position,normal=photos[2]
            comparable &= ((face==face_from_geometry(position,eye)) & (np.max(abs(p-position),axis=2)<.001)
                           & ((normal==0)|(normal==face)))
        records=[]
        for i,source in enumerate(FOREST_SOURCES):
            fa,fb=a[:,:,i,2],b[:,:,i,2]
            valid=comparable&(fa>=64)&(fb>=64)&((fa&12)==0)&((fb&12)==0)
            if witness:
                flags=companion[:,:,i,2]
                valid &= (flags>=64)&((flags&12)==0)
            ref=integral(p,face,valid,source,FOREST_ANCHOR,grid)
            partial=(ref>.005)&(ref<.995)
            old=a[:,:,i,1]/255.;new=b[:,:,i,1]/255.
            for key,val in (("visible",new-old),("oldError",old-ref),("newError",new-ref)):
                accumulation[key].append(val[partial])
            if prior:
                c,oldp,f,pr,pa,pb,pm=prior[i]
                # Maintain the same solid face and receiver block along each
                # screen ray. Subtract its physical change in finite-source visibility.
                near=(np.linalg.norm(p-oldp,axis=2)<.09)&(cell==c).all(axis=2)&(face==f)
                soft=(ref>=0)&(pr>=0)&(partial|((pr>.005)&(pr<.995)))
                pairs=near&soft
                ea=(old-pa)-(ref-pr);eb=(new-pb)-(ref-pr)
                samePlane=(face==f)&(abs((normals*(p-oldp)).sum(axis=2))<.0005)
                onPlane=(np.linalg.norm(p-oldp,axis=2)<.09)&samePlane&soft
                sameCell=(cell==c).all(axis=2)
                for side,group in (("same",onPlane&sameCell),("cross",onPlane&~sameCell)):
                    stat=sides.setdefault(side,{"n":0,"oldOver10":0,"newOver10":0,"oldMax":0.,"newMax":0.})
                    stat["n"]+=int(group.sum())
                    if group.any():
                        for series,data in (("old",ea),("new",eb)):
                            stat[series+"Over10"]+=int((group&(abs(data)>.10)).sum())
                            stat[series+"Max"]=max(stat[series+"Max"],float(abs(data[group]).max()))
                method=fb%4
                for fromMethod,toMethod in np.unique(np.column_stack([pm[pairs],method[pairs]]),axis=0):
                    group=pairs&(fromMethod==pm)&(toMethod==method)
                    key=f"{int(fromMethod)}-{int(toMethod)}"
                    row=transitions.setdefault(key,{"pairs":0,"over2":0,"over10Points":0})
                    row["pairs"]+=int(group.sum())
                    row["over2"]+=int((group&(abs(eb)>2/255)).sum())
                    row["over10Points"]+=int((group&(abs(eb)>.10)).sum())
                if pairs.any():
                    y,j=np.unravel_index(np.where(pairs,abs(eb),-1).argmax(),eb.shape)
                    worst.append(dict(stage=stage,lamp=i,screen=[8*int(j),int(y)],oldPosition=oldp[y,j].tolist(),position=p[y,j].tolist(),
                        face=int(face[y,j]),methods=[int(pm[y,j]),int(method[y,j])],priorPack=[float(pa[y,j]),float(old[y,j])],
                        candidate=[float(pb[y,j]),float(new[y,j])],reference=[float(pr[y,j]),float(ref[y,j])],residual=float(eb[y,j])))
                for key,val in (("jump",abs(eb)-abs(ea)),("oldJump",ea),("newJump",eb)):
                    accumulation[key].append(val[pairs])
            records.append((cell,p,face,ref,old,new,fb%4))
        prior=records
        details[stage]={"commonSurfaces":int(comparable.sum()),"x":x}
    metrics={}
    for key,groups in accumulation.items():
        v=np.concatenate(groups)
        assert v.size>0 and np.isfinite(v).all()
        metrics[key]=dict(n=int(v.size),meanAbs=float(abs(v).mean()),maxAbs=float(abs(v).max()),
                          p99Abs=float(np.quantile(abs(v),.99)),positiveOver2=int((v>2./255+1e-9).sum()),
                          negativeOver2=int((v< -2./255-1e-9).sum()),changed=int((abs(v)>1e-9).sum()))
    return dict(packSha=receipt,scenes=details,metrics=metrics,dimensions=[1280,720],
                columnsSampledEvery=8,referenceDiskRays=8192,framesPerPose=1,transitions=transitions,cellBoundaries=sides,
                worstByPoseAndLamp=sorted(worst,key=lambda row:abs(row["residual"]),reverse=True))


if __name__=="__main__":
    comparisons={"--three":("adaptive12","three-way.json"),"--final-three":("cone64","visibility-comparison.json"),
                 "--geometry":("joint","final-comparison.json")}
    if len(sys.argv)==2 and sys.argv[1] in comparisons:
        candidate_name,out=comparisons[sys.argv[1]]
        base=HERE/"birch-two-caps"
        alternate=HERE/("birch-"+candidate_name)
        twentyFour=HERE/"birch-motion24"
        first=measure(base,alternate,twentyFour)
        second=measure(base,twentyFour,alternate)
        assert first["metrics"]["oldError"]==second["metrics"]["oldError"]
        assert first["metrics"]["oldJump"]==second["metrics"]["oldJump"]
        result={name:{k:data[k] for k in ("packSha","metrics","cellBoundaries")}
                for name,data in ((candidate_name,first),("motion24",second))}
    else:
        old,new,out=sys.argv[1:]
        result=measure(HERE/old,HERE/new)
    dest=HERE/out
    if dest.exists():raise FileExistsError(dest)
    dest.write_text(json.dumps(result,indent=2)+"\n")
