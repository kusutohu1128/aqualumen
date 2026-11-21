"""Two diffuse wall reflections reaching a ceiling beyond the lamp aperture."""
import itertools
import json
import re

PLAYER="CeilingOptics"
PLAYER_UUID="00000000000040008000000000000418"
EVENT_RE=re.compile(r'\[Server\] AQLAVA_(READY|FAIL|STILL|DRIFT|BEGIN|ARM)(?:_([a-z0-9-]+))?_END')
ORIGIN=(400,230,-415)
POSE="407.65 230.48 -410.35 135 -56.18"
CORE=["white","red","grey","entry","middle","exit","off","reopened"]
ALL=[*CORE,"screen"]
STAGE_TABLE=dict.fromkeys(ALL)
HOOD=[((0,0,1),(1,3,4)),((1,0,1),(4,3,2)),((1,0,3),(4,3,4)),((1,0,2),(4,1,3)),((1,2,2),(4,3,3))]
WALL_A=((6,0,0),(7,3,4))
WALL_B=((3,0,5),(6,4,6))
CEILING=((6,4,3),(8,5,5))
SHUTTERS={"entry":((4,1,2),(5,2,3)),"middle":((3,0,4),(7,4,5)),"exit":((6,3,3),(8,4,5)),"screen":((6,0,4),(7,4,5))}
CELLS=list(itertools.product(range(9),range(6),range(7)))
LAMP=(1,1,2)

def world(point):
    return " ".join(str(i+j) for i,j in zip(ORIGIN,point))

def cells(box):
    return itertools.product(*(range(lo,hi) for lo,hi in zip(*box)))

def materials(stage):
    m=dict.fromkeys(CELLS,"air")
    def fill(box,mat):
        for p in cells(box): m[p]=mat
    for box in HOOD: fill(box,"black_concrete")
    fill(WALL_A,"red_concrete" if stage=="red" else "white_concrete")
    fill(WALL_B,"gray_concrete" if stage=="grey" else "white_concrete")
    fill(CEILING,"white_concrete")
    if stage in SHUTTERS: fill(SHUTTERS[stage],"black_concrete")
    if stage!="off": m[LAMP]="lantern"
    return m

def configure(period):
    global PERIOD,READY_AT,STILL_AT
    PERIOD=period;READY_AT=period//5;STILL_AT=period*17//20

configure(180)

def geometry(names):
    return dict(origin=ORIGIN,pose=POSE,hood=HOOD,wallA=WALL_A,wallB=WALL_B,ceiling=CEILING,shutters=SHUTTERS,
                lamp=LAMP,stages=names,verifiedCells=len(CELLS),daytime=18000)

def self_test(names):
    assert len(set(names))==len(names)>0 and set(names)<=set(ALL)
    assert materials("white")==materials("reopened")
    assert materials("white")[LAMP]=="lantern" and materials("off")[LAMP]=="air"

def datapack(names):
    f={}
    f["tick"]=[f"execute as @a[name={PLAYER},tag=!aq_init] run function ceiling:setup",
               f"execute as @a[name={PLAYER},tag=aq_ready,tag=!aq_started] if items entity @s weapon.offhand paper run function ceiling:start"]
    f["setup"]=["tag @s add aq_init","gamerule doDaylightCycle false","gamerule doWeatherCycle false","gamerule doMobSpawning false",
                "gamerule sendCommandFeedback false","difficulty peaceful","weather clear","time set 18000","gamemode creative @s",
                "scoreboard objectives add aq_room dummy","forceload add 400 -415 408 -409",f"tp @s {POSE}","schedule function ceiling:prepare 15t replace"]
    f["prepare"]=["execute if loaded 400 230 -415 if loaded 408 235 -409 run function ceiling:check_space",
                  "execute unless loaded 400 230 -415 run schedule function ceiling:prepare 15t replace",
                  "execute unless loaded 408 235 -409 run schedule function ceiling:prepare 15t replace"]
    f["check_space"]=["scoreboard players set #space aq_room 1"]+[
        f"execute unless block {world(p)} air run scoreboard players set #space aq_room 0" for p in CELLS
    ]+["execute if score #space aq_room matches 1 run function ceiling:arm"]
    f["arm"]=[f"item replace entity {PLAYER} weapon.mainhand with paper",f"tag {PLAYER} add aq_ready","say AQLAVA_ARM_END"]
    f["start"]=["tag @s add aq_started","item replace entity @s weapon.offhand with air","gamemode spectator @s","function ceiling:s0"]
    for i,stage in enumerate(names):
        expected=materials(stage)
        # Rebuild from the same known empty volume so a shutter from the preceding run cannot linger.
        f["s"+str(i)]=["fill 400 230 -415 408 235 -409 air"]+[
            f"setblock {world(p)} {mat}" for p,mat in expected.items() if mat!="air" and p!=LAMP
        ]+([f"setblock {world(LAMP)} lantern"] if stage!="off" else [])+[
            f"tp {PLAYER} {POSE}",f"say AQLAVA_BEGIN_{stage}_END",f"schedule function ceiling:v{i} {READY_AT}t replace",
            f"schedule function ceiling:e{i} {STILL_AT}t replace",f"schedule function ceiling:s{(i+1)%len(names)} {PERIOD}t replace"]
        f["check"+str(i)]=["scoreboard players set #ok aq_room 1"]+[
            f"execute unless block {world(p)} {mat} run scoreboard players set #ok aq_room 0" for p,mat in expected.items()
        ]+[f"execute positioned 407.65 230.48 -410.35 unless entity @a[name={PLAYER},gamemode=spectator,distance=..0.02,x_rotation=-56.23..-56.13,y_rotation=134.95..135.05] run scoreboard players set #ok aq_room 0"]
        for prefix,good,bad in (("v","READY","FAIL"),("e","STILL","DRIFT")):
            f[prefix+str(i)]=[f"function ceiling:check{i}",f"execute if score #ok aq_room matches 1 run say AQLAVA_{good}_{stage}_END",
                               f"execute unless score #ok aq_room matches 1 run say AQLAVA_{bad}_{stage}_END"]
    files={"pack.mcmeta":json.dumps({"pack":{"pack_format":48,"description":"Hooded lantern and two reflecting walls"}}),
           "data/minecraft/tags/function/tick.json":json.dumps({"values":["ceiling:tick"]})}
    files.update({f"data/ceiling/function/{name}.mcfunction":"\n".join(lines)+"\n" for name,lines in f.items()})
    return files
