"""Observe low afternoon sunlight on an exposed, white-concrete floor."""
from glass_room import HERE, ROOT, guarded

STAGES=("open-early","red","blue","stone","open-late")
# A three-block window runs north/south, perpendicular to the afternoon sun.
def block(stage,z):
    if stage in ("open-early","open-late"):return "air"
    if stage=="stone":return "stone"
    return (stage+"_stained_glass_pane[west=false,east=false,north="+str(z>-411).lower()
            +",south="+str(z<-409).lower()+"]")

class SunRoom:
    def __init__(self,base):
        self.base=base
        for name in STAGES:base.STAGE_TABLE[name]=(False,False,None,"white_concrete",False,9400)
    def __getattr__(self,key):return getattr(self.base,key)
    def self_test(self,names):
        assert tuple(names) in (STAGES,("open-early","red"))
    def geometry(self,names):
        return dict(self.base.geometry(names),barrier=[[406,151,-411],[406,153,-409]],
                    openWestWall=[[403,151,-412],[403,154,-406]])
    def datapack(self,names):
        files=self.base.datapack(names)
        for i,stage in enumerate(names):
            changes=["fill 403 151 -412 403 154 -406 air","fill 406 151 -411 406 153 -409 air"]
            checks=["if block 403 152 -410 air"]
            for z in range(-411,-408):
                material=block(stage,z)
                if material!="air":
                    changes.append(f"fill 406 151 {z} 406 153 {z} {material}")
                checks += [f"if block 406 {y} {z} {material}" for y in range(151,154)]
            mark="say AQLAVA_BEGIN_"+stage+"_END"
            f=f"data/animal/function/s{i}.mcfunction"
            assert files[f].count(mark)==1
            files[f]=files[f].replace(mark,"\n".join(changes+[mark]))
            for phase in "ve":
                f=f"data/animal/function/{phase}{i}.mcfunction"
                mark="if block 406 152 -410 air"
                assert files[f].count(mark)==1
                files[f]=files[f].replace(mark," ".join(checks))
        return files

PACKAGES={"baseline":("Aqualumen-Stained-Panes.zip","7f5403e7c3fd57666f2417837bfe3d72d4d142d7b4cce29fdeff891504e36a77"),
          "filtered":("Aqualumen-Sunlit-Panes.zip","c84ea61f7ae5cc97872edaf6789bc5541297f4a253f7465d6e16dbc51b60443f")}

def source_pack(mode):
    name,sha=PACKAGES[mode]
    path=ROOT/"dist"/name
    assert guarded.sha(path)==sha
    return path

def capture(pack,label,period,size="1280x720",stages=STAGES):
    fixed=dict(backend="vgl",size=size,settle="1",stages=",".join(stages),glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":str(period),"shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    assert not (HERE/label).exists()
    guarded.launch(pack,label,"off",fixed,HERE,SunRoom)

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",nargs="?",default="baseline",choices=PACKAGES)
    mode=parser.parse_args().mode
    capture(source_pack(mode),"sun-window" if mode=="baseline" else "sun-filtered",340)
