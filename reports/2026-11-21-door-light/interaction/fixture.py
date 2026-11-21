"""Vanilla lever -> door interaction fixture for the Aqualumen door milestone (pure; no world access).

Geometry is the existing two-room sunset house (../house.py, imported read-only).  This module adds

  * a wall lever on the WEST face of the stripped dark-oak post at local (11, 2, 5), i.e. in Room A at
    (10, 2, 5), block state lever[face=wall,facing=west]; the post is a redstone conductor adjacent to the
    upper half of the dark oak door (11, 2, 6), so the lever powers the door through vanilla rules;
  * a survival player standing still in Room A who looks at the lever from reachable distance;
  * a world-local datapack that builds the house ONCE (initial construction, door closed, lever off, both
    lamps placed) and afterwards only WATCHES: it never writes a door or lever block again.  Every state
    change in the logs therefore comes from a real client right-click on the lever.

Server evidence: every tick the datapack evaluates a signature of the lever and both door halves with
`execute if block` and says `AQDI_S <kind> <tick> <sig> <x_mm> <y_mm> <z_mm> <yaw_cdeg> <pitch_cdeg> <ground>`
on every signature change (kind 1) and every 10 ticks (kind 0).
"""

import importlib.util
import json
import math
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # never write __pycache__ into other authors' directories
HERE = Path(__file__).resolve().parent
PARENT = HERE.parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


H = _load("aql_door_house", PARENT / "house.py")

NS = "aqdi"
PLAYER = "AqualumenDoor"
PLAYER_UUID = "00000000000040008000000000000451"
PLAYER_FILE = "00000000-0000-4000-8000-000000000451.dat"
PACK_NAME = "DoorInteraction"
EVENT_RE = re.compile(r"\[(?:Server|%s)\] AQDI_(READY|FAIL|DRIFT|ABORT|BUILT)((?:_[a-z0-9-]+)?)_END" % PLAYER)
SAMPLE_RE = re.compile(r"\[(?:Server|%s)\] AQDI_S (-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) END" % PLAYER)
ERROR_RE = re.compile(r"\[Render thread/ERROR\]|/ERROR\].*(aqdi:|function|DoorInteraction)")

WIDTH, HEIGHT, FOV, EYE = 1600, 900, H.FOV, H.EYE  # video size; vertical FOV and eye height as house.py
FOV_OPTION = (FOV - 70) / 40  # options.txt fov, same encoding as the earlier fixtures

AIR = H.AIR
LEVER_CELL = (10, 2, 5)  # Room A side of the post at (11, 2, 5)
LEVER_OFF = "minecraft:lever[face=wall,facing=west,powered=false]"
LEVER_ANY = "minecraft:lever[face=wall,facing=west]"
# Vanilla LeverBlock WEST_AABB (wall lever attached to the block on its EAST side): box(10,4,5, 16,12,11)/16
LEVER_BOX = ((10 + 10 / 16, 2 + 4 / 16, 5 + 5 / 16), (11.0, 2 + 12 / 16, 5 + 11 / 16))
LEVER_AIM = tuple((a + b) / 2 for a, b in zip(*LEVER_BOX))
POST = (11, 2, 5)
REACH = 4.5  # survival block_interaction_range in 1.21.1

FEET_LOCAL = (8.0, 1.0, 3.3)  # on the oak floor of Room A, 3.6 m from the lever
EYE_LOCAL = (FEET_LOCAL[0], FEET_LOCAL[1] + EYE, FEET_LOCAL[2])
HOLD_POS_MM = 25  # server flags a player that moves more than this from the anchor

DARK_LOWER = H.door("dark_oak", "lower", False)
DARK_UPPER = H.door("dark_oak", "upper", False)
DOOR_LOWER_PRED = "minecraft:dark_oak_door[half=lower,facing=east,hinge=left]"
DOOR_UPPER_PRED = "minecraft:dark_oak_door[half=upper,facing=east,hinge=left]"

# Signature bits written by the server watcher
BIT_LEVER_ON, BIT_LOWER_OPEN, BIT_UPPER_OPEN, BIT_LOWER_POWERED, BIT_UPPER_POWERED, BIT_DOOR_INTACT, BIT_LEVER_INTACT = (
    1, 2, 4, 8, 16, 32, 64)
