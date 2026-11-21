"""World-local optical controls for a cow between warm and soul lanterns."""
import json
import re

PLAYER = "AqualumenOptics"
PLAYER_UUID = "00000000000040008000000000000411"
SELECT = "@e[type=minecraft:cow,tag=aq_crossing,limit=1]"
POSE = "409.48 151 -405.95 153.8 7"
WEST = (405.5, 151, -409.35)
EAST = (406.8, 151, -409.35)
FLOOR = "404 150 -412 409 150 -406"
ROOF = "403 155 -413 410 155 -405"
WARM = "404 151 -407"
SOUL = "408 151 -407"
EVENT_RE = re.compile(r'\[Server\] AQLAVA_(READY|FAIL|STILL|DRIFT|BEGIN|ARM)(?:_([a-z0-9-]+))?_END')
# warm, soul, cow position, floor, roof, daytime
STAGE_TABLE = {}
for position, cow in (("empty", None), ("west", WEST), ("east", EAST)):
    for source in ("warm", "soul", "both"):
        STAGE_TABLE[source + "-" + position] = (source != "soul", source != "warm", cow, "white_concrete", True, 18000)
STAGE_TABLE["both-restored"] = STAGE_TABLE["both-empty"]
for roof in (False, True):
    for pigment in ("white", "red"):
        STAGE_TABLE["day-" + pigment + ("-roof" if roof else "")] = (False, False, WEST, pigment + "_concrete", roof, 6000)
CORE = list(STAGE_TABLE)
HERD = [(x,151,z) for x in (404.65,405.85,407.05,408.25) for z in (-410.42,-411.50)]
STAGE_TABLE["day-herd"] = STAGE_TABLE["day-white"]
STAGE_TABLE["walk"] = (True, True, (404.7,151,-410.4), "white_concrete", True, 18000)
STAGE_TABLE["walk-cleared"] = STAGE_TABLE["both-empty"]
ALL = list(STAGE_TABLE)


def configure(period):
    global PERIOD, READY_AT, STILL_AT
    PERIOD = period
    READY_AT = period // 5
    STILL_AT = period * 17 // 20


configure(180)


def geometry(names):
    return dict(camera=POSE, warm=WARM, soul=SOUL, floor=FLOOR, roof=ROOF, receiverWallZ=-412,
                stages={n:STAGE_TABLE[n] for n in names}, herd=HERD if "day-herd" in names else [], readyAt=READY_AT, stillAt=STILL_AT)


