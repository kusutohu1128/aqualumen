"""Read the HDR comparison on wet stone, leaf cutouts, and an intervening cow."""
import json
from pathlib import Path
import sys

from visible_pack import HERE, ROOT, WORK
from meter import METER, replace
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-umbra"))
from moving import CACHE,COMPILER,guarded

STAGES=("wet-empty","wet-leaf-cow","wet-cleared")
LEAF="406 152 -410"


class WetRoom:
    def __init__(self, base):
        self.base=base
        for name in STAGES:
            base.STAGE_TABLE[name]=(True,True,base.WEST if name=="wet-leaf-cow" else None,"cobblestone",False,18000)

    def __getattr__(self,name):
        return getattr(self.base,name)

    def self_test(self,names):
        assert tuple(names)==STAGES

    def geometry(self,names):
        return {**self.base.geometry(names),"rain":True,"leafCell":LEAF}

    def datapack(self,names):
        files=self.base.datapack(names)
        files["data/animal/predicate/rain.json"]=json.dumps({"condition":"minecraft:weather_check","raining":True})
        directory="data/animal/function/"
        files[directory+"setup.mcfunction"]=replace(files[directory+"setup.mcfunction"],"weather clear","weather rain 1000000t")
        for i,name in enumerate(names):
            block="birch_leaves[persistent=true]" if name=="wet-leaf-cow" else "air"
            stage=directory+f"s{i}.mcfunction"
            files[stage]=replace(files[stage],f"say AQLAVA_BEGIN_{name}_END",f"setblock {LEAF} {block}\nsay AQLAVA_BEGIN_{name}_END")
            for phase in ("v","e"):
                key=directory+f"{phase}{i}.mcfunction"
                files[key]=replace(files[key],f"if block {LEAF} air",f"if predicate animal:rain if block {LEAF} {block}")
        return files


if __name__=="__main__":
    cache=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else CACHE
    assert guarded.sha(METER)=="aa82f618f9853b4c1bcd7b46dbf27223e130ea9b091938ceb591a63476c4a5c8"
    fixed={"backend":"vgl","size":"1600x900","settle":"1","period-ticks":"260","shot-gap":".15",
           "stages":",".join(STAGES),"glcache":str(cache),"compiler-mod":str(COMPILER)}
    guarded.launch(METER,sys.argv[1],"off",fixed,HERE,WetRoom)