SIG_CLOSED = BIT_DOOR_INTACT + BIT_LEVER_INTACT
SIG_OPEN = SIG_CLOSED + BIT_LEVER_ON + BIT_LOWER_OPEN + BIT_UPPER_OPEN + BIT_LOWER_POWERED + BIT_UPPER_POWERED


def decode(sig):
    return dict(
        lever_on=bool(sig & BIT_LEVER_ON), lower_open=bool(sig & BIT_LOWER_OPEN), upper_open=bool(sig & BIT_UPPER_OPEN),
        lower_powered=bool(sig & BIT_LOWER_POWERED), upper_powered=bool(sig & BIT_UPPER_POWERED),
        door_intact=bool(sig & BIT_DOOR_INTACT), lever_intact=bool(sig & BIT_LEVER_INTACT),
    )  # fmt: skip


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


fmt = H.fmt
world = H.world


def w(p):
    return " ".join(str(v) for v in world(p))


def cfmt(v):
    """Always with a decimal point: Minecraft centres integer x/z in Vec3 arguments (+0.5)."""
    return "%.4f" % v


def wf(p):
    return " ".join(cfmt(v) for v in world(p))


# ------------------------------------------------------------------ geometry


def pose():
    """Yaw/pitch (Minecraft convention) that put the crosshair on the lever's box centre."""
    d = [LEVER_AIM[i] - EYE_LOCAL[i] for i in range(3)]
    dist = math.sqrt(sum(v * v for v in d))
    yaw = math.degrees(math.atan2(-d[0], d[2]))
    pitch = -math.degrees(math.asin(d[1] / dist))
    return dict(eye=EYE_LOCAL, yaw=round(yaw, 2), pitch=round(pitch, 2))


POSE = pose()
FEET_WORLD = world(FEET_LOCAL)


def initial_grid():
    g = H.cells(H.role("closed-both"))  # dark oak door closed, warm + soul lantern placed
    require(g[LEVER_CELL] == AIR, "lever cell not free")
    g[LEVER_CELL] = LEVER_OFF
    return g


DYNAMIC = (H.DOOR_LOWER, H.DOOR_UPPER, LEVER_CELL)  # the only cells that change during the take


def project(point, pose_=None):
    p = pose_ or POSE
    u, v, depth = H.IF.project(p, point)  # 1280x720 window coordinates
    return u * WIDTH / H.WIDTH, v * HEIGHT / H.HEIGHT, depth


def ray_dir(pose_=None):
    p = pose_ or POSE
    f, _, _ = H.IF.basis(p["yaw"], p["pitch"])
    return f


def crosshair_hit():
    """First solid or lever hit along the view direction: (what, distance)."""
    e, f = EYE_LOCAL, ray_dir()
    far = tuple(e[i] + f[i] * REACH for i in range(3))
    best = (math.inf, None)
    t = H.seg_box(e, far, *LEVER_BOX)
    if t is not None:
        best = (t * REACH, "lever")
    for c, b in H.STATIC.items():
        if b == AIR or c == LEVER_CELL:
            continue
        i = H.block_id(b)
        if i in ("minecraft:glass_pane", "minecraft:chain"):
            continue
        t = H.seg_box(e, far, c, tuple(v + 1 for v in c))
        if t is not None and t * REACH < best[0]:
            best = (t * REACH, b)
    return best[1], best[0]


def view_boxes():
    """Full-cell occluders for line-of-sight tests (panes/chains/lamps/furniture plants ignored)."""
    out = []
    for c, b in initial_grid().items():
        if b == AIR:
            continue
        if H.block_id(b) in ("minecraft:glass_pane", "minecraft:chain", "minecraft:lantern", "minecraft:soul_lantern",
                             "minecraft:potted_red_tulip", "minecraft:lever") or b.endswith("]") and "_door[" in b:
            continue
        out.append((c, tuple(v + 1 for v in c), c, b))
    return out