def datapack(names):
    funcs = {}
    funcs["tick"] = [
        f"execute as @a[name={PLAYER},tag=!aq_init] run function animal:setup",
        f"execute as @a[name={PLAYER},tag=aq_ready,tag=!aq_start] if items entity @s weapon.offhand minecraft:paper run function animal:start",
    ]
    funcs["setup"] = ["tag @s add aq_init","gamerule doDaylightCycle false","gamerule doWeatherCycle false",
                      "gamerule doMobSpawning false","gamerule doMobLoot false","gamerule randomTickSpeed 0",
                      "gamerule sendCommandFeedback false","difficulty peaceful","weather clear","gamemode creative @s",
                      "scoreboard objectives add aq_room dummy","forceload add 403 -413 410 -405",
                      f"tp @s {POSE}", "schedule function animal:prepare 20t replace"]
    funcs["prepare"] = ["execute if loaded 403 150 -413 if loaded 410 155 -405 run function animal:room",
                        "execute unless loaded 403 150 -413 run schedule function animal:prepare 20t replace",
                        "execute unless loaded 410 155 -405 run schedule function animal:prepare 20t replace"]
    funcs["room"] = ["scoreboard players set #empty aq_room 1"]
    for x in range(403,411):
        for y in range(150,156):
            for z in range(-413,-404):
                funcs["room"].append(f"execute unless block {x} {y} {z} air run scoreboard players set #empty aq_room 0")
    funcs["room"].append("execute if score #empty aq_room matches 1 run function animal:build")
    funcs["build"] = ["fill 403 150 -413 410 155 -405 white_concrete hollow",
                      f"tp {PLAYER} {POSE}",f"item replace entity {PLAYER} weapon.mainhand with paper",
                      f"tag {PLAYER} add aq_ready","say AQLAVA_ARM_END"]
    funcs["start"] = ["tag @s add aq_start", "item replace entity @s weapon.offhand with air","function animal:s0"]
    for i, name in enumerate(names):
        warm,soul,cow,floor,roof,day = STAGE_TABLE[name]
        lamps=("lantern" if warm else "air","soul_lantern" if soul else "air")
        top="white_concrete" if roof else "air"
        stage=[f"time set {day}", f"tp {PLAYER} {POSE}", f"fill {FLOOR} {floor}", f"fill {ROOF} {top}",
               f"setblock {WARM} {lamps[0]}",f"setblock {SOUL} {lamps[1]}"]
        check=[f"if block {WARM} {lamps[0]}", f"if block {SOUL} {lamps[1]}",
               f"if block 405 150 -409 {floor}",f"if block 406 155 -409 {top}","if block 406 152 -413 white_concrete",
               "if block 406 152 -410 air",f"positioned 409.48 151 -405.95 if entity @a[name={PLAYER},distance=..0.04,x_rotation=6.95..7.05,y_rotation=153.75..153.85]"]
        if cow is None:
            stage.append(f"execute if entity {SELECT} run kill {SELECT}")
            check.append(f"unless entity {SELECT}")
        else:
            xyz=" ".join(map(str,cow))
            stage += [f'execute unless entity {SELECT} run summon cow {xyz} {{Tags:["aq_crossing"],NoAI:1b,PersistenceRequired:1b,Silent:1b,Rotation:[90f,0f]}}',
                      f"tp {SELECT} {xyz} 90 0"]
            check.append(f"positioned {xyz} if entity @e[type=cow,tag=aq_crossing,distance=..0.05,limit=1]")
        if "day-herd" in names:
            stage.append("kill @e[type=cow,tag=aq_herd]")
            if name=="day-herd":
                for hx,hy,hz in HERD:
                    stage.append(f'summon cow {hx} {hy} {hz} {{Tags:["aq_herd"],NoAI:1b,PersistenceRequired:1b,Silent:1b,Rotation:[90f,0f]}}')
                    check.append(f"positioned {hx} {hy} {hz} if entity @e[type=cow,tag=aq_herd,distance=..0.06]")
            else:
                check.append("unless entity @e[type=cow,tag=aq_herd]")
        stage += [f"say AQLAVA_BEGIN_{name}_END",f"schedule function animal:v{i} {READY_AT}t replace",
                  f"schedule function animal:e{i} {STILL_AT}t replace"]
        if name=="walk":
            stage += [f"item replace entity {PLAYER} weapon.mainhand with wheat",f"schedule function animal:release {PERIOD}t replace",
                      f"schedule function animal:s{i+1} {PERIOD+210}t replace"]
        elif i+1<len(names):
            stage.append(f"schedule function animal:s{i+1} {PERIOD}t replace")
        elif name!="walk-cleared":
            stage.append(f"schedule function animal:s0 {PERIOD}t replace")
        funcs[f"s{i}"]=stage
        for prefix, ok, fail in (("v","READY","FAIL"), ("e","STILL","DRIFT")):
            funcs[prefix+str(i)]=["scoreboard players set #ok aq_room 0","execute store result score #t aq_room run time query daytime",
                                 f"execute if score #t aq_room matches {day} {' '.join(check)} run scoreboard players set #ok aq_room 1",
                                 f"execute if score #ok aq_room matches 1 run say AQLAVA_{ok}_{name}_END",
                                 f"execute unless score #ok aq_room matches 1 run say AQLAVA_{fail}_{name}_END"]
    funcs["release"]=[f"data merge entity {SELECT} {{NoAI:0b}}","say AQ_WALK_START","function animal:track","schedule function animal:finish 160t replace"]
    funcs["track"]=[f"execute store result storage animal:walk pos.{a} int 1 run data get entity {SELECT} Pos[{j}] 1000"
                    for j,a in enumerate("xyz")]+["function animal:log with storage animal:walk pos","schedule function animal:track 4t replace"]
    funcs["log"]=["$say AQ_WALK_MM $(x) $(y) $(z)"]
    funcs["finish"]=["schedule clear animal:track",f"kill {SELECT}",f"item replace entity {PLAYER} weapon.mainhand with air","say AQ_WALK_END"]
    files={"pack.mcmeta":json.dumps({"pack":{"pack_format":48,"description":"Two lamps and a moving cow"}}),
           "data/minecraft/tags/function/tick.json":json.dumps({"values":["animal:tick"]})}
    files.update({f"data/animal/function/{k}.mcfunction":"\n".join(lines)+"\n" for k,lines in funcs.items()})
    return files


def self_test(names):
    assert names and len(set(names))==len(names) and all(n in STAGE_TABLE for n in names)
    assert "walk" not in names or names==["walk","walk-cleared"]
    assert STAGE_TABLE["both-restored"]==STAGE_TABLE["both-empty"]
