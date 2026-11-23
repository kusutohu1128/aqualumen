"""Plant and remove a torch and trunk under a leaf roof, then release a cow."""
import sys
from pack import BASE, BASE_SHA, HERE, ROOT, WORK

sys.path.insert(0,str(HERE.parent/"2026-11-22-gpu-profile"))
import run as guarded

TORCH = "405 151 -408"
TRUNK = "406 151 -410 406 152 -410"
STAGES = ["shade", "torch", "trunk", "shifted", "home", "trunk-cut", "extinguished", "walk", "walk-cleared"]
PACKS = {
    "control":(BASE, BASE_SHA),
    "trial":(WORK/"Aqualumen-Open-Volume.zip","d2e8b1396c7580762e606f83c0861f66d675b17e58af693316491aad3cf78363"),
    "meter":(WORK/"Aqualumen-Open-Volume-Meter.zip","515fdfd778294b15580502681f3de3ab99c7d477a83f2c134309964fb7701420"),
    "cell":(WORK/"Aqualumen-Torch-Cell.zip","e1e06b864967cd61305931d499f71a8f0f07eb66d5696c49eb3a5ecd36903671"),
    "cell-meter":(WORK/"Aqualumen-Torch-Cell-Meter.zip","e9e89380880436db339ad2cfcc66e2769c0b7228903deace7a11e3a49fdeeff8"),
}


class Grove:
    def __init__(self, base):
        self.base = base
        for name in STAGES:
            cow = (404.7,151,-410.4) if name=="walk" else None
            base.STAGE_TABLE[name] = (False,False,cow,"grass_block",True,9800)

    def __getattr__(self,key):
        return getattr(self.base,key)

    def self_test(self,names):
        assert names==STAGES or names==STAGES[:3]

    def geometry(self,names):
        return dict(self.base.geometry(names),source=TORCH, trunk=TRUNK, shiftedX=407.83,
                    roofMaterial="birch_leaves[persistent=true]", sourceOff=["shade","extinguished"])

    def datapack(self,names):
        self.self_test(names)
        files=self.base.datapack(names)
        for i,name in enumerate(names):
            block="birch_log" if name in ("trunk","shifted","home") else "air"
            lamp="air" if name in ("shade","extinguished") else "torch"
            key=f"data/animal/function/s{i}.mcfunction"
            roof=f"fill {self.ROOF} white_concrete"
            assert files[key].count(roof)==1
            files[key]=files[key].replace(roof, f"fill {self.ROOF} birch_leaves[persistent=true]\n"
                f"fill {TRUNK} {block}\nsetblock {TORCH} {lamp}")
            if name=="shifted":
                files[key]=files[key].replace(self.POSE,self.POSE.replace("409.48","407.83"))
            for prefix in ("v","e"):
                key=f"data/animal/function/{prefix}{i}.mcfunction"
                for old,new in {
                    "if block 406 152 -410 air": f"if block 406 152 -410 {block} if block 406 151 -410 {block} if block {TORCH} {lamp}",
                    "if block 406 155 -409 white_concrete":"if block 406 155 -409 birch_leaves[persistent=true]",
                }.items():
                    assert files[key].count(old)==1
                    files[key]=files[key].replace(old,new)
                if name=="shifted":
                    files[key]=files[key].replace("positioned 409.48","positioned 407.83")
        return files


def main():
    mode=sys.argv[1]
    label=sys.argv[2] if len(sys.argv)>2 else f"grove-{mode}"
    pack,expected=PACKS[mode]
    assert guarded.sha(pack)==expected and not (HERE/label).exists()
    placement=sys.argv[3:]==["--placement"]
    assert placement or not sys.argv[3:]
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(STAGES[:3] if placement else STAGES),
               glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"200","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(pack,label,"off",fixed,HERE,Grove)


if __name__=="__main__":
    main()