ROIS = [  # (name, local point, what the pixel patch looks at)
    ("floor-front", (10.4, 1.0, 6.5), "white_concrete on the doorway axis, 0.6 m inside the door"),
    ("floor-mid", (9.8, 1.0, 6.5), "white_concrete on the doorway axis"),
    ("floor-far", (9.0, 1.0, 6.5), "white_concrete on the doorway axis, 2 m from the door"),
    ("floor-off-axis", (10.5, 1.0, 5.5), "white_concrete beside the doorway (control)"),
    ("door-lower", (11.0, 1.5, 6.5), "dark oak lower half (closed) / room B (open)"),
    ("door-upper", (11.0, 2.5, 6.5), "dark oak upper half (closed) / room B (open)"),
    ("lever", (10.75, 2.5, 5.5), "lever handle"),
]


def selftest():
    p = POSE
    g = initial_grid()
    require(len(g) == H.CELLS, "grid size")
    ex, ey, ez = (math.floor(v) for v in EYE_LOCAL)
    require(g[ex, ey, ez] == AIR and g[ex, ey - 1, ez] == AIR, "player cells not air")
    require(g[ex, ey - 2, ez] != AIR, "no floor below the player")
    # the 0.6 x 1.8 hitbox must be inside air cells
    for x in (7.7, 8.3):
        for z in (3.0, 3.6):
            for y in (1.0, 2.0, 2.79):
                require(g[math.floor(x), math.floor(y), math.floor(z)] == AIR, "hitbox in a block")
    what, dist = crosshair_hit()
    require(what == "lever", "crosshair misses the lever: %s at %.2f" % (what, dist))
    require(dist <= REACH - 0.5, "lever too far: %.2f" % dist)
    # lever is attached to a redstone conductor adjacent to the upper door half
    require(H.block_id(g[POST]) == "minecraft:stripped_dark_oak_log", "post is not a solid log")
    require(sum(abs(a - b) for a, b in zip(POST, H.DOOR_UPPER)) == 1, "post not adjacent to the upper half")
    require(all(abs(a - b) == 0 for a, b in zip(LEVER_CELL, (10, 2, 5))), "lever cell")
    # visibility: door halves, receivers and lever are inside the frame and unobstructed
    boxes = view_boxes()
    rois = []
    for name, pt, why in ROIS:
        u, v, depth = project(pt)
        require(depth > 0 and 60 <= u <= WIDTH - 60 and 60 <= v <= HEIGHT - 60, "ROI %s off screen: %.0f,%.0f" % (name, u, v))
        eye_pt = tuple(pt[i] - 1e-4 * (1 if i == 0 else 0) for i in range(3))
        target = (pt[0] - 1e-3, pt[1] + (1e-3 if pt[1] == 1.0 else 0), pt[2])
        require(H.clear(EYE_LOCAL, target, boxes), "ROI %s occluded" % name)
        rois.append(dict(name=name, local=list(pt), world=list(world(pt)), projected=[round(u, 1), round(v, 1)], what=why))
    # neither lamp is directly visible from the camera
    bare = [b for b in H.occluders(dict(H.role("open-both"), door="none", cow=False), light=True)]
    require(not H.clear(EYE_LOCAL, H.WARM_CENTRE, bare), "warm lantern visible from the camera")
    # the soul lantern is a second lit object in Room A: report whether the camera sees it (informational)
    soul_visible = H.clear(EYE_LOCAL, H.SOUL_CENTRE, bare)
    u, v, depth = project(H.SOUL_CENTRE)
    return dict(
        pose=dict(feetWorld=list(FEET_WORLD), eyeLocal=list(EYE_LOCAL), yaw=p["yaw"], pitch=p["pitch"]),
        crosshair=dict(what=what, distance=round(dist, 3), reach=REACH),
        rois=rois,
        soulLanternInFrame=bool(depth > 0 and 0 <= u <= WIDTH and 0 <= v <= HEIGHT and soul_visible),
    )


# ------------------------------------------------------------------ datapack


def count(cell, block, score="#n"):
    return "execute if block %s %s run scoreboard players add %s %s 1" % (w(cell), block, score, NS)


