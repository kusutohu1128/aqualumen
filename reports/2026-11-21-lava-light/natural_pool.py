"""Find exposed underground lava and a safe camera stance in the actual saved Woodland terrain."""
from pathlib import Path
from collections import defaultdict,deque
from functools import lru_cache
import json,math,sys
here=Path(__file__).resolve().parent
root=here.parents[1]
sys.path.insert(0,str(root/'reports/2026-11-21-rain-eaves/fixture'))
from anvil import World
wpath=Path(json.loads((here.parent/'2026-11-21-leaf-light/play/slope-return/identity.json').read_text())['world'])
w=World(wpath)
@lru_cache(maxsize=400000)
def kind(x,y,z):return (w.block(x,y,z) or 'unavailable').split(':')[-1].split('[')[0]
def clear(x,y,z):return kind(x,y,z) in ('air','cave_air')
source=defaultdict(set)
for cx in range(32,39):
    for cz in range(23,30):
        chunk=w.chunk(cx,cz)
        if not chunk or chunk.get('Status')!='minecraft:full':continue
        for sec in chunk['sections']:
            sy=sec['Y']
            if sy not in (-4,-3,-2,-1):continue
            pal=sec.get('block_states',{}).get('palette',[])
            if not any(v['Name']=='minecraft:lava' for v in pal):continue
            for dy in range(16):
                y=sy*16+dy
                for dx in range(16):
                    for dz in range(16):
                        x,z=cx*16+dx,cz*16+dz
                        if kind(x,y,z)=='lava' and clear(x,y+1,z):source[y].add((x,z))
def groups(cells):
    rest=set(cells)
    while rest:
        start=rest.pop();q=[start];comp={start}
        while q:
            x,z=q.pop()
            for p in ((x-1,z),(x+1,z),(x,z-1),(x,z+1)):
                if p in rest:rest.remove(p);comp.add(p);q.append(p)
        yield comp
stone={'stone','deepslate','tuff','cobbled_deepslate','andesite','granite','diorite','smooth_basalt','calcite','gravel','dirt'}
def sees(eye, target):
    # Conservative: only empty cave cells are traversed. Stop just above the liquid.
    for i in range(1,45):
        p=[math.floor(a+(b-a)*i/45) for a,b in zip(eye,target)]
        if not clear(*p):return False
    return True
best=None
for y,surface in sorted(source.items()):
    for comp in groups(surface):
        if len(comp)<9:continue
        cx=sum(x+.5 for x,z in comp)/len(comp);cz=sum(z+.5 for x,z in comp)/len(comp)
        visible_targets=sorted(comp,key=lambda v:(v[0]+.5-cx)**2+(v[1]+.5-cz)**2)[:25]
        for x,z in sorted(comp):
            for dx,dz in ((-3,0),(3,0),(0,-3),(0,3)):
                a,b=x+dx,z+dz
                for h in (y+2,y+1,y+3):
                    if kind(a,h-1,b) not in stone or not clear(a,h,b) or not clear(a,h+1,b):continue
                    eye=[a+.5,h+1.62,b+.5]
                    visible=[(lx,lz) for lx,lz in visible_targets if sees(eye,[lx+.5,y+1.01,lz+.5])]
                    if len(visible)<5:continue
                    score=(len(visible),min(len(comp),64),-math.hypot(a-565,b-422))
                    if best is None or score>best[0]:
                        best=(score,dict(levelY=y,exposedConnectedCellsInSurvey=len(comp),feet=[a+.5,h,b+.5],support=kind(a,h-1,b),
                            targetCell=[visible[0][0],y,visible[0][1]],visibleTopSamples=len(visible),biome=w.biome(a,h,b),
                            distinctVisibleCells=[[vx,y,vz] for vx,vz in visible]))
                    break
assert best
doc={'seed':308060,'source':'The uninstrumented Minecraft 1.21.1 Woodland cave journey save. Offline Anvil test, no in-game camera was moved.',
     'surveyChunks':[32,38,23,29],'surveySectionY':[-4,-1],'candidate':best[1]}
(here/'natural-pool.json').write_text(json.dumps(doc,indent=2)+'\n')
print({k:v for k,v in best[1].items() if k!='distinctVisibleCells'})
