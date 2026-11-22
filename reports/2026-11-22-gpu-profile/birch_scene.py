"""Extend only the private older-pack runs with the two historical birch poses."""
import json
from hashlib import sha256
from pathlib import Path
import math
import subprocess
import sys
from statistics import mean

R = Path(__file__).resolve().parent
FOREST = R.parent/"2026-11-20-local-light/forest-tools"
HIST = R.parent/"2026-11-21-lava-light/wall-v190/birch-stable/capture"
SITE = json.loads((FOREST/"forest-site.json").read_text())
ROOMS = ("both-west", "day-white")
BIRCH = ("birch-off", "birch-torch")
STAGES = ROOMS + BIRCH
TORCH = "207 64 359"
POSE = "208.5 64 355.5 12.7 -2"
READY, STILL, PERIOD = 320, 780, 860


def audit_world():
    if str(FOREST) not in sys.path:
        sys.path.insert(0,str(FOREST))
    from worldread import World
    w=World()
    for item in SITE["existing_verified_cells"]:
        state=w.state(*item["cell"])
        assert state and state["Name"]==item["id"]
        properties={f"{k}={v}" for k,v in state.get("Properties",{}).items()}
        assert properties.issuperset(item["required_state_substrings"])
    for item in SITE["reserved_exact_air_cells"]:
        assert w.state(*item["cell"])=={"Name":"minecraft:air"}
    origin=[8*math.floor(c/8)-32 for c in SITE["camera"]["eye"]]
    for x in range(origin[0],origin[0]+64):
        for z in range(origin[2],origin[2]+64):
            for y in range(origin[1],origin[1]+64):
                assert w.name(x,y,z) not in (None,"minecraft:lava"),(x,y,z)
    assert w.unchanged()
    return dict(world=w.marker["world_id"],seed=w.marker["seed"],gridOrigin=origin,checkedBlocks=64**3,
                lavaBlocks=0,missingBlocks=0,existingCells=len(SITE["existing_verified_cells"]),
                reservedAir=len(SITE["reserved_exact_air_cells"]))


class BirchRooms:
    def __init__(self,rooms):
        self.rooms=rooms
        self.STAGE_TABLE={name:None for name in STAGES}

    def __getattr__(self,key):
        return getattr(self.rooms,key)

    def self_test(self,names):
        assert tuple(names)==STAGES
        self.rooms.self_test(ROOMS)

    def geometry(self,names):
        self.self_test(names)
        return dict(**self.rooms.geometry(ROOMS),birch={"pose":POSE,"time":9800,"slot":TORCH,
                    "stages":list(BIRCH),"readyAt":READY,"stillAt":STILL,"period":PERIOD})

    def datapack(self,names):
        self.self_test(names)
        files=self.rooms.datapack(ROOMS)
        prefix="data/animal/function/"
        # Keep both room windows byte-identical up to the next-stage destination.
        files[prefix+"s1.mcfunction"]=files[prefix+"s1.mcfunction"].replace(
            "schedule function animal:s0 ", "schedule function animal:s2 ")
        player=self.rooms.PLAYER
        def put(name,lines):
            files[prefix+name+".mcfunction"]="\n".join(lines)+"\n"
        for i,name in enumerate(BIRCH,2):
            lit=i==3
            wanted="minecraft:torch" if lit else "minecraft:air"
            start=[f"gamemode spectator {player}",f"tp {player} {POSE}","time set 9800",f"say AQLAVA_BEGIN_{name}_END"]
            # Place only in the verified reserved air cell, after the off-stage stays there.
            if lit:
                start.append(f"execute if block {TORCH} minecraft:air run setblock {TORCH} minecraft:torch")
            start += [f"schedule function animal:v{i} {READY}t replace",
                      f"schedule function animal:e{i} {STILL}t replace",
                      f"schedule function animal:s{0 if lit else 3} {PERIOD}t replace"]
            put("s"+str(i),start)
            checks=["scoreboard players set #ok aq_room 1",
                    "execute store result score #t aq_room run time query daytime",
                    "execute unless score #t aq_room matches 9800 run scoreboard players set #ok aq_room 0",
                    f"execute positioned 208.5 64 355.5 unless entity @a[name={player},gamemode=spectator,distance=..0.04,x_rotation=-2.05..-1.95,y_rotation=12.65..12.75] run scoreboard players set #ok aq_room 0"]
            for item in SITE["existing_verified_cells"]+SITE["reserved_exact_air_cells"]:
                xyz=" ".join(map(str,item["cell"]))
                block=item.get("id",wanted if xyz==TORCH else "minecraft:air")
                props=item.get("required_state_substrings")
                if props: block+="["+ ",".join(props)+"]"
                checks.append(f"execute unless block {xyz} {block} run scoreboard players set #ok aq_room 0")
            # Check every XZ chunk in the 64^3 captured field, including the far edges.
            for x in range(176,240,16):
                for z in range(320,384,16):
                    checks.append(f"execute unless loaded {x} 64 {z} run scoreboard players set #ok aq_room 0")
            for func,good,bad in (("v","READY","FAIL"),("e","STILL","DRIFT")):
                body=checks.copy()
                if lit and func=="e":
                    body += [f"execute if block {TORCH} minecraft:torch run setblock {TORCH} minecraft:air",
                             f"execute unless block {TORCH} minecraft:air run scoreboard players set #ok aq_room 0",
                             f"execute if score #ok aq_room matches 1 run say AQ_BIRCH_RESTORED",
                             f"gamemode creative {player}"]
                body += [f"execute if score #ok aq_room matches 1 run say AQLAVA_{good}_{name}_END",
                         f"execute unless score #ok aq_room matches 1 run say AQLAVA_{bad}_{name}_END"]
                put(func+str(i),body)
        return files


def tiles(image):
    raw=subprocess.check_output(["ffmpeg","-v","error","-i",str(image),"-vf","scale=360:202,format=gray",
                                 "-frames:v","1","-f","rawvideo","-"])
    assert len(raw)==360*202
    # Birch bark, adjacent trunk/ground boundary, far shore. Omit sky and torch flame.
    return [[raw[y*360+x] for y in range(y0,y1) for x in range(x0,x1)]
            for x0,y0,x1,y1 in [(98,32,146,145),(152,52,211,124),(228,92,350,138)]]


def image_check(folder,scene):
    historical="ground-noon" if scene==BIRCH[0] else "ground-evening"
    reference=HIST/(historical+".png")
    ref=tiles(reference)
    f2=tiles(folder/(scene+"-ingame.png"))
    a,b=[tiles(folder/(scene+"-x11-"+tag+".png")) for tag in ("a","b")]
    correlations=[]
    drift=[]
    for old,new,before,after in zip(ref,f2,a,b):
        mean_old,mean_new=mean(old),mean(new)
        x=[v-mean_old for v in old]
        y=[v-mean_new for v in new]
        correlations.append(sum(i*j for i,j in zip(x,y))/math.sqrt(sum(i*i for i in x)*sum(j*j for j in y)))
        drift.append(abs(mean(before)-mean(after)))
    # Dark/bright bark and ground edges retain geometry across the two packs.
    assert min(correlations)>.75 and max(drift)<=3,(scene,correlations,drift)
    return dict(historical=historical,historicalPngSha256=sha256(reference.read_bytes()).hexdigest(),landmarkCorrelation=correlations,
                captureMeanDisplayCodeDrift=drift,minCorrelation=.75,maxDriftCodes=3)