def pose_selector():
    p = POSE
    return "@a[name=%s,gamemode=survival,distance=..0.05,x_rotation=%s..%s,y_rotation=%s..%s]" % (
        PLAYER, fmt(p["pitch"] - 0.05), fmt(p["pitch"] + 0.05), fmt(p["yaw"] - 0.05), fmt(p["yaw"] + 0.05))


def datapack():
    """{relative path: text}."""
    lo_w, hi_w = world(H.LO), world(H.HI)
    grid = initial_grid()
    files = {
        "pack.mcmeta": json.dumps({"pack": {"pack_format": 48, "description": "Private Aqualumen door lever interaction"}}),
        "data/minecraft/tags/function/tick.json": json.dumps({"values": [NS + ":tick"]}),
    }
    S = lambda s: "scoreboard players " + s
    fn = {}
    fn["tick"] = [
        "execute as @a[name=%s,tag=!aqdi_started] run function %s:start" % (PLAYER, NS),
        "execute as @a[name=%s,tag=aqdi_started] run function %s:step" % (PLAYER, NS),
    ]
    start = [
        "tag @s add aqdi_started",
        "gamerule doDaylightCycle false",
        "gamerule doWeatherCycle false",
        "gamerule doMobSpawning false",
        "gamerule doMobLoot false",
        "gamerule doEntityDrops false",
        "gamerule doTileDrops false",
        "gamerule randomTickSpeed 0",
        "gamerule doFireTick false",
        "gamerule sendCommandFeedback false",
        "gamerule commandBlockOutput false",
        "gamerule announceAdvancements false",
        "difficulty peaceful",
        "weather clear",
        "time set %d" % H.TIME,
        "gamemode spectator @s",  # held in place while the house is built; survival only after verification
        "clear @s",
        "scoreboard objectives add %s dummy" % NS,
    ]
    for k, v in (("attempt", 0), ("ready_attempt", 0), ("built", 0), ("t", 0), ("watch", 0), ("live", 0), ("last", -1),
                 ("ten", 10), ("twenty", 20)):
        start.append(S("set #%s %s %d" % (k, NS, v)))
    start += [
        "forceload add %d %d %d %d" % (lo_w[0], lo_w[2], hi_w[0], hi_w[2]),
        "tp @s %s %s %s" % (wf(FEET_LOCAL), fmt(POSE["yaw"]), fmt(POSE["pitch"])),
        "schedule function %s:setup 20t replace" % NS,
    ]
    fn["start"] = start
    corners = [(x, lo_w[1], z) for x in (lo_w[0], hi_w[0]) for z in (lo_w[2], hi_w[2])]
    loaded = " ".join("if loaded %d %d %d" % c for c in corners)
    fn["setup"] = [
        S("add #attempt %s 1" % NS),
        S("set #loaded %s 0" % NS),
        "execute %s run scoreboard players set #loaded %s 1" % (loaded, NS),
        "execute if score #loaded %s matches 0 if score #attempt %s matches ..60 run schedule function %s:setup 20t replace" % (NS, NS, NS),
        "execute if score #loaded %s matches 0 if score #attempt %s matches 61.. run say AQDI_ABORT_unloaded_END" % (NS, NS),
        "execute if score #loaded %s matches 1 if score #built %s matches 0 run function %s:reserve" % (NS, NS, NS),
    ]
    lo, hi = H.LO, H.HI
    census = "execute store result score #e %s positioned %s if entity @e[type=!minecraft:player,dx=%d,dy=%d,dz=%d]" % (
        NS, wf(lo), hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])
    reserve = [S("set #n %s 0" % NS)] + [count(c, AIR) for c in sorted(grid)] + [
        census,
        "execute if score #n %s matches %d if score #e %s matches 0 run function %s:build" % (NS, H.CELLS, NS, NS),
        "execute unless score #n %s matches %d run say AQDI_ABORT_reserved_END" % (NS, H.CELLS),
        "execute unless score #e %s matches 0 run say AQDI_ABORT_entities_END" % NS,
    ]
    fn["reserve"] = reserve
    # Initial construction: static solids bottom-up (posts before panes), then lever, door, lamps.
    order = sorted((c for c, b in H.STATIC.items() if b != AIR), key=lambda c: (c[1], "glass_pane" in H.STATIC[c], c))
    build = [S("set #built %s 1" % NS)]
    build += ["setblock %s %s" % (w(c), H.STATIC[c]) for c in order]
    build += [
        "setblock %s %s" % (w(LEVER_CELL), LEVER_OFF),
        "setblock %s %s" % (w(H.DOOR_LOWER), DARK_LOWER),
        "setblock %s %s" % (w(H.DOOR_UPPER), DARK_UPPER),
        "setblock %s %s" % (w(H.WARM_CELL), H.WARM),
        "setblock %s %s" % (w(H.SOUL_CELL), H.SOUL),
        "say AQDI_BUILT_END",
        "schedule function %s:seat 20t replace" % NS,
    ]
    fn["build"] = build
    fn["seat"] = [  # re-assert the pose, then become a survival player on the floor and start watching
        "tp %s %s %s %s" % (PLAYER, wf(FEET_LOCAL), fmt(POSE["yaw"]), fmt(POSE["pitch"])),
        "gamemode survival %s" % PLAYER,
        S("set #watch %s 1" % NS),
        "schedule function %s:ready 40t replace" % NS,
    ]
    dyn = set(DYNAMIC)
    static_cells = [(c, b) for c, b in sorted(grid.items()) if c not in dyn]
    fn["vstatic"] = [count(c, b) for c, b in static_cells]
    n_static = len(static_cells)
    feet = " ".join(cfmt(v) for v in FEET_WORLD)
    fn["measure"] = [
        S("set #n %s 0" % NS),
        S("set #ok %s 0" % NS),
        "function %s:vstatic" % NS,
        census,
        "execute store result score #time %s run time query daytime" % NS,
        "execute store result score #g %s run data get entity %s OnGround" % (NS, PLAYER),
        "execute if score #n %s matches %d if score #e %s matches 0 if score #time %s matches %d if score #g %s matches 1 "
        "positioned %s if entity %s run scoreboard players set #ok %s 1" % (NS, n_static, NS, NS, H.TIME, NS, feet, pose_selector(), NS),
    ]
    fn["ready"] = [
        S("add #ready_attempt %s 1" % NS),
        "function %s:measure" % NS,
        "execute if score #ok %s matches 1 if score #sig %s matches %d run scoreboard players set #live %s 1" % (NS, NS, SIG_CLOSED, NS),
        "execute if score #live %s matches 1 run say AQDI_READY_END" % NS,
        "execute if score #live %s matches 0 if score #ready_attempt %s matches ..15 run schedule function %s:ready 20t replace" % (NS, NS, NS),
        "execute if score #live %s matches 0 if score #ready_attempt %s matches 16.. run say AQDI_ABORT_ready_END" % (NS, NS),
    ]
    fn["step"] = [
        S("add #t %s 1" % NS),
        "execute if score #watch %s matches 1 run function %s:watch" % (NS, NS),
    ]
    L, DL, DU = w(LEVER_CELL), w(H.DOOR_LOWER), w(H.DOOR_UPPER)
    add = lambda b: "run scoreboard players add #sig %s %d" % (NS, b)
    fn["watch"] = [
        S("set #sig %s 0" % NS),
        "execute if block %s minecraft:lever[powered=true] %s" % (L, add(BIT_LEVER_ON)),
        "execute if block %s minecraft:dark_oak_door[half=lower,open=true] %s" % (DL, add(BIT_LOWER_OPEN)),
        "execute if block %s minecraft:dark_oak_door[half=upper,open=true] %s" % (DU, add(BIT_UPPER_OPEN)),
        "execute if block %s minecraft:dark_oak_door[half=lower,powered=true] %s" % (DL, add(BIT_LOWER_POWERED)),
        "execute if block %s minecraft:dark_oak_door[half=upper,powered=true] %s" % (DU, add(BIT_UPPER_POWERED)),
        "execute if block %s %s if block %s %s %s" % (DL, DOOR_LOWER_PRED, DU, DOOR_UPPER_PRED, add(BIT_DOOR_INTACT)),
        "execute if block %s %s %s" % (L, LEVER_ANY, add(BIT_LEVER_INTACT)),
        S("operation #d %s = #sig %s" % (NS, NS)),
        S("operation #d %s -= #last %s" % (NS, NS)),
        S("set #kind %s 0" % NS),
        "execute unless score #d %s matches 0 run scoreboard players set #kind %s 1" % (NS, NS),
        S("operation #m %s = #t %s" % (NS, NS)),
        S("operation #m %s %%= #ten %s" % (NS, NS)),
        "execute if score #m %s matches 0 if score #kind %s matches 0 run scoreboard players set #kind %s 2" % (NS, NS, NS),
        "execute unless score #kind %s matches 0 run function %s:emit" % (NS, NS),
        S("operation #last %s = #sig %s" % (NS, NS)),
        S("operation #m %s = #t %s" % (NS, NS)),
        S("operation #m %s %%= #twenty %s" % (NS, NS)),
        "execute if score #live %s matches 1 if score #m %s matches 0 run function %s:drift" % (NS, NS, NS),
    ]
    fn["drift"] = [
        "function %s:measure" % NS,
        "execute if score #ok %s matches 0 run say AQDI_DRIFT_END" % NS,
    ]
    fields = [("k", "#kind"), ("t", "#t"), ("sig", "#sig")]
    emit = ["execute store result storage %s:s %s int 1 run scoreboard players get %s %s" % (NS, f, s, NS) for f, s in fields]
    emit += [
        "execute store result storage %s:s x int 1 run data get entity @s Pos[0] 1000" % NS,
        "execute store result storage %s:s y int 1 run data get entity @s Pos[1] 1000" % NS,
        "execute store result storage %s:s z int 1 run data get entity @s Pos[2] 1000" % NS,
        "execute store result storage %s:s yaw int 1 run data get entity @s Rotation[0] 100" % NS,
        "execute store result storage %s:s pitch int 1 run data get entity @s Rotation[1] 100" % NS,
        "execute store result storage %s:s g int 1 run data get entity @s OnGround" % NS,
        "function %s:say_s with storage %s:s" % (NS, NS),
    ]
    fn["emit"] = emit
    fn["say_s"] = ["$say AQDI_S $(k) $(t) $(sig) $(x) $(y) $(z) $(yaw) $(pitch) $(g) END"]
    for k, lines in fn.items():
        files["data/%s/function/%s.mcfunction" % (NS, k)] = "\n".join(lines) + "\n"
    return files


