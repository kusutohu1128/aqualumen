"""Find a dry walk from the saved oak to the pasture where cattle last grazed."""
import json
import math
import sys
from collections import deque
from functools import lru_cache
from pathlib import Path
here=Path(__file__).resolve().parent
root=here.parents[2]
sys.path.insert(0,str(root/"reports/2026-11-21-settlement-light/tools"))
from mcnbt import Region,block_at

@lru_cache(None)
def region(x,z):
    p=world/"region"/f"r.{x}.{z}.mca"
    return Region(p) if p.is_file() else None

@lru_cache(None)
def chunk(x,z):
    r=region(x//32,z//32)
    return r.chunk(x,z) if r else None

@lru_cache(None)
def name(x,y,z):
    c=chunk(x//16,z//16)
    return block_at(c,x,y,z)["Name"][10:] if c else "unloaded"

free={"air","cave_air","short_grass","tall_grass","fern","large_fern","poppy","dandelion","blue_orchid","allium","azure_bluet","oxeye_daisy","cornflower","lily_of_the_valley","torch","vine","sugar_cane","brown_mushroom","red_mushroom"}
def stand(x,y,z):
    land=name(x,y-1,z)
    return land not in free|{"water","lava","unloaded"} and not land.endswith(("_leaves","_sapling","_slab","_fence","_wall")) and name(x,y,z) in free and name(x,y+1,z) in free

def nearby_cows(position):
    cows=[]
    for f in (world/"entities").glob("*.mca"):
        r=Region(f)
        for cx,cz in r.present():
            for e in r.chunk(cx,cz).get("Entities",[]):
                if e["id"]=="minecraft:cow":
                    cows.append({"position":e["Pos"],"uuid":e["UUID"]})
    return sorted(cows,key=lambda c:math.dist(position,c["position"]))

def visible(cell, animal):
    eye=(cell[0]+.5,cell[1]+1.62,cell[2]+.5)
    for height in (.55,1.15):
        target=(animal[0],animal[1]+height,animal[2])
        steps=math.ceil(math.dist(eye,target)*8)
        for i in range(1,steps):
            voxel=tuple(math.floor(a+(b-a)*i/steps) for a,b in zip(eye,target))
            if name(*voxel) not in free: return False
    return True

@lru_cache(None)
def column(x,y,z):
    return next((h for h in (y,y+1,y-1) if stand(x,h,z)),None)

def clear_line(a,b):
    dx,dz=b[0]-a[0],b[2]-a[2]
    length=math.hypot(dx,dz)
    if not length or length>6.5 or abs(a[1]-b[1])>1: return False
    steps=math.ceil(length*5)
    y=a[1]
    for k in range(steps+1):
        x,z=a[0]+.5+dx*k/steps,a[2]+.5+dz*k/steps
        for side in (-.33,0.,.33):
            xx,zz=math.floor(x-side*dz/length),math.floor(z+side*dx/length)
            h=column(xx,y,zz)
            if h is None or side and abs(h-y)>0 or h<y and name(xx,y+1,zz) not in free: return False
            if not side: y=h
    return y==b[1]

def build(source_name, world_dir, position, line_of_sight=False, destination=None):
    global world
    world=world_dir
    region.cache_clear();chunk.cache_clear();name.cache_clear();column.cache_clear()
    start=tuple(map(math.floor,position))
    cows=nearby_cows(position) if destination is None else []
    targets=cows[:4] if line_of_sight else cows[:1]
    chosen=None
    trail={start:None};queue=deque([start]);end=None
    while queue:
        p=queue.popleft()
        if p==destination:
            end=p;break
        for animal in targets:
            dist=math.dist((p[0]+.5,p[1],p[2]+.5),animal["position"])
            if dist<4 and (not line_of_sight or dist>=1.8 and visible(p,animal["position"])):
                chosen=animal;end=p;break
        if end: break
        for dx,dz in ((1,0),(0,-1),(-1,0),(0,1)):
            x,z=p[0]+dx,p[2]+dz
            if not 505<=x<=650 or not 320<=z<=455:continue
            h=column(x,p[1],z)
            n=(x,h,z)
            if h is None or n in trail: continue
            if h>p[1] and name(p[0],p[1]+2,p[2]) not in free: continue
            if h<p[1] and name(x,p[1]+1,z) not in free: continue
            trail[n]=p;queue.append(n)
    if not end: raise RuntimeError(f"No dry route to destination ({len(trail)} reachable cells)")
    path=[]
    while end is not None:
        path.append(end);end=trail[end]
    path.reverse()
    pts=[path[0]];i=0
    while i<len(path)-1:
        j=min(len(path)-1,i+14)
        while j>i+1 and not clear_line(path[i],path[j]): j-=1
        pts.append(path[j]);i=j
    return dict(previous=source_name,targetCow=chosen,nearbyCows=cows[:4],cellCount=len(path),waypoints=[[x+.5,y,z+.5] for x,y,z in pts])
if __name__=="__main__":
    source=Path(sys.argv[1]) if len(sys.argv)>1 else root/"reports/2026-11-21-ground-return/walk/ridge-revisit"
    saved=Path(json.loads((source/"identity.json").read_text())["world"])
    position=json.loads((source/"complete.json").read_text())["savedPlayer"]["Pos"]
    data=build(source.name,saved,position,True)
    (Path(sys.argv[2]) if len(sys.argv)>2 else here/"trail.json").write_text(json.dumps(data,indent=2)+"\n")
    print(data["cellCount"],data["waypoints"])
