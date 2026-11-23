"""Score the proposed per-point switch, including its boundaries on the actual wall/ground."""
import ctypes as ct
import json
import subprocess
from grid import HERE, WORK
from attribute import registered_frames
from score import FOREST_ANCHOR, FOREST_SOURCES, integral, moments, np


def apply(rows, p, origins, cell, src, mask, func):
    method = np.full(mask.shape,-1,np.int8)
    estimate = np.full(mask.shape,-1.)
    block_count = np.zeros(mask.shape,np.int32)
    for row in rows:
        same = mask & (cell==(np.array(row["cell"])-FOREST_ANCHOR)).all(axis=2)
        indices = np.flatnonzero(same)
        if not indices.size:
            continue
        pos=np.ascontiguousarray(p.reshape(-1,3)[indices])
        start=np.ascontiguousarray(origins.reshape(-1,3)[indices])
        cubes=np.array([b["xyz"] for b in row["solid"]],np.int32)
        touched=np.empty(len(pos),np.int32)
        rect=np.empty_like(touched)
        vis=np.empty(len(pos),np.float64)
        ptr=lambda arr: arr.ctypes.data
        func(len(pos),ptr(pos),ptr(start),ptr(src),len(cubes),ptr(cubes),ptr(touched),ptr(rect),ptr(vis))
        # A path with no intersection is also certified clear.
        method.flat[indices]=(touched==0)|(rect!=0)
        estimate.flat[indices]=vis
        block_count.flat[indices]=touched
    return method,estimate,block_count


def score():
    subprocess.run(["c++","-std=c++17","-O3","-shared","-fPIC",str(HERE/"footprint.cpp"),
                    "-o",str(WORK/"footprint.so")],check=True)
    func=ct.CDLL(str(WORK/"footprint.so")).classify
    func.argtypes=[ct.c_int]+[ct.c_void_p]*3+[ct.c_int]+[ct.c_void_p]*4
    func.restype=None
    rows=json.loads((HERE/"forest-census.json").read_text())["rows"]
    base,trial,p,face,axis,cell,grid,registered=registered_frames()
    origins=p+.025*axis
    out=[]
    for i,src in enumerate(FOREST_SOURCES):
        a,b=base[:,:,i,2],trial[:,:,i,2]
        mask=registered & (a>=64)&(b>=64)&((a&12)==0)&((b&12)==0)&((b%4)==0)
        ref=integral(p,face,mask,src,FOREST_ANCHOR,grid)
        old=trial[:,:,i,1]/255.
        method,analytic,hits=apply([r for r in rows if r["source"]==i and r["reason"]=="irregularSolids"],
                                   p,origins,cell,src,ref>=0,func)
        new=np.where(method==1,analytic,old)
        partial=(ref>.005)&(ref<.995)
        report={}
        for name,route in (("oneCuboid",1),("multiple",0)):
            take=partial&(method==route)
            report[name]=dict(n=int(take.sum()),oldSSE=float(np.square(old[take]-ref[take]).sum()),
                              oldError=moments(abs(old-ref)[take]),trialError=moments(abs(new-ref)[take]))
        # The original capture has consecutive rows, with one sampled column
        # out of every eight. Only adjacent rows on the same face are used.
        dpos=np.diff(p,axis=0)
        same=(face[:-1]==face[1:])&(abs((axis[:-1]*dpos).sum(axis=2))<.00025)&(np.linalg.norm(dpos,axis=2)<.09)
        edge=(method[:-1]>=0)&(method[1:]>=0)&(method[:-1]!=method[1:])&same&(partial[:-1]|partial[1:])
        err=[abs(np.diff(t,axis=0)-np.diff(ref,axis=0)) for t in (old,new)]
        report["switchPairs"]=dict(n=int(edge.sum()),excess2Bytes=[int((edge&(e>2/255.)).sum()) for e in err],
                                   worseThanOld2Bytes=int((edge&(err[1]-err[0]>2/255.)).sum()),
                                   differenceErrors=[moments(e[edge]) for e in err])
        if edge.any():
            y,x=np.unravel_index(np.where(edge,err[1]-err[0],-np.inf).argmax(),edge.shape)
            report["worstPair"]=dict(screen=[int(x)*8,int(y)],world=p[y:y+2,x].tolist(),
                                     method=method[y:y+2,x].tolist(),intersectedVoxels=hits[y:y+2,x].tolist(),
                                     ref=ref[y:y+2,x].tolist(),old=old[y:y+2,x].tolist(),trial=new[y:y+2,x].tolist())
        out.append(report)
    assert sum(s[k]["n"] for s in out for k in ("oneCuboid","multiple"))==11174
    return out


if __name__ == "__main__":
    (HERE/"per-point-switch.json").write_text(json.dumps(score(),indent=2)+"\n")
