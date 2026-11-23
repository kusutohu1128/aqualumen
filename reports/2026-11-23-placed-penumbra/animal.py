"""Isolate temporal shadow changes when a cow passes the standing trunk."""
import sys
from pack import HERE,ROOT,WORK
from swept import METER
from body import METER as JOINT_METER
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-open-volume"))
from room import Grove,guarded,TRUNK

NAMES=["trunk","walk","walk-cleared"]
NEAR=["trunk","near-cow","walk","walk-cleared"]
class StillTree(Grove):
    def __init__(self,base):
        super().__init__(base)
        base.STAGE_TABLE["near-cow"]=(False,False,(405.85,151,-408.35),"grass_block",True,9800)
    def self_test(self,names):
        assert names in (NAMES,NEAR)
    def datapack(self,names):
        files=super().datapack(names)
        for i in range(1,len(names)):
            key=f"data/animal/function/s{i}.mcfunction"
            old=f"fill {TRUNK} air"
            assert files[key].count(old)==1
            files[key]=files[key].replace(old,f"fill {TRUNK} birch_log")
            for stage in ("v","e"):
                key=f"data/animal/function/{stage}{i}.mcfunction"
                old="if block 406 152 -410 air if block 406 151 -410 air"
                assert files[key].count(old)==1
                files[key]=files[key].replace(old,old.replace(" air"," birch_log"))
        return files
    def geometry(self,names):
        return dict(super().geometry(names),trunkPresent=names,sourceOff=[])
if __name__=="__main__":
    mode=sys.argv[1] if len(sys.argv)>1 else "terrain"
    filename,label,sha={
        "terrain":(METER,"cow-and-trunk","0c0e9752379b80680df4664a0f81832e8d5270b4f165d618475380e913557f4a"),
        "body":(JOINT_METER,"cow-and-trunk-joint","8e09c529a48ee717b1c3998ff0fa7bcae38800f0c09a3f21e32ed5598d70f572"),
        "ordinary":("ordinary/Aqualumen-Placed-Penumbra-Animal-Study.zip","animal-ordinary","231e3b92831701eea5d7129c65904a63302467b2dc3534a3ffc863c9d6c368ef")
    }[mode]
    candidate=WORK/filename
    assert guarded.sha(candidate)==sha and not (HERE/label).exists()
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(NAMES if mode=="terrain" else NEAR),
               glcache=str(guarded.BUILD/"driver-cache"),**{"period-ticks":"200","shot-gap":".15",
               "compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(candidate,label,"off",fixed,HERE,StillTree)
