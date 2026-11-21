"""Scout connected, two-block-high walking cells in the existing natural Lab TEST terrain."""
import json
import sys
from collections import deque
from functools import lru_cache
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "reports/2026-11-20-local-light/forest-tools"))
from worldread import World

world = World()
start = (208,64,355)
air = {"air","cave_air","void_air","short_grass","tall_grass","fern","large_fern",
       "dandelion","poppy","cornflower","azure_bluet","oxeye_daisy","lily_of_the_valley"}
ground = {"stone","deepslate","andesite","granite","diorite","gravel","sand","tuff","clay",
          "dirt","grass_block","coarse_dirt","podzol","moss_block","calcite","dripstone_block"}
@lru_cache(maxsize=600000)
def block(x,y,z):
    name=world.name(x,y,z)
    return name.split(":")[-1] if name else None
def walk(p):
    x,y,z=p
    floor=block(x,y-1,z)
    if y==62 and block(x,y,z)=="water" and block(x,y+1,z) in air:
        return True  # optional surface swim segment between banks
    return (floor in ground or (floor and floor.endswith("_ore"))) and block(x,y,z) in air and block(x,y+1,z) in air
def roof(p):
    x,y,z=p
    return sum(block(x,y+h,z) in ground for h in range(2,20))
def shore(p):
    x,y,z=p
    return 61<=y<=65 and any(block(x+dx,62,z+dz)=="water" for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)))
def explore(origin, upper, allow_swim=True):
    paths={origin:None};depth={origin:0};queue=deque([origin])
    while queue:
        p=queue.popleft()
        if depth[p]>=upper: continue
        x,y,z=p
        for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
            nx,nz=x+dx,z+dz
            if abs(nx-start[0])>155 or abs(nz-start[2])>155:continue
            for dy in (0,-1,1):
                dest=(nx,y+dy,nz)
                if not walk(dest) or (not allow_swim and block(*dest)=="water"):continue
                if (dy==1 and block(x,y+2,z) not in air) or (dy==-1 and block(nx,y+1,nz) not in air):continue
                if dest not in paths:
                    paths[dest]=p;depth[dest]=depth[p]+1;queue.append(dest)
                break
    return paths,depth
def route(paths,end):
    result=[]
    while end is not None:
        result.append(end);end=paths[end]
    return result[::-1]
def discover():
    assert walk(start)
    paths,dist=explore(start,280)
    print("reachable",len(paths),"range",[(min(p[i] for p in paths),max(p[i] for p in paths)) for i in range(3)],flush=True)
    caves=[p for p in paths if block(*p)!="water" and p[1]<63 and roof(p)>=5 and dist[p]>15]
    assert caves,"no roofed underground destination in the bounded search"
    cave=min(caves,key=lambda p:p[1]+0.10*dist[p]-0.3*roof(p))
    cpath,cdist=explore(cave,220)
    banks=[p for p in cpath if block(*p)!="water" and shore(p)]
    assert banks,"no connected riverbank"
    bank=min(banks,key=lambda p:cdist[p])
    out=[route(paths,cave),route(cpath,bank)]
    assert all(walk(p) for line in out for p in line) and world.unchanged()
    result=dict(type="read-only route through saved Minecraft blocks; passability and stone cover only, no live gameplay yet",
                marker=world.marker, start=start,cave=cave,bank=bank,caveOverheadStoneCells=roof(cave),
                graphReachable=len(paths),pathLengths=[len(r)-1 for r in out],
                steps=out,waterLevel=62,swimmingCells=[sum(block(*p)=="water" for p in r) for r in out])
    target=Path(__file__).with_name("route.json")
    with target.open("x") as f: json.dump(result,f,indent=1);f.write("\n")
    print(cave,bank,result["pathLengths"],len(paths))

def land_route():
    survey=json.loads(Path(__file__).with_name("route.json").read_text())
    cave=tuple(survey["cave"])
    paths,depth=explore(cave,120,allow_swim=False)
    candidates=[]
    for p,d in depth.items():
        if not 12<=d<=82: continue
        x,y,z=p
        logs=[(x+dx,y,z+dz) for dx,dz in ((1,0),(-1,0),(0,-1),(0,1))]
        for tree in logs:
            tx,ty,tz=tree
            log=block(*tree)
            if log not in ("birch_log","oak_log","spruce_log","dark_oak_log"):continue
            if not all(block(tx,ty+h,tz)==log for h in (1,2,3)):continue
            leaves=0
            for dx in range(-2,3):
                for dz in range(-2,3):
                    for dy in range(3,9):
                        st=world.state(tx+dx,ty+dy,tz+dz)
                        if st and st["Name"].endswith("_leaves") and st.get("Properties",{}).get("persistent")=="false":leaves+=1
            if leaves>=10:
                score=abs(d-38)-min(leaves,65)*0.1
                candidates.append((score,p,tree,leaves))
    assert candidates,"no confirmed natural tree reachable on foot"
    _,forest,tree,leaves=min(candidates)
    bank=min((p for p in paths if shore(p)),key=lambda p:depth[p])
    legs=[route(paths,forest)[::-1],route(paths,bank)]
    assert world.unchanged() and all(walk(p) and block(*p)!="water" for leg in legs for p in leg)
    result=dict(type="read-only terrain survey; no actual traversal or illumination measurements",
                marker=world.marker,start=forest,tree=tree,treeSpecies=block(*tree),generatedLeaves=leaves,
                cave=cave,bank=bank,caveOverheadStoneCells=roof(cave),graphReachable=len(paths),
                pathLengths=[len(l)-1 for l in legs],swimmingCells=[0,0],steps=legs)
    out=Path(__file__).with_name("forest-to-bank.json")
    with out.open("x") as f:json.dump(result,f,indent=1);f.write("\n")
    print(forest,cave,bank,result["pathLengths"],leaves)
if __name__=="__main__":
    land_route() if "--land" in sys.argv else discover()
