"""Cross-check extreme polygon-oracle results by directly tracing the disk."""
import json
import numpy as np
from integral import HERE,WORK


def visibility(row,count=131072):
    i=np.arange(count)+.5
    r=np.sqrt(i/count);phi=i*2.399963229728653
    t=row.astype(float)
    delta=t[4,:3]+(r*np.cos(phi))[:,None]*t[5,:3]+(r*np.sin(phi))[:,None]*t[6,:3]
    def hit(lo,hi):
        parallel=abs(delta)<1e-14
        den=np.where(parallel,1.,delta)
        a,b=lo/den,hi/den
        near=np.where(parallel,-np.inf,np.minimum(a,b))
        far=np.where(parallel,np.inf,np.maximum(a,b))
        return (~(parallel&((lo>=0)|(hi<=0))).any(axis=1)
                &(np.maximum(0,near.max(axis=1))<np.minimum(1,far.min(axis=1))))
    return float((~(hit(t[0,:3],t[1,:3])|hit(t[2,:3],t[3,:3]))).mean())


if __name__=="__main__":
    data={}
    for source in ("generic","voxel"):
        if source=="generic":
            records={k:v["groups"]["nearEdges"] for k,v in json.loads((HERE/"polygon.json").read_text()).items()}
            path=WORK/"queries.f32"
        else:
            records=json.loads((HERE/"voxel-cases.json").read_text())["polygon"]
            path=WORK/"voxel.f32"
        rows=np.memmap(path,np.float32,mode="r").reshape(-1,7,4)
        data[source]={vendor:dict(index=r["worst"],old=r["value"],polygon=r["reference"],rays=visibility(rows[r["worst"]]))
                      for vendor,r in records.items()}
    (HERE/"ray-check.json").write_text(json.dumps(dict(samples=131072,groups=data),indent=2)+"\n")
