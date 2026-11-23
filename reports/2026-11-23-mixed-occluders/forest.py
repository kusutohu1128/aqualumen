"""Compare the new geometry against actual earlier and independent reference visibilities."""
import json
from grid import HERE,PRIOR,WORK
from attribute import registered_frames
from compare import data
from score import FOREST_ANCHOR,FOREST_SOURCES,integral,np,moments,face_from_geometry


def score(label):
    _,old,p,face,normal,cell,grid,registered=registered_frames()
    digest,(new,q,n)=data(label)
    registered &= (face==face_from_geometry(q,np.array([208.5,65.62,355.5]))) & (np.max(abs(p-q),axis=2)<.001)&((n==0)|(face==n))
    stats=[]
    for i,source in enumerate(FOREST_SOURCES):
        a,b=old[:,:,i],new[:,:,i]
        fa,fb=a[:,:,2],b[:,:,2]
        valid=registered&(fa>=64)&(fb>=64)&((fa&12)==0)&((fb&12)==0)
        ref=integral(p,face,valid,source,FOREST_ANCHOR,grid)
        values=[a[:,:,1]/255.,b[:,:,1]/255.]
        partial=(ref>.005)&(ref<.995)
        pair=(fb%4)==3
        report={}
        for name,mask in (("all",partial),("twoBoxes",partial&pair),("remainder",partial&~pair)):
            report[name]=[moments(abs(v-ref)[mask]) for v in values]
        dpos=np.diff(p,axis=0)
        same=(face[:-1]==face[1:])&(abs((normal[:-1]*dpos).sum(axis=2))<.00025)&(np.linalg.norm(dpos,axis=2)<.09)
        for name,edge in (("twoBoxEdges",pair[:-1]!=pair[1:]),("allSoftNeighbours",partial[:-1]|partial[1:])):
            mask=(ref[:-1]>=0)&(ref[1:]>=0)&same&edge&(partial[:-1]|partial[1:])
            err=[abs(np.diff(v,axis=0)-np.diff(ref,axis=0)) for v in values]
            report[name]=dict(errors=[moments(e[mask]) for e in err],
                              worse2Bytes=int((mask&(err[1]-err[0]>2/255.)).sum()),
                              better2Bytes=int((mask&(err[0]-err[1]>2/255.)).sum()))
            if mask.any():
                y,x=np.unravel_index(np.where(mask,err[1]-err[0],-np.inf).argmax(),mask.shape)
                report[name]["worst"]=dict(x=int(x)*8,y=int(y),world=p[y:y+2,x].tolist(),
                        old=values[0][y:y+2,x].tolist(),new=values[1][y:y+2,x].tolist(),
                        methods=(fb[y:y+2,x]%4).tolist(),ref=ref[y:y+2,x].tolist())
        stats.append(report)
    return dict(packSha=digest,lights=stats)

if __name__=="__main__":
    import sys
    label,filename=sys.argv[1:] or ("gp-density-double-box-meter","forest.json")
    (HERE/filename).write_text(json.dumps(score(label),indent=2)+"\n")
