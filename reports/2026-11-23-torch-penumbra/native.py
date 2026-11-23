"""Independent finite segment/voxel reference, including the original placed endpoint rule."""
import argparse
import json
import numpy as np
from pack import HERE, ROOT, WORK
BOXES={0:[],1:[(32,32,32)],2:[(32,32,32),(33,32,32)],3:[(32,32,32)],
       4:[(32,32,32),(33,32,33)],5:[(32,32,32),(33,32,33),(33,33,33)],6:[(32,32,32),(32,33,32)]}
TABLE=WORK/"mixed-angles.txt"
ORACLE=WORK/"mixed-reference.npz"


def prepare():
    rows=np.loadtxt(ROOT/"build/torch-umbra/inputs.txt").tolist()
    for scene in (1,2,4,6):
        for axis in range(3):
            h=(axis+1)%3
            for start in (31.,32.,32.25,33.,34.):
                for end in (31.99,32.,32.55,33.,33.01):
                    for shift in (-.11,0.,.11):
                        a=np.full(3,32.5)
                        b=a.copy()
                        a[axis],b[axis]=start,end
                        a[h]=33.+shift
                        rows.append([scene,*a,*b,.13])
    rows=np.asarray(rows)
    np.savetxt(TABLE,rows,fmt=["%d"]+["%.9f"]*7)
    samples=np.arange(4096)
    phase=samples*np.pi*(3-np.sqrt(5))+.827
    disk=np.sqrt((samples+.5)/len(samples))[:,None]*np.c_[np.cos(phase),np.sin(phase)]
    output=[]
    for scene,*p in rows:
        cells=BOXES[int(scene)]
        if scene==3 or not cells:
            output.append([np.nan if scene==3 else 1.]*2)
            continue
        # OpenGL receives 32-bit world coordinates in the input texture.
        a,b=np.split(np.array(p[:6],dtype=np.float32).astype(float),2)
        l=b-a+[0,.025,0]
        l/=np.linalg.norm(l)
        u=np.cross(l,[0,1,0] if abs(l[1])<.9 else [1,0,0])
        u*=np.float32(p[6])/np.linalg.norm(u)
        rays=b-a+disk[:,:1]*u+disk[:,1:]*np.cross(l,u)
        hit=np.zeros((2,len(samples)),dtype=bool)
        ends=np.floor(a+rays).astype(int)
        for lower in cells:
            c=np.array(lower,float)
            nonzero=abs(rays)>1e-12
            inv=np.divide(1,rays,out=np.zeros_like(rays),where=nonzero)
            t0=(c-a)*inv
            t1=(c+1-a)*inv
            possible=np.all(nonzero|((a>c)&(a<c+1)),axis=1)
            low=np.where(nonzero,np.minimum(t0,t1),-np.inf).max(axis=1)
            high=np.where(nonzero,np.maximum(t0,t1),np.inf).min(axis=1)
            covered=possible & (np.maximum(0.,low)<np.minimum(1.,high))
            hit[0]|=covered & np.any(ends!=c,axis=1)
            hit[1]|=covered
        output.append(1.-hit.mean(axis=1))
    np.savez_compressed(ORACLE,visibility=output)
    print(len(rows),"receivers, 4096 target positions per geometric reference")


def report(tag,hand,variant):
    mode="hand" if hand else "placed"
    prefix=variant+"-" if variant else ""
    f=WORK/(prefix+"mixed-angles-"+tag+"-"+mode+".log")
    src=f.read_text().splitlines()
    assert ("RTX 3080 Ti" if tag=="rtx" else "llvmpipe") in src[0]
    data=np.loadtxt(TABLE)
    outputs=np.loadtxt(src[1:])
    refs=np.load(ORACLE)["visibility"][:,int(hand)]
    # The native fixture submits one draw call per scene, retaining row order within it.
    order=np.argsort(data[:,0],kind="stable")
    data,refs=data[order],refs[order]
    assert outputs.shape==(len(data),5) and np.array_equal(data[:,0],outputs[:,0])
    assert np.isfinite(outputs).all()
    assert ((outputs[:,2:4]>=0)&(outputs[:,2:4]<=1)).all()
    for scene in np.unique(data[:,0]):
        ordinals=outputs[outputs[:,0]==scene,1]
        assert np.array_equal(ordinals,np.arange(len(ordinals)))
    if variant=="joint" and not hand:
        assert (outputs[:,4]==-1).all(), "placed lights unexpectedly entered the new path"
        assert np.array_equal(outputs[:,2],outputs[:,3]), "placed-light visibility differs from preview 12"
    all_stats={}
    for name,mask in [("all",np.ones(len(data),bool)),("analytic",outputs[:,4]>=0),("fallback",outputs[:,4]<0)]:
        partial=mask & (refs>.001) & (refs<.999)
        valid=mask & np.isfinite(refs)
        err=abs(outputs[valid,3]-refs[valid])
        all_stats[name]={"n":int(mask.sum()),"withGeometryReference":int(valid.sum()),"partial":int(partial.sum()),
                         "maxError":float(err.max(initial=0)),"maxChangeFromPreview12":float(np.max(abs(outputs[mask,2]-outputs[mask,3]),initial=0)),
                         "partialReferenceMeanError":float(abs(outputs[partial,2]-refs[partial]).mean()) if partial.any() else None,
                         "partialStudyMeanError":float(abs(outputs[partial,3]-refs[partial]).mean()) if partial.any() else None}
    accepted=(outputs[:,4]>=0)&np.isfinite(refs)
    worst=None
    if accepted.any():
        idx=np.flatnonzero(accepted)[np.argmax(abs(outputs[accepted,3]-refs[accepted]))]
        worst={"input":data[idx].tolist(),"stock":outputs[idx,2],"trial":outputs[idx,3],"reference":refs[idx]}
    result={"renderer":src[0][9:],"mode":mode,"diskRays":4096,"groups":all_stats,
            "worstAccepted":worst}
    (HERE/f"{prefix}mixed-{tag}-{mode}.json").write_text(json.dumps(result,indent=2)+"\n")
    print(tag,mode,all_stats["analytic"],"fallback difference",all_stats["fallback"]["maxChangeFromPreview12"])


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("op",choices=["prepare","rtx","mesa"])
    p.add_argument("--carried",action="store_true")
    p.add_argument("--variant",choices=["","rim","joint"],default="")
    a=p.parse_args()
    if a.op=="prepare": prepare()
    else: report(a.op,a.carried,a.variant)
