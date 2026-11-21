"""Find a walkable route from open sky to a natural rock roof, with a sightline back out."""
from collections import deque
import json
import math
import sys
from pathlib import Path

import numpy as np

here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/"2026-11-21-rain-eaves/fixture"))
from anvil import World


def main():
    record=json.loads((here/"generated.json").read_text())
    world=World(record["world"])
    cx0,cz0=record["chunkMin"]
    cx1,cz1=record["chunkMax"]
    x0,z0,y0=cx0*16,cz0*16,32
    shape=(128,(cz1-cz0+1)*16,(cx1-cx0+1)*16)
    clear=np.zeros(shape,dtype=bool)
    ground=clear.copy();roof=clear.copy()
    sky=np.zeros(shape,dtype=np.uint8)
    top=np.zeros(shape[1:],dtype=int)
    passable={"air","cave_air","short_grass","tall_grass","fern","large_fern","poppy","dandelion",
              "red_mushroom","brown_mushroom","lily_of_the_valley"}
    rock={"stone","granite","andesite","diorite","tuff","deepslate","dripstone_block","coal_ore","iron_ore","copper_ore"}
    stable=rock|{"dirt","grass_block","coarse_dirt","gravel","podzol","moss_block","clay","rooted_dirt"}
    ids=np.arange(4096)
    for cx in range(cx0,cx1+1):
        for cz in range(cz0,cz1+1):
            x,z=cx*16-x0,cz*16-z0
            chunk=world.chunk(cx,cz)
            assert chunk["Status"]=="minecraft:full"
            for dz in range(16):
                for dx in range(16):top[z+dz,x+dx]=world.height(cx*16+dx,cz*16+dz)-y0
            for sec in chunk["sections"]:
                y=sec["Y"]*16-y0
                if y<0 or y+16>shape[0] or "block_states" not in sec:continue
                bs=sec["block_states"]
                names=[b["Name"].removeprefix("minecraft:") for b in bs["palette"]]
                palette=np.zeros(4096,dtype=int)
                if len(names)>1:
                    bits=max(4,(len(names)-1).bit_length());per=64//bits
                    words=np.asarray(bs["data"],dtype=np.int64).view(np.uint64)
                    palette=((words[ids//per]>>((ids%per)*bits).astype(np.uint64))&((1<<bits)-1)).astype(int)
                section=np.s_[y:y+16,z:z+16,x:x+16]
                for mask,types in ((clear,passable),(ground,stable),(roof,rock|{"dirt","grass_block"})):
                    mask[section]=np.asarray([name in types for name in names])[palette].reshape(16,16,16)
                if "SkyLight" in sec:
                    nib=np.frombuffer(sec["SkyLight"],dtype=np.uint8)
                    sky[section]=((nib[ids//2]>>((ids%2)*4).astype(np.uint8))&15).reshape(16,16,16)
    stand=clear & np.roll(clear,-1,axis=0) & np.roll(ground,1,axis=0)
    stand[:2]=False;stand[-4:]=False
    stand[:,:3]=False;stand[:,-3:]=False;stand[:,:,:3]=False;stand[:,:,-3:]=False
    open_air=stand & (np.arange(shape[0])[:,None,None]>=top[None,:,:])
    queue=deque(tuple(map(int,p)) for p in np.argwhere(open_air))
    back={p:None for p in queue}
    distance={p:0 for p in queue}
    candidates=[]
    while queue:
        p=queue.popleft();y,z,x=p;steps=distance[p]
        if 8<=steps<=24 and sky[y+1,z,x]<=7 and roof[y+2:y+8,z,x].any():
            candidates.append(p)
        if steps>=24:continue
        for dz,dx in ((0,1),(0,-1),(1,0),(-1,0)):
            for dy in (0,1,-1):
                n=(y+dy,z+dz,x+dx)
                if not stand[n] or n in back:continue
                if dy==1 and not clear[y+2,z,x]:continue
                if dy==-1 and not clear[y+1,z+dz,x+dx]:continue
                back[n]=p;distance[n]=steps+1;queue.append(n)

    def xyz(p):
        y,z,x=p
        return [x+x0,y+y0,z+z0]

    def clear_sky_rays(p,q):
        y,z,x=p
        heading=math.atan2(q[1]-z,q[2]-x)
        seen=0
        for yaw in (-.5,-.25,0,.25,.5):
            for pitch in (.03,.14,.27,.42,.65):
                for d in np.arange(.3,35,.4):
                    a=int(y+1.62+d*math.sin(pitch))
                    b=int(z+.5+d*math.cos(pitch)*math.sin(heading+yaw))
                    c=int(x+.5+d*math.cos(pitch)*math.cos(heading+yaw))
                    if not (0<=a<shape[0] and 0<=b<shape[1] and 0<=c<shape[2]) or not clear[a,b,c]:break
                    if a>=top[b,c]:
                        seen+=1;break
        return seen

    options=[]
    for p in sorted(candidates,key=lambda p:(sky[p[0]+1,p[1],p[2]],abs(distance[p]-12),p))[:1500]:
        path=[p]
        while back[path[-1]] is not None:path.append(back[path[-1]])
        rays=clear_sky_rays(p,path[-1])
        if rays:
            inside=int(sky[p[0]+1,p[1],p[2]])
            bx,by,bz=xyz(p)
            if inside>5 or world.block(bx,by-1,bz).split(":")[-1] not in rock:continue
            if world.light(bx,by+1,bz) != inside:continue
            score=rays*(15-inside)/(1+.02*abs(len(path)-13))
            options.append((score,rays,path[::-1],inside))
    if not options:raise RuntimeError(f"No sun-facing cave mouth among {len(candidates)} cells")
    _,rays,path,inside=max(options)
    endpoints=[xyz(path[0]),xyz(path[-1])]
    out=dict(seed=record["seed"],endpoints=endpoints,waypoints=[xyz(p) for p in path],skyLightInside=inside,
             skyLightOutside=world.light(*endpoints[0]),biomes=[world.biome(*p) for p in endpoints],
             skyRaysAtOpening=rays,skyRaysTested=25,screenedStandableCells=len(back),darkCells=len(candidates),
             floor=[world.block(p[0],p[1]-1,p[2]) for p in endpoints])
    (here/"route.json").write_text(json.dumps(out,indent=2)+"\n")
    print(out)


if __name__=="__main__":
    main()
