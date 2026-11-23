"""Create each orientation by placing neighbouring panes in a private Minecraft room."""
from pathlib import Path
import sys
from packs import HERE,ROOT,build
sys.path.insert(0,str(HERE.parent/"2026-11-22-gpu-profile"))
import run as guarded

C=(406,-410)
def line(dx,dz):
    return {(C[0]+i*dx,C[1]+i*dz):"red_stained_glass_pane" for i in (-1,0,1)}
ROW=line(1,0)
COL=line(0,1)
LAYOUT={"air":{},"post":{C:"red_stained_glass_pane"},"red-ew":ROW,
        "blue-ew":{p:"blue_stained_glass_pane" for p in ROW},"red-ns":COL,
        "corner":{C:ROW[C],(405,-410):ROW[C],(406,-409):ROW[C]},
        "two-colours":dict(ROW)|{(x,-409):"blue_stained_glass_pane" for x in (405,406,407)},
        "thick":{p:"red_stained_glass" for p in ROW},"clear-again":{}}
DIRECTIONS={"west":(-1,0),"east":(1,0),"north":(0,-1),"south":(0,1)}
def state(layout,x,z):
    name=layout[x,z]
    if not name.endswith("_pane"): return name
    arms=[f"{side}={str((x+dx,z+dz) in layout).lower()}" for side,(dx,dz) in DIRECTIONS.items()]
    return name+"["+",".join(arms)+"]"

class Room:
    def __init__(self,base):
        self.base=base
        for name in LAYOUT:base.STAGE_TABLE[name]=(False,False,None,"white_concrete",True,18000)
    def __getattr__(self,key):return getattr(self.base,key)
    def self_test(self,names):assert names and all(n in LAYOUT for n in names)
    def geometry(self,names):
        return dict(self.base.geometry(names),source=[405.5,151.64,-407.5],columns={
            name:[[x,z,state(LAYOUT[name],x,z)] for x,z in LAYOUT[name]] for name in names},y=[151,152])
    def datapack(self,names):
        files=self.base.datapack(names)
        for i,name in enumerate(names):
            layout=LAYOUT[name]
            block=["fill 405 151 -411 407 152 -409 air","setblock 405 151 -408 torch"]
            for x,z in layout:block.append(f"fill {x} 151 {z} {x} 152 {z} {state(layout,x,z)}")
            key=f"data/animal/function/s{i}.mcfunction";mark=f"say AQLAVA_BEGIN_{name}_END"
            assert files[key].count(mark)==1
            files[key]=files[key].replace(mark,"\n".join(block+[mark]))
            checks=["if block 405 151 -408 torch"]
            for x in range(405,408):
                for z in range(-411,-408):
                    for y in (151,152):
                        material=state(layout,x,z) if (x,z) in layout else "air"
                        checks.append(f"if block {x} {y} {z} {material}")
            for phase in "ve":
                key=f"data/animal/function/{phase}{i}.mcfunction";mark="if block 406 152 -410 air"
                assert files[key].count(mark)==1
                files[key]=files[key].replace(mark," ".join(checks))
        return files
if __name__=="__main__":
    label=sys.argv[1]
    mode=sys.argv[2]; assert mode in ("base","pane")
    role=sys.argv[3]; assert role in ("rgb","ordinary")
    names=sys.argv[4:] or list(LAYOUT)
    path=build(mode=="pane",role=="rgb")
    assert not (HERE/label).exists()
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(names),
        glcache=str(guarded.BUILD/"driver-cache"),**{"period-ticks":"180","shot-gap":".15",
        "compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(path,label,"off",fixed,HERE,Room)
