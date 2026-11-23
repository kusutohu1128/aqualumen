"""Reconstruct the two sides of the measured near-corner discontinuity."""
import json
from functools import lru_cache
from itertools import product
from grid import HERE,captured_grid
from attribute import blockers
from pairs import boxes,basis
from score import FOREST_ANCHOR,FOREST_SOURCES,np
from compare import data

def explain():
    from score import worldgrid
    worldgrid()
    from worldread import World
    words,routes=captured_grid()
    shapes=words&63
    world=World()
    _,(old,p,n)=data("gp-density-placed-hull-meter")
    _,(new,q,n)=data("gp-density-double-box-meter")
    report=json.loads((HERE/"forest.json").read_text())["lights"][2]["twoBoxEdges"]["worst"]
    lamp=2;source=FOREST_SOURCES[lamp]
    @lru_cache(None)
    def info(cell):
        point=np.array(cell)
        route=(int(routes[cell])>>(2*lamp))&3
        label,solid,other=blockers(point,source-FOREST_ANCHOR,shapes,world)
        pair=label=="irregularSolids" and len(solid)<=12 and boxes(solid) is not None
        return route>=2 or route==1 and pair,solid,label
    rows=[]
    for dy in range(2):
        y,x=report["y"]+dy,report["x"]//8
        pos=q[y,x]
        start=pos+[0,.025,0]
        cell=np.floor(start).astype(int)-FOREST_ANCHOR
        accepted,solids,_=info(tuple(cell))
        assert accepted
        frac=start-np.floor(start)
        near=np.where(frac<.5,-1,1)
        edges=[]
        for dx,dz in product((0,near[0]),(0,near[2])):
            if dx==dz==0:continue
            offset=np.array([dx,0,dz]);other=cell+offset
            valid,_,label=info(tuple(other))
            distance=float(np.linalg.norm(np.minimum(frac,1-frac)*(offset!=0)))
            edges.append(dict(offset=offset.tolist(),nearest=distance,eligible=bool(valid),shape=int(shapes[tuple(other)]),label=label))
        u,v=basis((source-pos)[None,:]);u=u[0];v=v[0]
        def open_ray(a,b):
            ray=source-start+a*u+b*v
            for row in solids:
                lo=np.array(row["xyz"])-start
                first=lo/ray;last=(lo+1)/ray
                if max(0.,np.minimum(first,last).max())<min(1.,np.maximum(first,last).min()):return 0
            return 1
        pilot=sum(open_ray(a,b) for a,b in ((.66,0),(-.33,.57156),(-.33,-.57156)))/3.
        estimates=[]
        for diagonal in (False,True):
            possible=[e["nearest"] for e in edges if not e["eligible"] and e["shape"]!=1 and
                      (diagonal or sum(o!=0 for o in e["offset"])==1)]
            t=np.clip((min([.35,*possible])-.06)/.29,0,1)
            weight=float(t*t*(3-2*t))
            estimates.append(dict(weight=weight,value=(1-weight)*pilot+weight*report["ref"][dy]))
        rows.append(dict(position=pos.tolist(),actual=report["new"][dy],reference=report["ref"][dy],
                         pilot=pilot,neighbours=edges,predictions=estimates))
    assert world.unchanged()
    return rows

if __name__=="__main__":
    (HERE/"corner.json").write_text(json.dumps(explain(),indent=2)+"\n")
