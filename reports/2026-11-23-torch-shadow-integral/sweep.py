"""Take calibrated Minecraft frames across a block boundary at fixed torch positions."""
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
from measure_density import TorchCounts, guarded, survey
from integral import ROOT

POSES = dict(zip(("left-far","left","centre","right","right-far"), (208.96,208.98,209.,209.02,209.04)))


class Sweep(TorchCounts):
    positions=POSES

    def __init__(self,rooms):
        super().__init__(rooms)
        self.STAGE_TABLE=dict.fromkeys(self.positions)

    def self_test(self,names):
        assert names in (list(POSES),["left","centre"])

    def geometry(self,names):
        return dict(sites=survey(),time=9800,stages=names,cameraX=self.positions)

    def datapack(self,names):
        self.self_test(names)
        base=TorchCounts(self.rooms).datapack(["birch-4"])
        files={k:v for k,v in base.items() if not re.search(r"/[spev]0.mcfunction$",k)}
        for i,(name,x) in enumerate((name,self.positions[name]) for name in names):
            for phase in "spev":
                key=f"data/animal/function/{phase}0.mcfunction"
                body=base[key].replace("208.5 64 355.5",f"{x} 64 355.5").replace("birch-4",name)
                if phase=="s":
                    body=body.replace("animal:s0 ",f"animal:s{(i+1)%len(names)} ")
                    for fn in "pve":
                        body=body.replace(f"animal:{fn}0 ",f"animal:{fn}{i} ")
                    body=body.replace("80t replace","4t replace")
                if phase in "ev":
                    assert f"positioned {x} 64 355.5" in body
                    body=body.replace("distance=..0.04,","distance=..0.001,")
                if phase=="e":
                    body="\n".join(line for line in body.splitlines() if " run setblock " not in line
                                   and not ("unless block " in line and " air " in line))+"\n"
                files[key.replace(f"{phase}0.",f"{phase}{i}.")]=body
        return files


class NightSweep(Sweep):
    def geometry(self,names):
        return dict(super().geometry(names),time=18000)

    def datapack(self,names):
        files=super().datapack(names)
        for i in range(len(names)):
            for phase in "sve":
                key=f"data/animal/function/{phase}{i}.mcfunction"
                assert files[key].count("9800")==1
                files[key]=files[key].replace("9800","18000")
        return files


class SettledNight(NightSweep):
    positions={"warm-first":208.98,"warm-second":208.98,"left":208.98,"centre":209.}

    def self_test(self,names):
        assert names==list(self.positions)


if __name__=="__main__":
    label,package,digest=sys.argv[1:4]
    mode=sys.argv[4:]
    assert mode in ([],["--pair"],["--night-pair"],["--night-settled"])
    scene=Sweep
    names=list(POSES)
    period="200"
    if mode:
        names=["left","centre"]
    if mode==["--night-pair"]:
        scene=NightSweep
    if mode==["--night-settled"]:
        scene=SettledNight
        names=list(scene.positions)
        period="500"
    pack=Path(package).resolve(strict=True)
    assert guarded.sha(pack)==digest and not (HERE/label).exists()
    fixed=dict(backend="vgl",size="1280x720",settle="1",stages=",".join(names),
               glcache=str(guarded.BUILD/"driver-cache"),**{"period-ticks":period,"shot-gap":".15",
               "compiler-mod":str(ROOT/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(pack,label,"off",fixed,HERE,scene)
