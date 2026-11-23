"""Plan a walk on the already generated terrain from the village porch to a poppy."""
from functools import lru_cache
from heapq import heappop,heappush
from pathlib import Path
import json
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-21-rain-eaves/fixture"))
from anvil import World

FLOWER=(-896,71,508)
def plan(saved):
    world=World(saved)
    @lru_cache(None)
    def tile(p):
        return (world.block(*p) or "unloaded").removeprefix("minecraft:")
    def free(p):
        name=tile(p)
        return name in {"air","cave_air","poppy","dandelion","fern","tall_grass","short_grass"} or name.startswith("snow[") and "layers=1" in name
    def support(x,y,z):
        return tile((x,y-1,z)).split("[")[0] in {"grass_block","dirt","coarse_dirt","podzol","stone","snow_block","dirt_path","gravel","cobblestone"}
    start=(-901,69,574);end=(-896,72,509)
    assert tile(FLOWER)=="poppy" and support(*start) and support(*end)
    queue=[(0,0,start)];best={start:0};prior={}
    while queue:
        _,cost,p=heappop(queue)
        if p==end:break
        if cost!=best[p]:continue
        x,y,z=p
        for dx,dz in ((0,-1),(1,0),(-1,0),(0,1)):
            for dy in (0,-1,1):
                nx,ny,nz=x+dx,y+dy,z+dz;q=(nx,ny,nz)
                if not -960<nx<-865 or not 490<nz<586:continue
                if not support(*q) or not free(q) or not free((nx,ny+1,nz)):continue
                if dy>0 and not free((x,y+2,z)) or dy<0 and not free((nx,y+1,nz)):continue
                step=cost+1+.5*abs(dy)
                if step<best.get(q,1.e9):
                    best[q]=step;prior[q]=p
                    heappush(queue,(step+abs(nx-end[0])+abs(nz-end[2]),step,q))
                break
    assert end in prior
    cells=[end]
    while cells[-1]!=start:cells.append(prior[cells[-1]])
    cells.reverse()
    keep=[start]
    for a,b,c in zip(cells,cells[1:],cells[2:]):
        if any(b[k]-a[k]!=c[k]-b[k] for k in range(3)) or max(abs(b[k]-keep[-1][k]) for k in (0,2))>=7:keep.append(b)
    result=[[x+.5,y-(.0625 if tile((x,y-1,z))=="dirt_path" else 0.),z+.5] for x,y,z in keep+[end]]
    return dict(flower=FLOWER,cells=len(cells),waypoints=result)
if __name__=="__main__":
    origin=HERE.parent/"2026-11-22-ceiling-return/village/lamp-road/identity.json"
    data=plan(Path(json.loads(origin.read_text())["world"]))
    (HERE/"flower-route.json").write_text(json.dumps(data,indent=2)+"\n")
    print(len(data["waypoints"]),data["waypoints"][-3:])
