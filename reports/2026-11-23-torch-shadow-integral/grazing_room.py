"""Rebuild a reachable grazing light path in a guarded disposable Minecraft world."""
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"2026-11-22-gpu-profile"))
import run as guarded

WALL="397 148 -415 402 153 -415"
TRUNK="403 151 -411 403 152 -411"
BLOCKS={"405 150 -408":"stone","405 151 -408":"torch","404 151 -410":"grass_block"}
CAMERAS={"minus":399.023,"aligned":399.025,"plus":399.027}
ROOM="403 150 -413 410 155 -405"
BASE="data/animal/function/"


class Grazing:
    def __init__(self,rooms):
        self.rooms=rooms
        self.STAGE_TABLE=dict.fromkeys(CAMERAS)

    def __getattr__(self,k):
        return getattr(self.rooms,k)

    def self_test(self,names):
        assert names==list(CAMERAS)

    def geometry(self,names):
        return dict(wall=WALL,trunk=TRUNK,blocks=BLOCKS,cameraX=CAMERAS,stages=names,
                    feetY=148.3624,cameraZ=-411,source=[405.5,151.64,-407.5])

    def datapack(self,names):
        self.self_test(names)
        f=self.rooms.datapack(["day-white"])
        key=BASE+"setup.mcfunction"
        f[key]=f[key].replace("forceload add 403 -413", "forceload add 397 -415")
        key=BASE+"prepare.mcfunction"
        f[key]=f[key].replace("if loaded 403 150 -413 if loaded", "if loaded 397 148 -415 if loaded 403 150 -413 if loaded")
        f[key]+="execute unless loaded 397 148 -415 run schedule function animal:prepare 20t replace\n"
        # The parent proved this entire room empty before creating its test
        # shell. Check all additional wall cells before placing anything.
        build=f[BASE+"build.mcfunction"].splitlines()
        assert build[0]==f"fill {ROOM} white_concrete hollow"
        build=["scoreboard players set #free aq_room 1"]+[f"execute unless block {x} {y} -415 air run scoreboard players set #free aq_room 0"
                    for x in range(397,403) for y in range(148,154)]+[
            "execute if score #free aq_room matches 1 run function animal:fixture"]
        f[BASE+"build.mcfunction"]="\n".join(build)+"\n"
        f[BASE+"fixture.mcfunction"]="\n".join([f"fill {WALL} white_concrete",f"fill {TRUNK} birch_log",
            *[f"setblock {pos} {kind}" for pos,kind in BLOCKS.items()],
            f"tp {self.PLAYER} {self.POSE}",f"item replace entity {self.PLAYER} weapon.mainhand with paper",
            f"tag {self.PLAYER} add aq_ready","say AQLAVA_ARM_END"])+"\n"
        for i,(name,x) in enumerate(CAMERAS.items()):
            pos=f"{x} 148.3624 -411"
            f[BASE+f"s{i}.mcfunction"]="\n".join([f"gamemode spectator {self.PLAYER}",f"tp {self.PLAYER} {pos} 180 0",
                "time set 18000",f"say AQLAVA_BEGIN_{name}_END",f"schedule function animal:v{i} {self.READY_AT}t replace",
                f"schedule function animal:e{i} {self.STILL_AT}t replace",f"schedule function animal:s{(i+1)%len(names)} {self.PERIOD}t replace"])+"\n"
            checks=[f"positioned {pos} if entity @a[name={self.PLAYER},gamemode=spectator,distance=..0.0005,x_rotation=-0.01..0.01,y_rotation=179.98..-179.98]"]
            checks += [f"if block {pos} {kind}" for pos,kind in BLOCKS.items()]
            checks+=["if block 403 151 -411 birch_log","if block 403 152 -411 birch_log","if block 399 149 -415 white_concrete",
                     f"unless items entity {self.PLAYER} weapon.mainhand *",f"unless items entity {self.PLAYER} weapon.offhand *"]
            for prefix,ok,fail in (("v","READY","FAIL"),("e","STILL","DRIFT")):
                f[BASE+f"{prefix}{i}.mcfunction"]="\n".join(["scoreboard players set #ok aq_room 0",
                    "execute store result score #t aq_room run time query daytime",
                    "execute if score #t aq_room matches 18000 "+" ".join(checks)+" run scoreboard players set #ok aq_room 1",
                    f"execute if score #ok aq_room matches 1 run say AQLAVA_{ok}_{name}_END",
                    f"execute unless score #ok aq_room matches 1 run say AQLAVA_{fail}_{name}_END"])+"\n"
        return f


if __name__=="__main__":
    label,name,digest=sys.argv[1:]
    path=Path(name).resolve(strict=True)
    assert guarded.sha(path)==digest and not (HERE/label).exists()
    config=dict(backend="vgl",size="1281x721",settle="1",stages=",".join(CAMERAS),
                glcache=str(guarded.BUILD/"driver-cache"),**{"period-ticks":"200","shot-gap":".15",
                "compiler-mod":str(HERE.parents[1]/"dist/aqualumen-lighting-compiler-0.3.0.jar")})
    guarded.launch(path,label,"off",config,HERE,Grazing)
