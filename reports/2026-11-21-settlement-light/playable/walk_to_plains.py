"""Find an outdoor path from the village porch to a verified plains column in the saved client terrain."""
from pathlib import Path
import heapq,json,sys,itertools,re
from functools import lru_cache
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parents[2]/'reports/2026-11-21-rain-eaves/fixture'))
from anvil import World
world=World(Path(json.loads((here/'enter-by-porch/identity.json').read_text())['world']))
rows=json.loads((here.parent/'site/transect.json').read_text())['rows']
destination=next(r for r in reversed(rows) if r['precip']=='rain' and r['matches']==1)
assert (destination['x'],destination['z'])==(-1030,598)
air={'air','cave_air','short_grass','tall_grass','fern','large_fern','poppy','dandelion','cornflower','azure_bluet','sweet_berry_bush','brown_mushroom','red_mushroom','seagrass'}
solid={'grass_block','dirt','coarse_dirt','podzol','dirt_path','stone','andesite','granite','diorite','cobblestone','gravel','sand','ice','packed_ice','blue_ice','snow_block','moss_block','clay'}
@lru_cache(maxsize=None)
def block(x,y,z):
    v=world.block(x,y,z) or 'unknown'
    return v.split('[')[0].split(':')[-1],v
def free(x,y,z):
    b,v=block(x,y,z)
    return b in air or b=='snow' and 'layers=1' in v
def stand(x,y,z):
    return block(x,y-1,z)[0] in solid and free(x,y,z) and free(x,y+1,z)
def actual_height(pos):
    x,y,z=pos
    return y-(1/16 if block(x,y-1,z)[0]=='dirt_path' else 0)
start=(-901,69,574)
target_x,target_z=destination['x'],destination['z']
end=next((target_x,y,target_z) for y in range(90,50,-1) if stand(target_x,y,target_z))
def heuristic(p):
    return abs(p[0]-end[0])+abs(p[2]-end[2])+abs(actual_height(p)-actual_height(end))*.2
assert stand(*start),(start,block(*start))
heap=[(heuristic(start),0,start)]
parent={start:None};cost={start:0}
while heap:
    _,d,a=heapq.heappop(heap)
    if d>cost[a]:continue
    if a==end:break
    x,y,z=a
    for dx,dz in ((-1,0),(0,1),(1,0),(0,-1)):
        for dy in (0,1,-1):
            b=x+dx,y+dy,z+dz
            if not (-1042<=b[0]<=-892 and 536<=b[2]<=634) or not stand(*b):continue
            if dy>0 and not free(x,y+2,z):continue
            if dy<0 and not free(b[0],y+1,b[2]):continue
            c=d+1+abs(dy)*.35+(1.1 if block(b[0],b[1]-1,b[2])[0] in ('ice','packed_ice','blue_ice') else 0)
            if c<cost.get(b,float('inf')):
                cost[b]=c;parent[b]=a;heapq.heappush(heap,(c+heuristic(b),c,b))
            break
assert end in parent
cells=[end]
while cells[-1]!=start:cells.append(parent[cells[-1]])
cells.reverse()
def delta(a,b):return tuple(v-u for u,v in zip(a,b))
def vec(p):return [p[0]+.5,actual_height(p),p[2]+.5]
keep=[cells[0]]
for prev,cur,nex in zip(cells,cells[1:],cells[2:]):
    if delta(prev,cur)!=delta(cur,nex) or max(abs(cur[i]-keep[-1][i]) for i in (0,2))>=6:
        keep.append(cur)
keep.append(cells[-1])
doc=dict(start=vec(start),end=vec(end),cells=len(cells),waypoints=list(map(vec,keep)),goalBiomeOnServer=destination,source='Existing ordinary 1.21.1 client save. Surface path excludes water, leaves, fences and crops. Rising and descending steps check head clearance on both sides.')
(here/'plains-route.json').write_text(json.dumps(doc,indent=2)+'\n')
print(len(cells),len(keep),vec(end))