def check_datapack(files):
    """Static validation: coordinates stay inside the reserve, the door and lever are written only by build,
    and no later function can toggle, open or replace them."""
    lo_w, hi_w = world(H.LO), world(H.HI)
    coord = re.compile(r"(?:block|fill|setblock|loaded|positioned|tp \S+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)")
    for path, text in files.items():
        for line in text.splitlines():
            for m in coord.finditer(line):
                x, y, z = map(float, m.groups())
                require(lo_w[0] <= x <= hi_w[0] + 1 and lo_w[1] <= y <= hi_w[1] + 1 and lo_w[2] <= z <= hi_w[2] + 1,
                        "outside the reserved volume: " + line)
    fdir = "data/%s/function/" % NS
    dyn_w = [w(c) for c in DYNAMIC]
    for path, text in files.items():
        name = path.rsplit("/", 1)[-1]
        for line in text.splitlines():
            if re.match(r"^(execute .* run )?(setblock|fill|clone|data modify block|data merge block|loot|place|summon|kill|item) ", line) \
                    or " run setblock " in line or " run fill " in line:
                require(name == "build.mcfunction", "world write outside build: %s: %s" % (name, line))
            if any(c in line for c in dyn_w) and name not in ("build.mcfunction",):
                require(re.match(r"^execute if block ", line), "door/lever cell referenced by a non-test command: %s" % line)
    require("tp " not in files[fdir + "reserve.mcfunction"] and "gamemode" not in files[fdir + "build.mcfunction"], "setup order")
    reserve = files[fdir + "reserve.mcfunction"].splitlines()
    require(sum("minecraft:air run" in l for l in reserve) == H.CELLS, "reserve covers every cell")
    static = files[fdir + "vstatic.mcfunction"].splitlines()
    require(len(static) == H.CELLS - len(DYNAMIC), "vstatic count")
    require(not any(c in l for l in static for c in dyn_w), "vstatic counts a dynamic cell")
    builds = files[fdir + "build.mcfunction"].splitlines()
    for cell, block in ((LEVER_CELL, LEVER_OFF), (H.DOOR_LOWER, DARK_LOWER), (H.DOOR_UPPER, DARK_UPPER)):
        require(sum(l == "setblock %s %s" % (w(cell), block) for l in builds) == 1, "initial construction of %s" % (cell,))
    require(sum(re.search(r"setblock %s " % re.escape(c), l) is not None for l in builds for c in dyn_w) == 3, "dynamic cells written once")
    for f in ("tick", "start", "setup", "reserve", "seat", "ready", "step", "watch", "measure", "drift", "emit", "say_s", "vstatic", "build"):
        require(fdir + f + ".mcfunction" in files, "missing " + f)
    refs = {m for t in files.values() for m in re.findall(r"function %s:(\w+)" % NS, t)}
    require(refs <= {p.rsplit("/", 1)[-1][:-11] for p in files if p.endswith(".mcfunction")}, "dangling function reference")


