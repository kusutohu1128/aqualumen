"""Edit an L-shaped dirt step beside a birch trunk and move a cow through its light."""
import sys
from pathlib import Path

from build_trial import HERE, ROOT, WORK
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-open-volume"))
from room import Grove, guarded, TRUNK

STAGES=["trunk","touching","separate","near-cow","walk","walk-cleared","cut-step","extinguished"]
STEPS={"touching":(406,151,-409),"separate":(407,151,-409)}


class SteppedGrove(Grove):
    def __init__(self,base):
        super().__init__(base)
        for name in STAGES:
            animal={"near-cow":(405.85,151,-408.35),"walk":(404.7,151,-410.4)}.get(name)
            base.STAGE_TABLE[name]=(False,False,animal,"grass_block",True,9800)

    def self_test(self,names):
        assert names==STAGES or names==STAGES[:3]

    def geometry(self,names):
        g=super().geometry(names)
        return dict(g,trunkPresent=names,sourceOff=["extinguished"],
                    steps={"touching":list(STEPS["touching"]),"separate":list(STEPS["separate"])},
                    singleStep=self.step_by_stage(names))

    def step_by_stage(self,names):
        return {s:("separate" if s=="separate" else "touching" if s in
                   ("touching","near-cow","walk","walk-cleared") else None) for s in names}

    def datapack(self,names):
        files=super().datapack(names)
        for i,name in enumerate(names):
            previous="birch_log" if name=="trunk" else "air"
            blocks={key:("grass_block" if key==self.step_by_stage(names)[name] else "air") for key in STEPS}
            key=f"data/animal/function/s{i}.mcfunction"
            source=f"fill {TRUNK} {previous}"
            assert files[key].count(source)==1
            steps=[f"setblock {' '.join(map(str,pos))} {blocks[k]}" for k,pos in STEPS.items()]
            files[key]=files[key].replace(source,"\n".join([f"fill {TRUNK} birch_log",*steps]))
            for phase in ("v","e"):
                key=f"data/animal/function/{phase}{i}.mcfunction"
                source=f"if block 406 152 -410 {previous} if block 406 151 -410 {previous}"
                assert files[key].count(source)==1
                tests=[f"if block {' '.join(map(str,pos))} {blocks[k]}" for k,pos in STEPS.items()]
                files[key]=files[key].replace(source," ".join(["if block 406 152 -410 birch_log if block 406 151 -410 birch_log",*tests]))
        return files


if __name__=="__main__":
    label,package,digest=sys.argv[1:4]
    extra=sys.argv[4:]
    assert extra in ([],["--geometry"])
    path=Path(package).resolve(strict=True)
    assert guarded.sha(path)==digest and not (HERE/label).exists()
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(STAGES[:3] if extra else STAGES),
               glcache=str(guarded.BUILD/"driver-cache"),**{"period-ticks":"200","shot-gap":".15",
               "compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(path,label,"off",fixed,HERE,SteppedGrove)
