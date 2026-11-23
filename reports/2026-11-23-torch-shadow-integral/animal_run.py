"""Use the existing moving-cow fixture with a hash-pinned diagnostic pack."""
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-23-mixed-occluders"))
from room_run import guarded,ROOT,SteppedGrove,STAGES,TRUNK

EDIT_STAGES=STAGES[:-1]+["trunk-cut","replanted",STAGES[-1]]


class EditedGrove(SteppedGrove):
    def __init__(self,base):
        super().__init__(base)
        base.STAGE_TABLE["replanted"]=base.STAGE_TABLE["cut-step"]

    def self_test(self,names):
        assert names==EDIT_STAGES

    def geometry(self,names):
        return dict(super().geometry(names),trunkPresent=[n for n in names if n!="trunk-cut"])

    def datapack(self,names):
        files=super().datapack(names)
        i=names.index("trunk-cut")
        source=f"fill {TRUNK} birch_log"
        key=f"data/animal/function/s{i}.mcfunction"
        assert files[key].count(source)==1
        files[key]=files[key].replace(source,f"fill {TRUNK} air")
        for phase in "ve":
            key=f"data/animal/function/{phase}{i}.mcfunction"
            check="if block 406 152 -410 birch_log if block 406 151 -410 birch_log"
            assert files[key].count(check)==1
            files[key]=files[key].replace(check,check.replace("birch_log","air"))
        return files

if __name__=="__main__":
    label,package,digest=sys.argv[1:4]
    assert sys.argv[4:] in ([],["--edits"])
    pack=Path(package).resolve(strict=True)
    assert guarded.sha(pack)==digest and not (HERE/label).exists()
    edits=bool(sys.argv[4:])
    stages=EDIT_STAGES if edits else STAGES
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(stages),glcache=str(guarded.BUILD/"driver-cache"),
               **{"period-ticks":"200","shot-gap":".15","compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(pack,label,"off",fixed,HERE,EditedGrove if edits else SteppedGrove)