def simulate(files):
    """Replay the build function on an all-air reserve and compare with the intended initial grid, then
    check the verification counts expect exactly that grid."""
    fdir = "data/%s/function/" % NS
    grid = {world(c): AIR for c in initial_grid()}
    set_re = re.compile(r"^setblock (-?\d+) (-?\d+) (-?\d+) (\S+)$")
    for line in files[fdir + "build.mcfunction"].splitlines():
        if m := set_re.match(line):
            c = tuple(map(int, m.groups()[:3]))
            require(c in grid, "setblock outside fixture")
            grid[c] = m.group(4)
    want = {world(c): b for c, b in initial_grid().items()}
    bad = [c for c in grid if grid[c] != want[c]]
    require(not bad, "build differs from the intended grid: %s" % [(c, grid[c], want[c]) for c in bad[:3]])
    count_re = re.compile(r"^execute if block (-?\d+) (-?\d+) (-?\d+) (\S+) run scoreboard")
    hits = [m for m in map(count_re.match, files[fdir + "vstatic.mcfunction"].splitlines()) if m]
    require(all(grid[tuple(map(int, m.groups()[:3]))] == m.group(4) for m in hits), "vstatic expects a different block")
    return True


def plan():
    return dict(
        fixture="reports/2026-11-21-door-light/interaction/fixture.py (+ ../house.py read-only)",
        origin=H.ORIGIN, reservedCells=dict(local=[H.LO, H.HI], count=H.CELLS), time=H.TIME,
        lever=dict(cell=list(world(LEVER_CELL)), block=LEVER_OFF, attachedTo=list(world(POST)), box=[list(b) for b in LEVER_BOX]),
        door=dict(lower=list(world(H.DOOR_LOWER)), upper=list(world(H.DOOR_UPPER)), lowerBlock=DARK_LOWER, upperBlock=DARK_UPPER),
        lamps=dict(warm=dict(cell=list(world(H.WARM_CELL)), block=H.WARM), soul=dict(cell=list(world(H.SOUL_CELL)), block=H.SOUL)),
        signatureBits=dict(leverOn=BIT_LEVER_ON, lowerOpen=BIT_LOWER_OPEN, upperOpen=BIT_UPPER_OPEN, lowerPowered=BIT_LOWER_POWERED,
                           upperPowered=BIT_UPPER_POWERED, doorIntact=BIT_DOOR_INTACT, leverIntact=BIT_LEVER_INTACT,
                           closed=SIG_CLOSED, open=SIG_OPEN),
        player=dict(name=PLAYER, uuid=PLAYER_UUID, gamemode="survival", feetWorld=list(FEET_WORLD), yaw=POSE["yaw"], pitch=POSE["pitch"]),
        video=dict(width=WIDTH, height=HEIGHT, verticalFov=FOV),
    )


if __name__ == "__main__":
    rep = selftest()
    files = datapack()
    check_datapack(files)
    simulate(files)
    print(json.dumps(rep, indent=1))
    print("fixture selftest ok | functions", len(files) - 2, "| longest", max(len(t.splitlines()) for t in files.values()), "lines")
