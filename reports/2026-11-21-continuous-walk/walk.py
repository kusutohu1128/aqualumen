"""Uncut first-person walk: real dark-oak trunk -> roofed cave -> river bank (forest-to-bank.json).

Ordinary client (the three normal Lab mods, unchanged 0.2 physics, no recorder Mod) in a private,
exact-UUID/seed copy of the Lab world. Nothing in the world is written: the vanilla datapack only
reads entity data, says log lines, sets weather/time/gamerules/items on the private player and
rotates the camera.

    python3 walk.py --dry-run                         # no lock, no world copy, no launch
    python3 walk.py <shaderpack.zip> <out-dir-name>   # real run (Codex only; NVIDIA, DISPLAY :1)
        [--variant afternoon|dusk|dusk-rain|night-rain] [--light torch|lantern|soul_torch]

Movement is real client physics. The client holds W (actual XTest key on the verified, focused
Minecraft window) with autoJump off; an uphill stall triggers a Space press. Steering is NOT mouse
input: at each route corner a server tick function applies `tp @s ~ ~ ~ <yaw> <pitch>` (zero
translation; the client keeps its own position and velocity) once, when the server-side position
passes the corner tile centre minus LEAD. At the cave (direction reversal) and at the bank the
client releases W first and the rotation only happens after >= 1 s standing still. Every rotation
is logged as AQW_ROT with the sampled position. The only coordinate teleport is the initial setup.

Timeline: initial tp to the start tile facing the dark-oak bark, torch/lantern stored in hotbar
slot 2 with an empty selected slot -> READY -> video starts -> stored view -> actual key "2" draws
the light -> server sees it held for HOLD ticks, turns toward the route -> W ... cave stop/turn ...
bank stop, turn to the water -> END -> dwell -> video stops.

Server samples (every 2 ticks, 10 Hz, via `say`, which the integrated server logs even with chat
hidden): tick, feet XYZ (mm), yaw/pitch (1/100 deg), OnGround as reported by the client,
abilities.flying, selected slot, light-in-mainhand, stage, still-ticks.
"""

import argparse
import fcntl
import gzip
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "reports/2026-11-21-indirect-light"))
import capture as C  # noqa: E402  (copy_world, tree, nbt, digest, sha, READY_RE, LOCK)

SURVEY = HERE / "forest-to-bank.json"
WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d"
SEED = 308060
PLAYER = "AqualumenWalker"
PLAYER_UUID = "00000000000040008000000000000431"
PLAYER_FILE = "00000000-0000-4000-8000-000000000431.dat"
PACK_NAME = "ContinuousWalk"
NS = "aqw"
START, TREE, CAVE, BANK = (92, 64, 394), (91, 64, 394), (97, 57, 411), (99, 63, 401)

LEAD = 0.30  # blocks before a corner centre at which the moving turn fires (server-side position)
STOP_LEAD = {"cave": 1.3, "bank": 0.55}  # blocks before a stop centre at which W is released
# (cave: stone wall behind it absorbs overshoot; bank: open ground toward the water, release later)
STILL = 20  # ticks of < 3 mm/tick horizontal motion before a stop-turn rotation
HOLD = 40  # ticks the light must be held before the first turn
SAMPLE = 2  # ticks between samples (10 Hz)
WALK_PITCH = 8.0
BARK_PITCH = -12.0
BANK_PITCH = 22.0
VARIANTS = {
    "afternoon": (10800, "clear"),
    "dusk": (12700, "clear"),
    "dusk-rain": (12700, "rain"),
    "night-rain": (14500, "rain"),
}
LIGHTS = ("torch", "lantern", "soul_torch")
YAW = {(1, 0): -90.0, (-1, 0): 90.0, (0, 1): 0.0, (0, -1): 180.0}
EVENT_RE = re.compile(r"\[(?:Server|%s)\] AQW_([A-Z]+)((?: [-\w.]+)*) END" % PLAYER)
SAY_RE = re.compile(r"^(\$?)say AQW_")
SETTLE = 8.0  # seconds after client render readiness before recording
STORED_SECONDS = 3.0  # recorded stored-light view before the draw key
CAVE_DWELL = 1.5  # seconds after the cave rotation before W again
END_DWELL = 4.0
WALK_TIMEOUT = 150.0
STALL_JUMP = 1.5  # seconds of < 0.12 block progress while W held -> one actual Space tap
STALL_FAIL = 10.0  # seconds without a stage change and without progress -> abort
require = C.require


def fmt(v):
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ---------------------------------------------------------------- route (pure + read-only survey)


def load_route(path=SURVEY):
    s = json.loads(path.read_text())
    m = s["marker"]
    require(m["world_id"] == WORLD_ID and m["seed"] == str(SEED) and m["minecraft"] == "1.21.1", "Survey world ID")
    require(tuple(s["start"]) == START and tuple(s["tree"]) == TREE and s["treeSpecies"] == "dark_oak_log", "Survey tree")
    require(tuple(s["cave"]) == CAVE and tuple(s["bank"]) == BANK, "Survey cave/bank")
    a, b = [[tuple(c) for c in leg] for leg in s["steps"]]
    require(a[0] == START and a[-1] == CAVE == b[0] and b[-1] == BANK, "Survey legs")
    cells = a + b[1:]
    for p, q in zip(cells, cells[1:]):
        require(abs(q[0] - p[0]) + abs(q[2] - p[2]) == 1 and abs(q[1] - p[1]) <= 1, "Non-adjacent step %s->%s" % (p, q))
    return cells, len(a) - 1


def direction(p, q):
    return (q[0] - p[0], q[2] - p[2])


def stages(cells, cave_index, bank_yaw):
    """Ordered server stages. Collinear steps are grouped: only direction changes become turns."""
    out = [dict(kind="go", name="tree", cell=START, yaw=YAW[direction(cells[0], cells[1])], pitch=WALK_PITCH)]
    for i in range(1, len(cells) - 1):
        din, dout = direction(cells[i - 1], cells[i]), direction(cells[i], cells[i + 1])
        if din == dout:
            continue
        reverse = dout == (-din[0], -din[1])
        require(reverse == (i == cave_index), "Unexpected reversal at %s" % (cells[i],))
        if reverse:
            out.append(dict(kind="stop", name="cave", cell=cells[i], din=din, lead=STOP_LEAD["cave"]))
            out.append(dict(kind="spin", name="cave", cell=cells[i], yaw=YAW[dout], pitch=WALK_PITCH))
        else:
            out.append(dict(kind="turn", name="corner-%d" % i, cell=cells[i], din=din, yaw=YAW[dout], pitch=WALK_PITCH))
    require(any(s["name"] == "cave" for s in out), "Cave is not a stop")
    out.append(dict(kind="stop", name="bank", cell=BANK, din=direction(cells[-2], cells[-1]), lead=STOP_LEAD["bank"]))
    out.append(dict(kind="spin", name="bank", cell=BANK, yaw=bank_yaw, pitch=BANK_PITCH))
    return out


def box(cell, din, lo, hi, lat):
    """mm score ranges [x, y, z] for positions with progress s in [lo, hi] past the cell centre."""
    c = [cell[0] + 0.5, cell[2] + 0.5]
    ax = 0 if din[0] else 1
    sign = din[ax]
    along = sorted((c[ax] + sign * lo, c[ax] + sign * hi))
    side = (c[1 - ax] - lat, c[1 - ax] + lat)
    h = [None, None]
    h[ax], h[1 - ax] = along, side
    y = (cell[1] - 1.3, cell[1] + 1.6)
    mm = lambda r: (math.floor(r[0] * 1000), math.ceil(r[1] * 1000))
    return [mm(h[0]), mm(y), mm(h[1])]


def region(st, lead=LEAD):
    if st["kind"] == "turn":
        return box(st["cell"], st["din"], -lead, 1.0, 0.8)
    if st["kind"] == "stop":
        return box(st["cell"], st["din"], -st["lead"], 2.0, 0.8)
    if st["kind"] == "spin":
        return box(st["cell"], (1, 0), -1.6, 1.6, 1.6)
    return None


def bbox(cells, pad):
    lo = [min(c[i] for c in cells) - pad for i in range(3)]
    hi = [max(c[i] for c in cells) + pad for i in range(3)]
    return lo, hi


def read_world():
    """Read-only access to the saved Lab world (scout.py / worldread)."""
    sys.path.insert(0, str(HERE))
    import scout

    return scout


def check_terrain(cells, scout):
    """Route cells walkable (2-high, dry), jump headroom for up-steps, fall room for down-steps."""
    air = scout.air
    for i, p in enumerate(cells):
        require(scout.walk(p) and scout.block(*p) != "water", "Route cell not walkable: %s" % (p,))
        if i:
            q = cells[i - 1]
            if p[1] > q[1]:
                require(scout.block(q[0], q[1] + 2, q[2]) in air, "No jump headroom at %s" % (q,))
            if p[1] < q[1]:
                require(scout.block(p[0], q[1] + 1, p[2]) in air, "No step-down room at %s" % (p,))
    require(scout.block(*TREE) == "dark_oak_log" and scout.block(TREE[0], TREE[1] + 1, TREE[2]) == "dark_oak_log", "Trunk")
    roof = scout.roof(CAVE)
    require(roof >= 5, "Cave roof")
    return roof


def bank_facing(scout):
    """Yaw from the bank feet centre toward the mean of nearby water surface cells (y 62)."""
    water = [(x, z) for x in range(BANK[0] - 3, BANK[0] + 4) for z in range(BANK[2] - 3, BANK[2] + 4)
             if scout.block(x, 62, z) == "water"]  # fmt: skip
    require(water, "No water near the bank")
    dx = sum(x + 0.5 for x, _ in water) / len(water) - (BANK[0] + 0.5)
    dz = sum(z + 0.5 for _, z in water) / len(water) - (BANK[2] + 0.5)
    return round(math.degrees(math.atan2(-dx, dz)), 1), len(water)


def solid(scout, x, y, z):
    return scout.block(x, y, z) not in scout.air and scout.block(x, y, z) != "water"


# ---------------------------------------------------------------- datapack (pure)


def datapack(cells, plan_stages, variant, light, lead=LEAD):
    t, weather = VARIANTS[variant]
    lo, hi = bbox(cells, 3)
    S = lambda name: "scoreboard players %s" % name
    sc = lambda k: "#%s %s" % (k, NS)
    files = {
        "pack.mcmeta": json.dumps({"pack": {"pack_format": 48, "description": "Private Aqualumen continuous walk"}}),
        "data/minecraft/tags/function/tick.json": json.dumps({"values": [NS + ":tick"]}),
    }
    fn = {}
    fn["tick"] = [
        "execute as @a[name=%s,tag=!aqw_started] at @s run function %s:start" % (PLAYER, NS),
        "execute as @a[name=%s,tag=aqw_started] at @s run function %s:step" % (PLAYER, NS),
    ]
    fn["start"] = [
        "tag @s add aqw_started",
        "gamerule doDaylightCycle false",
        "gamerule doWeatherCycle false",
        "gamerule doMobSpawning false",
        "gamerule randomTickSpeed 0",
        "gamerule doFireTick false",
        "gamerule sendCommandFeedback false",
        "gamerule commandBlockOutput false",
        "gamerule announceAdvancements false",
        "difficulty peaceful",
        "weather %s" % weather,
        "time set %d" % t,
        "gamemode adventure @s",
        "scoreboard objectives add %s dummy" % NS,
        S("set %s 0" % sc("t")),
        S("set %s 0" % sc("stage")),
        S("set %s 0" % sc("ready")),
        S("set %s 0" % sc("attempt")),
        S("set %s 0" % sc("hold")),
        S("set %s 0" % sc("still")),
        S("set %s 0" % sc("abort")),
        S("set %s %d" % (sc("period"), SAMPLE)),
        "clear @s",
        "item replace entity @s hotbar.1 with minecraft:%s" % light,
        "tp @s %s %s %s 90 %s" % (fmt(START[0] + 0.5), fmt(START[1]), fmt(START[2] + 0.5), fmt(BARK_PITCH)),
        "schedule function %s:setup 20t replace" % NS,
    ]
    chunks = sorted({(c[0] >> 4, c[2] >> 4) for c in cells})
    loaded = " ".join("if loaded %d %d %d" % (cx * 16, START[1], cz * 16) for cx, cz in chunks)
    near = "if score #x %s matches %d..%d if score #z %s matches %d..%d if score #y %s matches %d..%d" % (
        NS, START[0] * 1000 + 450, START[0] * 1000 + 550, NS, START[2] * 1000 + 450, START[2] * 1000 + 550,
        NS, START[1] * 1000 - 5, START[1] * 1000 + 5)  # fmt: skip
    ok = "%s if score #g %s matches 1 if score #still %s matches 10.. if score #slot %s matches 0 if score #lit %s matches 0" % (
        near, NS, NS, NS, NS)  # fmt: skip
    fn["setup"] = [
        S("add %s 1" % sc("attempt")),
        "execute %s %s run scoreboard players set #ready %s 1" % (loaded, ok, NS),
        "execute if score #ready %s matches 1 run say AQW_READY 0 END" % NS,
        "execute if score #ready %s matches 0 if score #attempt %s matches ..90 run schedule function %s:setup 20t replace"
        % (NS, NS, NS),
        "execute if score #ready %s matches 0 if score #attempt %s matches 91.. run say AQW_ABORT unready END" % (NS, NS),
    ]
    step = [
        S("add %s 1" % sc("t")),
        S("operation #px %s = #x %s" % (NS, NS)),
        S("operation #pz %s = #z %s" % (NS, NS)),
    ]
    step += ["execute store result score #%s %s run data get entity @s Pos[%d] 1000" % (a, NS, i) for i, a in enumerate("xyz")]
    step += [
        "execute store result score #angle %s run data get entity @s Rotation[0]" % NS,
        "execute store result score #g %s run data get entity @s OnGround" % NS,
        "execute store result score #fly %s run data get entity @s abilities.flying" % NS,
        "execute store result score #slot %s run data get entity @s SelectedItemSlot" % NS,
        "execute store success score #lit %s if items entity @s weapon.mainhand minecraft:%s" % (NS, light),
        S("operation #dx %s = #x %s" % (NS, NS)),
        S("operation #dx %s -= #px %s" % (NS, NS)),
        S("operation #dz %s = #z %s" % (NS, NS)),
        S("operation #dz %s -= #pz %s" % (NS, NS)),
        S("add %s 1" % sc("still")),
        "execute unless score #dx %s matches -3..3 run scoreboard players set #still %s 0" % (NS, NS),
        "execute unless score #dz %s matches -3..3 run scoreboard players set #still %s 0" % (NS, NS),
        "execute if score #ready %s matches 1 if score #abort %s matches 0 run function %s:guard" % (NS, NS, NS),
        "execute if score #ready %s matches 1 if score #abort %s matches 0 run function %s:stage" % (NS, NS, NS),
        S("operation #m %s = #t %s" % (NS, NS)),
        S("operation #m %s %%= #period %s" % (NS, NS)),
        "execute if score #m %s matches 0 run function %s:sample" % (NS, NS),
    ]
    fn["step"] = step
    rng = lambda a, b: "%d..%d" % (a * 1000, b * 1000 + 999)
    fn["guard"] = [
        "execute unless score #x %s matches %s run scoreboard players set #abort %s 1" % (NS, rng(lo[0], hi[0]), NS),
        "execute unless score #y %s matches %s run scoreboard players set #abort %s 1" % (NS, rng(lo[1], hi[1] + 1), NS),
        "execute unless score #z %s matches %s run scoreboard players set #abort %s 1" % (NS, rng(lo[2], hi[2]), NS),
        "execute if score #abort %s matches 1 run say AQW_ABORT bounds END" % NS,
        "execute if score #fly %s matches 1 run scoreboard players set #abort %s 2" % (NS, NS),
        "execute if score #abort %s matches 2 run say AQW_ABORT flying END" % NS,
    ]
    fields = ["t", "x", "y", "z", "yaw", "pitch", "g", "fly", "slot", "lit", "stage", "still"]
    sample = [
        "execute store result storage %s:s %s int 1 run scoreboard players get #%s %s" % (NS, f, f, NS)
        for f in fields
        if f not in ("yaw", "pitch")
    ]
    sample += [
        "execute store result storage %s:s yaw int 1 run data get entity @s Rotation[0] 100" % NS,
        "execute store result storage %s:s pitch int 1 run data get entity @s Rotation[1] 100" % NS,
        "function %s:emit with storage %s:s" % (NS, NS),
    ]
    fn["sample"] = sample
    fn["emit"] = ["$say AQW_S " + " ".join("$(%s)" % f for f in fields) + " END"]
    dispatch = []
    for k, st in enumerate(plan_stages):
        dispatch.append("execute if score #stage %s matches %d run function %s:k%d" % (NS, k, NS, k))
        nxt = S("set %s %d" % (sc("stage"), k + 1))
        rot = "tp @s ~ ~ ~ %s %s" % (fmt(st.get("yaw", 0)), fmt(st.get("pitch", 0)))
        rotsay = "say AQW_ROT %d %s %s %s END" % (k, st["name"], fmt(st.get("yaw", 0)), fmt(st.get("pitch", 0)))
        if st["kind"] == "go":
            body = [
                "execute if score #lit %s matches 1 if score #slot %s matches 1 run scoreboard players add #hold %s 1" % (NS, NS, NS),
                "execute unless score #lit %s matches 1 run scoreboard players set #hold %s 0" % (NS, NS),
                "execute if score #hold %s matches %d.. %s run function %s:r%d" % (NS, HOLD, near, NS, k),
            ]
            fn["r%d" % k] = [rot, rotsay, "say AQW_CP %s END" % st["name"], nxt, "function %s:sample" % NS]
        else:
            (x0, x1), (y0, y1), (z0, z1) = region(st, lead)
            cond = "if score #x %s matches %d..%d if score #y %s matches %d..%d if score #z %s matches %d..%d" % (
                NS, x0, x1, NS, y0, y1, NS, z0, z1)  # fmt: skip
            if st["kind"] == "spin" and st["name"] == "bank":
                for axis, value in [("x", BANK[0]), ("z", BANK[2])]:
                    cond += " if score #%s %s matches %d..%d" % (axis, NS, value * 1000, value * 1000 + 999)
                cond += " if score #g %s matches 1" % NS
            if st["kind"] == "spin":
                cond += " if score #still %s matches %d.." % (NS, STILL)
            body = ["execute %s run function %s:r%d" % (cond, NS, k)]
            # A jump preserves the previous heading's velocity. Correct lateral drift
            # using the newest server position and rotate in place.
            if "din" in st and k > 0:
                start = plan_stages[k - 1]["cell"]
                length = abs(st["cell"][0] - start[0]) + abs(st["cell"][2] - start[2])
                if length >= 1:
                    dx, dz = st["din"]
                    axis, side = ("x", -dz) if dz else ("z", dx)
                    centre = st["cell"][0 if dz else 2] * 1000 + 500
                    for j, (offset, within) in enumerate([
                        (26 * side, "..%d" % (centre - 251)),
                        (0, "%d..%d" % (centre - 250, centre + 250)),
                        (-26 * side, "%d.." % (centre + 251)),
                    ]):
                        yaw = int((YAW[st["din"]] + offset + 180) % 360 - 180)
                        f = "lane%d_%d" % (k, j)
                        fn[f] = ["tp @s ~ ~ ~ %d %d" % (yaw, WALK_PITCH), "say AQW_LANE %d %d END" % (k, yaw)]
                        # The next stage may already have fired in this tick.
                        body.append("execute if score #stage %s matches %d if score #%s %s matches %s unless score #angle %s matches %d run function %s:%s" %
                                    (NS, k, axis, NS, within, NS, yaw, NS, f))
            if st["kind"] == "stop":
                fn["r%d" % k] = ["say AQW_STOP %d %s END" % (k, st["name"]), "say AQW_CP %s END" % st["name"], nxt, "function %s:sample" % NS]
            else:
                fn["r%d" % k] = [rot, rotsay, nxt, "function %s:sample" % NS]
                if k == len(plan_stages) - 1:
                    fn["r%d" % k].insert(2, "say AQW_END %d END" % k)
        fn["k%d" % k] = body
    fn["stage"] = dispatch
    for k, lines in fn.items():
        files["data/%s/function/%s.mcfunction" % (NS, k)] = "\n".join(lines) + "\n"
    return files


ALLOWED = re.compile(
    r"^(\$?say AQW_|execute |scoreboard |gamerule |difficulty peaceful$|weather (clear|rain)$|time set \d+$|"
    r"gamemode adventure @s$|tag @s add aqw_started$|clear @s$|item replace entity @s hotbar\.1 with minecraft:\w+$|"
    r"tp @s |schedule function aqw:setup 20t replace$|function aqw:\w+( with storage aqw:s)?$)"
)


def check_datapack(files, cells):
    """Static guards: allowed command set, exactly one absolute tp, all other tp zero-translation,
    every absolute coordinate inside the route bounding box, no block-writing commands."""
    lo, hi = bbox(cells, 3)
    absolute, relative = [], []
    for path, text in files.items():
        if not path.endswith(".mcfunction"):
            continue
        for line in text.splitlines():
            require(ALLOWED.match(line), "Disallowed command in %s: %s" % (path, line))
            require(not re.search(r"\b(fill|setblock|clone|summon|kill|place|forceload|data modify|data merge|spreadplayers)\b", line), line)
            for m in re.finditer(r"\bif loaded (-?\d+) (-?\d+) (-?\d+)", line):
                x, _, z = map(int, m.groups())
                require(lo[0] - 16 <= x <= hi[0] and lo[2] - 16 <= z <= hi[2], "Chunk check outside route: " + line)
            if line.startswith("tp "):
                if re.fullmatch(r"tp @s ~ ~ ~ -?[\d.]+ -?[\d.]+", line):
                    if "/lane" not in path:
                        relative.append(line)
                else:
                    absolute.append((path, line))
    require(len(absolute) == 1 and absolute[0][0].endswith("/start.mcfunction"), "Absolute teleports: %s" % absolute)
    x, y, z = map(float, absolute[0][1].split()[2:5])
    require((x, y, z) == (START[0] + 0.5, START[1], START[2] + 0.5), "Setup tp is not the start tile centre")
    return len(relative)


# ---------------------------------------------------------------- dry-run kinematic check of the stages


def parse_stage_regions(files):
    """Re-read the generated k<i> functions (not the Python structures) for the simulator."""
    out = {}
    num = r"(-?\d+)\.\.(-?\d+)"
    for path, text in files.items():
        m = re.search(r"/k(\d+)\.mcfunction$", path)
        if not m:
            continue
        r = re.search(r"#x aqw matches %s if score #y aqw matches %s if score #z aqw matches %s" % (num, num, num), text)
        out[int(m.group(1))] = dict(
            box=[tuple(map(int, r.groups()[i : i + 2])) for i in (0, 2, 4)] if r else None,
            still="#still" in text,
            go="#hold" in text,
        )
    return out


def simulate(files, plan_stages, cells, scout=None, latency_ticks=3, corridor=0.85):
    """Point walker with vanilla-like ground acceleration (v <- 0.546 v + 0.098 heading, ~4.3 m/s),
    reacting to the generated stage regions. No terrain collision: reports hitbox contacts with solid
    blocks next to the path (real collision resolves those) and fails if the centre leaves the
    route corridor or a stage never fires."""
    regs = parse_stage_regions(files)
    route = {(c[0], c[2]): c[1] for c in cells}
    x, z, y = START[0] + 0.5, START[2] + 0.5, float(START[1])
    vx = vz = 0.0
    yaw, stage, still, held_w, release_at, press_at = 90.0, 0, 0, False, None, None
    contacts, ticks, log, excursion = 0, 0, [], 0.0
    yidx = 0
    while stage < len(plan_stages):
        ticks += 1
        require(ticks < 20 * 120, "simulated walk did not finish (stage %d)" % stage)
        if release_at is not None and ticks >= release_at:
            held_w, release_at = False, None
        if press_at is not None and ticks >= press_at:
            held_w, press_at = True, None
        a = 0.098 if held_w else 0.0
        hx, hz = -math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
        vx, vz = vx * 0.546 + a * hx, vz * 0.546 + a * hz
        px, pz = x, z
        x, z = x + vx, z + vz
        tile = (math.floor(x), math.floor(z))
        if tile in route:
            y = float(route[tile])
            yidx = cells.index(next(c for c in cells if (c[0], c[2]) == tile))
        near = min(max(abs(x - (cx + 0.5)), abs(z - (cz + 0.5))) for cx, cz in route)
        excursion = max(excursion, near)
        require(near <= corridor, "simulated centre left the route corridor at %.2f %.2f" % (x, z))
        if scout is not None:
            for ox in (-0.3, 0.3):
                for oz in (-0.3, 0.3):
                    bx, bz = math.floor(x + ox), math.floor(z + oz)
                    if (bx, bz) not in route and any(solid(scout, bx, int(y) + h, bz) for h in (0, 1)):
                        contacts += 1
        still = still + 1 if abs(x - px) * 1000 <= 3 and abs(z - pz) * 1000 <= 3 else 0
        r = regs[stage]
        st = plan_stages[stage]
        fire = False
        if r["go"]:
            fire = ticks > HOLD
        else:
            b = r["box"]
            inside = all(lo <= v <= hi for v, (lo, hi) in zip((int(x * 1000), int(y * 1000), int(z * 1000)), b))
            fire = inside and (not r["still"] or still >= STILL)
        if fire:
            log.append((stage, st["kind"], st["name"], round(x, 2), round(z, 2), ticks))
            if st["kind"] == "stop":
                release_at = ticks + latency_ticks
            else:
                yaw = st["yaw"]
                if st["kind"] == "go":
                    press_at = ticks + latency_ticks
                elif st["kind"] == "spin" and stage + 1 < len(plan_stages):
                    press_at = ticks + latency_ticks + int(CAVE_DWELL * 20)
            stage += 1
    end = (math.floor(x), math.floor(z))
    require(max(abs(end[0] - BANK[0]), abs(end[1] - BANK[2])) <= 1, "simulated end tile %s" % (end,))
    return dict(endTile=end, maxExcursion=round(excursion, 2), ticks=ticks, seconds=round(ticks / 20, 1), hitboxContactTicks=contacts, events=log)


# ---------------------------------------------------------------- log parsing / validation (pure)

FIELDS = ["t", "x", "y", "z", "yaw", "pitch", "g", "fly", "slot", "lit", "stage", "still"]


def parse_events(text, start=0):
    out = []
    for m in EVENT_RE.finditer(text, start):
        out.append((m.group(1), m.group(2).split(), m.end()))
    return out


def sample_row(args):
    require(len(args) == len(FIELDS), "sample arity")
    v = dict(zip(FIELDS, (int(re.sub(r"[a-zA-Z]$", "", a)) for a in args)))
    return dict(t=v["t"], pos=[v["x"] / 1000, v["y"] / 1000, v["z"] / 1000], yaw=v["yaw"] / 100, pitch=v["pitch"] / 100,
                grounded=v["g"] == 1, flying=v["fly"] == 1, slot=v["slot"], lightInMainhand=v["lit"] == 1,
                stage=v["stage"], stillTicks=v["still"])  # fmt: skip


def validate(samples, events, cells, n_stages, n_turn_rots):
    """Movement evidence from server samples. Returns (summary, problems)."""
    problems = []
    rots = [e for e in events if e[0] == "ROT"]
    cps = [e[1][0] for e in events if e[0] == "CP"]
    if cps != ["tree", "cave", "bank"]:
        problems.append("checkpoints %s" % cps)
    if len(rots) != n_turn_rots:
        problems.append("rotations %d != %d" % (len(rots), n_turn_rots))
    if not any(e[0] == "END" for e in events):
        problems.append("no END")
    walk = [s for s in samples if s["stage"] >= 1]
    if not walk:
        return dict(samples=len(samples)), problems + ["no walking samples"]
    route_xz = {(c[0], c[2]): c[1] for c in cells}
    off, jumps, maxstep = [], 0, 0.0
    for a, b in zip(walk, walk[1:]):
        dt = max(1, b["t"] - a["t"])
        d = math.hypot(b["pos"][0] - a["pos"][0], b["pos"][2] - a["pos"][2]) / dt
        maxstep = max(maxstep, d)
        if d > 0.45 or abs(b["pos"][1] - a["pos"][1]) / dt > 0.8:
            jumps += 1
    for s in walk:
        x, y, z = s["pos"]
        tx, tz = math.floor(x), math.floor(z)
        ok = any(
            abs(tx - cx) <= 1 and abs(tz - cz) <= 1 and cy - 1.5 <= y <= cy + 1.6 for (cx, cz), cy in route_xz.items()
        )
        if not ok:
            off.append(s["pos"])
        if s["flying"]:
            problems.append("flying at t=%d" % s["t"])
            break
    if jumps:
        problems.append("%d non-physical displacements (teleport?)" % jumps)
    if off:
        problems.append("%d samples off the route corridor, e.g. %s" % (len(off), off[:2]))
    if any(not s["lightInMainhand"] or s["slot"] != 1 for s in walk):
        problems.append("light not held throughout the walk")
    last = walk[-1]
    if (math.floor(last["pos"][0]), math.floor(last["pos"][2])) != (BANK[0], BANK[2]) or max(s["stage"] for s in walk) < n_stages or not last["grounded"]:
        problems.append("did not finish at the bank")
    visited = {(math.floor(s["pos"][0]), math.floor(s["pos"][2])) for s in walk}
    covered = sum((c[0], c[2]) in visited for c in cells) / len(cells)
    if covered < 0.9:
        problems.append("route tile coverage %.2f" % covered)
    secs = (walk[-1]["t"] - walk[0]["t"]) / 20
    pre = [s for s in samples if s["stage"] == 0]
    summary = dict(
        samples=len(samples),
        walkSamples=len(walk),
        walkSeconds=round(secs, 1),
        inTargetLength=25 <= secs <= 80,
        maxHorizontalBlocksPerTick=round(maxstep, 3),
        groundedFraction=round(sum(s["grounded"] for s in walk) / len(walk), 3),
        airborneSamples=sum(not s["grounded"] for s in walk),
        routeTileCoverage=round(covered, 3),
        storedViewSamples=sum(not s["lightInMainhand"] for s in pre),
        drawnBeforeWalkSamples=sum(s["lightInMainhand"] for s in pre),
        rotations=[dict(stage=int(e[1][0]), name=e[1][1], yaw=float(e[1][2]), pitch=float(e[1][3])) for e in rots],
        checkpoints=cps,
    )
    return summary, problems


# ---------------------------------------------------------------- input / window safety


class Keys:
    """XTest key input only while the exact Minecraft window of our PID has focus."""

    def __init__(self, env, wid, pid, run=subprocess.run):
        self.env, self.wid, self.pid, self.run, self.down, self.log = env, wid, pid, run, set(), []

    def _out(self, args):
        r = self.run(["xdotool"] + args, env=self.env, text=True, capture_output=True, timeout=4)
        return r.stdout.strip() if r.returncode == 0 else None

    def focused(self):
        return self._out(["getwindowfocus"]) == self.wid and self._out(["getwindowpid", self.wid]) == str(self.pid)

    def _send(self, verb, key):
        require(self.focused(), "Minecraft window lost focus; refusing input")
        self.run(["xdotool", verb, key], env=self.env, check=True, timeout=4)
        self.log.append((round(time.time(), 3), verb, key))

    def press(self, key):
        self._send("keydown", key)
        self.down.add(key)

    def tap(self, key):
        self._send("key", key)

    def release(self, key):
        self.run(["xdotool", "keyup", key], env=self.env, timeout=4)
        self.down.discard(key)
        self.log.append((round(time.time(), 3), "keyup", key))

    def release_all(self):
        for key in sorted(self.down | {"w", "space", "a", "d"}):
            try:
                self.release(key)
            except Exception:  # noqa: BLE001 - keep releasing the rest
                pass


# ---------------------------------------------------------------- dry run


def build_plan(variant="afternoon", light="torch", scout=None):
    cells, cave_index = load_route()
    scout = scout or read_world()
    roof = check_terrain(cells, scout)
    bank_yaw, waters = bank_facing(scout)
    st = stages(cells, cave_index, bank_yaw)
    files = datapack(cells, st, variant, light)
    n_rel = check_datapack(files, cells)
    return dict(cells=cells, cave_index=cave_index, stages=st, files=files, roof=roof, bankYaw=bank_yaw,
                bankWaterCells=waters, relativeRotations=n_rel, scout=scout)  # fmt: skip


def dry_run():
    t0 = time.monotonic()
    p = build_plan()
    cells, st, files = p["cells"], p["stages"], p["files"]
    turns = [s for s in st if s["kind"] in ("go", "turn", "spin")]
    require(p["relativeRotations"] == len(turns), "one zero-translation rotation per turn")
    for v in VARIANTS:
        for light in LIGHTS:
            check_datapack(datapack(cells, st, v, light), cells)
    sim = simulate(files, st, cells, p["scout"])
    sim_slow = simulate(files, st, cells, None, latency_ticks=8, corridor=1.6)
    # Log parsing + validation on a synthetic run built from the simulator events.
    fake, t = [], 0
    for k, (stage, kind, name, x, z, tick) in enumerate(sim["events"]):
        fake.append("[Server thread/INFO]: [Not Secure] [%s] AQW_S %d %d 64000 %d 9000 800 1 0 1 1 %d 0 END" % (PLAYER, tick, x * 1000, z * 1000, stage))
    log = "\n".join(
        ["[Render thread/INFO]: [STDOUT]: [Aqualumen Physics] 0.2.0 contact bridge initialized (512)",
         "[Server thread/INFO]: [Not Secure] [Server] AQW_READY 0 END",
         "[Server thread/INFO]: [Not Secure] [%s] AQW_ROT 0 tree -90 8 END" % PLAYER,
         "[Server thread/INFO]: [Not Secure] [%s] AQW_CP cave END" % PLAYER] + fake)  # fmt: skip
    ev = parse_events(log)
    require([e[0] for e in ev[:3]] == ["READY", "ROT", "CP"] and len(ev) == 3 + len(fake), "event parse")
    rows = [sample_row(e[1]) for e in ev if e[0] == "S"]
    require(rows[0]["pos"][0] == sim["events"][0][3] and rows[0]["slot"] == 1, "sample parse")
    good = [dict(t=i * 5, pos=[c[0] + 0.5, c[1], c[2] + 0.5], yaw=0, pitch=8, grounded=True, flying=False, slot=1,
                 lightInMainhand=True, stage=1 + i * len(st) // len(cells), stillTicks=0) for i, c in enumerate(cells)]  # fmt: skip
    evs = [("CP", ["tree"], 0), ("CP", ["cave"], 0), ("CP", ["bank"], 0), ("END", ["0"], 0)]
    evs += [("ROT", ["%d" % i, s["name"], "0", "8"], 0) for i, s in enumerate(st) if s["kind"] != "stop"]
    summary, probs = validate(good, evs, cells, len(st), len(turns))
    require(not [q for q in probs if "teleport" in q or "corridor" in q], probs)
    bad = [dict(r) for r in good]
    bad[10] = dict(bad[10], pos=[bad[10]["pos"][0] + 6, bad[10]["pos"][1], bad[10]["pos"][2]])
    _, probs = validate(bad, evs, cells, len(st), len(turns))
    require(any("teleport" in q for q in probs) and any("corridor" in q for q in probs), "validator misses a teleport")

    # Window safety: input refused without focus; release_all always releases W/Space.
    class R:
        def __init__(self, focus):
            self.focus, self.calls = focus, []

        def __call__(self, args, **kw):
            self.calls.append(args)
            out = {"getwindowfocus": self.focus, "getwindowpid": "4242"}.get(args[1], "")
            return subprocess.CompletedProcess(args, 0, out + "\n", "")

    k = Keys({}, "77", 4242, R("77"))
    k.press("w")
    require(k.down == {"w"}, "press")
    k.release_all()
    require(not k.down and ["xdotool", "keyup", "space"] in k.run.calls, "release_all")
    k = Keys({}, "77", 4242, R("78"))
    try:
        k.press("w")
        raise AssertionError("pressed without focus")
    except RuntimeError:
        pass
    require(not any(c[1] == "keydown" for c in k.run.calls), "keydown sent without focus")

    target = Path(tempfile.mkdtemp(prefix="aql-walk-dry-"))
    for rel, text in p["files"].items():
        q = target / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(text)
    print("dry run ok:", target, "| %.1fs" % (time.monotonic() - t0))
    print("route cells %d (cave index %d), roof %d, bank yaw %s (%d water cells)" % (
        len(cells), p["cave_index"], p["roof"], p["bankYaw"], p["bankWaterCells"]))  # fmt: skip
    print("stages:", " ".join("%s:%s" % (s["kind"], s["name"]) for s in st))
    print("zero-translation rotations:", p["relativeRotations"], "| absolute tp: 1 (setup)")
    print("kinematic sim (3-tick input latency): %.1fs walk, end tile %s, max excursion %.2f, hitbox contact ticks %d" % (
        sim["seconds"], sim["endTile"], sim["maxExcursion"], sim["hitboxContactTicks"]))
    print("stress (8-tick latency, no collision): %.1fs, end tile %s, max excursion %.2f" % (
        sim_slow["seconds"], sim_slow["endTile"], sim_slow["maxExcursion"]))  # fmt: skip
    for e in sim["events"]:
        print("  stage %2d %-4s %-10s at x=%.2f z=%.2f tick %d" % e)
    return target


# ---------------------------------------------------------------- real run


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("pack")
    ap.add_argument("out")
    ap.add_argument("--variant", choices=sorted(VARIANTS), default="afternoon")
    ap.add_argument("--light", choices=LIGHTS, default="torch")
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--fps", type=int, default=60)
    a = ap.parse_args(argv)
    require(os.getuid() == 1000, "Fixed lock/runtime paths assume uid 1000")
    width, height = map(int, a.size.split("x"))
    pack = Path(a.pack)
    require(pack.is_file() and not pack.is_symlink() and pack.suffix == ".zip", "Pack must be a regular .zip")
    pack = pack.resolve()
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", a.out) is not None, "Out dir must be a simple name")
    out = HERE / a.out
    require(out.parent == HERE and not out.exists() and not out.is_symlink(), "Out dir exists or escapes")
    p = build_plan(a.variant, a.light)
    cells, st, files = p["cells"], p["stages"], p["files"]
    n_rot = p["relativeRotations"]
    simulate(files, st, cells)
    script_hashes = {n: C.sha((HERE / n).read_bytes()) for n in ("walk.py", "forest-to-bank.json", "scout.py")}

    lock = open(C.LOCK, "a+b")
    fcntl.flock(lock, fcntl.LOCK_EX)
    sys.path.insert(0, str(ROOT / "tools"))
    import ground_shadow_lab as g

    lab = g.lab
    orig = g.GAME.resolve()
    runtime = json.loads((ROOT / "reports/2026-11-20-underwater-refinement/local-launch.json").read_text())
    assets = orig.parents[2] / "assets"
    src = orig / "saves" / lab.WORLD
    require(lab.WORLD_ID == WORLD_ID, "Lab world ID constant")
    require(src.is_dir() and not src.is_symlink() and src.resolve().parent == orig / "saves", "Source world path")
    require(not str(pack).startswith(str(orig) + os.sep), "Pack must not live inside the Lab instance")
    require(os.access("/tmp/aqualumen-wm-close", os.X_OK), "Missing /tmp/aqualumen-wm-close")
    originals = {n: C.sha((orig / n).read_bytes()) for n in ("options.txt", "config/iris.properties", "config/sodium-options.json") if (orig / n).is_file()}  # fmt: skip
    mods = {n: C.sha((orig / "mods" / n).read_bytes()) for n in sorted(lab.NORMAL_MODS)}
    require(len(mods) == 3, "Expected exactly the three normal mods")

    out.mkdir()
    labroot = Path(tempfile.mkdtemp(prefix="continuous-walk-", dir=orig.parent)).resolve()
    game = labroot / "Aqualumen Lab/minecraft"
    require(labroot.parent == orig.parent and not str(game).startswith(str(orig) + os.sep), "Clone path")
    game.mkdir(parents=True)
    (out / "private-game.txt").write_text(str(game) + "\n")
    for n in ["shaderpacks", "mods", "config", "saves"]:
        (game / n).mkdir()

    lab.shared.world_marker()
    with (src / "session.lock").open("r+b") as f:
        fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        source_manifest = C.copy_world(src, game / "saves" / lab.WORLD)
    world = (game / "saves" / lab.WORLD).resolve()
    require(world.parent == game / "saves" and len(list((game / "saves").iterdir())) == 1, "Clone not unique")
    require(C.tree(world) == source_manifest, "Clone differs from source")
    marker = lab.pairs((world / "aqualumen-world.properties").read_bytes())
    require(marker.get("world_id") == WORLD_ID and marker.get("seed") == str(SEED), "Clone UUID/seed marker")
    level = C.nbt(gzip.decompress((world / "level.dat").read_bytes()))
    require(level["Data"]["WorldGenSettings"]["seed"] == SEED, "level.dat seed differs")
    require(not (world / "playerdata" / PLAYER_FILE).exists(), "Walker player already in source world")
    require(not (world / "datapacks" / PACK_NAME).exists(), "Datapack already present")

    for n in sorted(lab.NORMAL_MODS):
        shutil.copy(orig / "mods" / n, game / "mods")
        require(C.sha((game / "mods" / n).read_bytes()) == mods[n], "Mod copy differs")
    shutil.copy(pack, game / "shaderpacks")
    pack_sha = C.sha(pack.read_bytes())
    for n in ["sodium-options.json", "iris.properties"]:
        if (orig / "config" / n).exists():
            shutil.copy(orig / "config" / n, game / "config")
    iris = game / "config/iris.properties"
    iris.write_bytes(lab.replace_values(iris.read_bytes(), {"shaderPack": pack.name}, "="))
    require(lab.pairs(iris.read_bytes()).get("enableShaders", "true") == "true", "Shaders disabled in config")
    options = dict(
        lab.OPTIONS, maxFps="120", overrideWidth=str(width), overrideHeight=str(height), pauseOnLostFocus="false",
        chatVisibility="2", mainHand='"right"', autoJump="false", bobView="true",
        **{"key_key.left": "key.keyboard.a", "key_key.right": "key.keyboard.d", "key_key.forward": "key.keyboard.w", "key_key.jump": "key.keyboard.space", "key_key.hotbar.2": "key.keyboard.2"},
    )  # fmt: skip
    (game / "options.txt").write_bytes(lab.replace_values((orig / "options.txt").read_bytes(), options, ":"))
    kit = world / "datapacks" / PACK_NAME
    for rel, text in files.items():
        q = kit / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(text)
    plan = dict(
        type="actual client walk plan; movement by client physics, rotations server zero-translation tp",
        variant=a.variant, time=VARIANTS[a.variant][0], weather=VARIANTS[a.variant][1], light=a.light,
        stages=[{k: v for k, v in s.items()} for s in st], bankYaw=p["bankYaw"], lead=LEAD, stopLead=STOP_LEAD,
        datapackDigest=C.digest({k: C.sha(v.encode()) for k, v in files.items()}), options=options, pack=pack.name,
        packSha256=pack_sha, playerUuid=PLAYER_UUID, scripts=script_hashes,
        world=dict(name=lab.WORLD, worldId=WORLD_ID, seed=SEED, sourceDigest=C.digest(source_manifest)),
    )  # fmt: skip
    (out / "plan.json").write_text(json.dumps(plan, indent=2))

    env = dict(
        os.environ, DISPLAY=":1", XDG_RUNTIME_DIR="/run/user/1000", DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus",
        __GLX_VENDOR_LIBRARY_NAME="nvidia", ALSOFT_DRIVERS="null", XDG_CACHE_HOME=str(labroot / "cache"),
    )  # fmt: skip
    for k in ["JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "GALLIUM_DRIVER", "LIBGL_KOPPER_DRI2", "VK_DRIVER_FILES"]:
        env.pop(k, None)
    java = [
        runtime["java"], "-Xms512m", "-Xmx2600m", "-XX:ActiveProcessorCount=4",
        "-Dorg.lwjgl.openal.libname=libopenal.so.1", "-cp", ":".join(runtime["cp"]),
        "net.fabricmc.loader.impl.launch.knot.KnotClient", "--username", PLAYER, "--version", "1.21.1",
        "--gameDir", str(game), "--assetsDir", str(assets), "--assetIndex", "17", "--uuid", PLAYER_UUID,
        "--accessToken", "0", "--userType", "legacy", "--width", str(width), "--height", str(height),
        "--quickPlaySingleplayer", lab.WORLD,
    ]  # fmt: skip
    log = out / "client.log"
    raw_video = labroot / "walk-raw.mkv"
    samples, events, timeline, jumps = [], [], [], []
    proc = ffmpeg = keys = None
    status = "incomplete"

    def note(kind, **kw):
        row = dict(wall=round(time.time(), 3), kind=kind, **kw)
        timeline.append(row)
        print(json.dumps(row), flush=True)

    def window():
        r = subprocess.run(["xdotool", "search", "--all", "--onlyvisible", "--pid", str(proc.pid), "--name", "Minecraft"],
                           env=env, text=True, capture_output=True)  # fmt: skip
        return r.stdout.strip() if r.returncode == 0 and len(r.stdout.split()) == 1 else None

    cursor = [0]

    def poll():
        """Read new log events; returns the list of new (kind, args, wall)."""
        text = log.read_text(errors="replace")
        fatal = C.fatal(text)
        require(fatal is None or fatal.startswith("Fixture"), str(fatal))
        new = []
        for kind, args, end in parse_events(text, cursor[0]):
            cursor[0] = end
            now = round(time.time(), 3)
            if kind == "S":
                samples.append(dict(sample_row(args), wall=now))
            else:
                events.append((kind, args, now))
                new.append((kind, args, now))
                note("server", event=kind, args=args)
                require(kind != "ABORT", "Server guard abort: %s" % args)
        require(proc.poll() is None, "Client exited")
        return new

    def wait_for(kind, timeout, first=None):
        deadline = time.monotonic() + timeout
        while True:
            for e in poll():
                if e[0] == kind and (first is None or e[1][:1] == [first]):
                    return e
            require(time.monotonic() < deadline, "Timed out waiting for AQW_%s" % kind)
            time.sleep(0.05)

    with log.open("xb") as stream:
        proc = subprocess.Popen(java, stdout=stream, stderr=stream, env=env, cwd=game)
        try:
            deadline = time.monotonic() + 300
            while not (ready := C.READY_RE.search(t := log.read_text(errors="replace"))):
                require(C.fatal(t) is None, str(C.fatal(t)))
                require(proc.poll() is None and time.monotonic() < deadline, "Client never reached a live world render")
                time.sleep(0.3)
            renderer = re.search(r"OpenGL Renderer: ([^\n]+)", t)
            require(renderer and lab.nvidia(renderer.group(1)), "Not the NVIDIA renderer")
            require("Using shaderpack: " + pack.name in t, "Iris did not select the pack")
            client_ready = time.monotonic()
            note("client-ready", renderer=renderer.group(1).strip())
            wait_for("READY", 120)
            time.sleep(max(0.0, client_ready + SETTLE - time.monotonic()))
            wid = window()
            require(wid is not None, "Minecraft window not found (or not unique) for our PID")
            subprocess.run(["xdotool", "windowfocus", "--sync", wid], env=env, check=True, timeout=4)
            keys = Keys(env, wid, proc.pid)
            require(keys.focused(), "Window focus/PID")
            title = subprocess.check_output(["xdotool", "getwindowname", wid], env=env, text=True).strip()
            require("Minecraft" in title, "Window title")
            note("window", wid=wid, title=title, pid=proc.pid)
            ff_wall = time.time()
            ffmpeg = subprocess.Popen(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "x11grab", "-draw_mouse", "0", "-framerate",
                 str(a.fps), "-window_id", wid, "-i", env["DISPLAY"], "-copyts", "-c:v", "libx264", "-preset",
                 "superfast", "-crf", "17", "-pix_fmt", "yuv420p", "-threads", "4", str(raw_video)],
                env=env, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
            )  # fmt: skip
            note("ffmpeg-start", pid=ffmpeg.pid)
            time.sleep(STORED_SECONDS)
            require(ffmpeg.poll() is None, "ffmpeg exited early")
            keys.tap("2")
            note("input", key="2", meaning="draw light from hotbar slot 2")
            wait_for("ROT", 15, "0")
            keys.press("w")
            note("input", key="w down")
            walk_start = w_at = progress_at = time.monotonic()
            stage_seen, last_jump, last_bank_nudge, done = 0, 0.0, 0.0, None
            # X11 may take several game ticks to answer under rendering load.
            # Keep the event reader responsive enough to release W at the river.
            focus_lost, stop_monitor = threading.Event(), threading.Event()
            def monitor_focus():
                while not stop_monitor.wait(0.15):
                    if not keys.focused():
                        focus_lost.set()
                        break
            threading.Thread(target=monitor_focus, daemon=True).start()
            while done is None:
                for kind, args, _ in poll():
                    if kind == "STOP":
                        keys.release("w")
                        note("input", key="w up", why="stop " + args[1])
                    elif kind == "END":
                        done = time.monotonic()
                    elif kind == "ROT" and args[1] == "cave":
                        time.sleep(CAVE_DWELL)
                        keys.press("w")
                        w_at = time.monotonic()
                        note("input", key="w down", why="leave cave")
                now = time.monotonic()
                require(now - walk_start < WALK_TIMEOUT, "Walk timeout")
                require(not focus_lost.is_set(), "Minecraft window lost focus")
                recent = [s for s in samples if s["wall"] >= time.time() - STALL_JUMP]
                moved = 1.0
                if len(recent) >= 5:
                    moved = math.hypot(recent[-1]["pos"][0] - recent[0]["pos"][0], recent[-1]["pos"][2] - recent[0]["pos"][2])
                if (samples and samples[-1]["stage"] != stage_seen) or moved >= 0.12:
                    stage_seen, progress_at = (samples[-1]["stage"] if samples else 0), now
                if samples and done is None and stage_seen == len(st) - 1 and not keys.down and now - last_bank_nudge > 0.7:
                    pose = samples[-1]
                    z = pose["pos"][2]
                    if pose["grounded"] and pose["stillTicks"] >= 8 and math.floor(z) != BANK[2]:
                        require(abs(z - BANK[2] - 0.5) < 1.8, "walked past riverbank")
                        key = "w" if z > BANK[2] + 0.5 else "s"
                        keys.press(key)
                        time.sleep(0.1)
                        keys.release(key)
                        note("input", key=key, why="settle on surveyed bank tile")
                        last_bank_nudge = now
                # W up (cave/bank stop) waits for the still-gated rotation; W down without progress -> jump, then abort.
                require(now - progress_at < STALL_FAIL, "Stalled at stage %d (no progress %.0f s)" % (stage_seen, STALL_FAIL))
                # Space taps >= 0.8 s apart: never a creative double-tap flight toggle (flight is also guarded).
                if "w" in keys.down and now - w_at > STALL_JUMP and moved < 0.12 and recent[-1]["grounded"] and now - last_jump > 0.8:
                    keys.press("space")
                    time.sleep(0.12)
                    keys.release("space")
                    last_jump = now
                    jumps.append(dict(wall=round(time.time(), 3), pos=recent[-1]["pos"], stage=stage_seen))
                    note("input", key="space", why="stall", pos=recent[-1]["pos"])
                time.sleep(0.02)
            stop_monitor.set()
            keys.release_all()
            while time.monotonic() < done + END_DWELL:
                poll()
                time.sleep(0.1)
            status = "finished"
        finally:
            if "stop_monitor" in locals():
                stop_monitor.set()
            if keys is not None:
                keys.release_all()
            if ffmpeg is not None and ffmpeg.poll() is None:
                try:
                    ffmpeg.communicate(b"q", timeout=20)
                except subprocess.TimeoutExpired:
                    ffmpeg.terminate()
                    ffmpeg.wait(timeout=10)
            wid = window() if proc is not None and proc.poll() is None else None
            if wid:
                subprocess.run(["/tmp/aqualumen-wm-close", hex(int(wid))], check=True, env=env)
            if proc is not None:
                try:
                    proc.wait(timeout=24)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    proc.wait(timeout=10)
            (out / "samples.jsonl").write_text("".join(json.dumps(s) + "\n" for s in samples))
            (out / "timeline.json").write_text(json.dumps(dict(status=status, timeline=timeline,
                                                               keys=keys.log if keys else [], stallJumps=jumps), indent=1))  # fmt: skip

    t = log.read_text(errors="replace")
    require(C.fatal(t) is None, str(C.fatal(t)))
    renderer = re.search(r"OpenGL Renderer: ([^\n]+)", t).group(1).strip()
    require(lab.nvidia(renderer) and "All dimensions are saved" in t, "Clean NVIDIA shutdown not logged")
    require(C.tree(src) == source_manifest, "SOURCE WORLD CHANGED")
    for n, h in originals.items():
        require(C.sha((orig / n).read_bytes()) == h, "Original Lab file changed: " + n)

    # Video: first frame wallclock (x11grab timestamps with -copyts) for sample alignment, then a
    # zero-based remux for viewing.
    first = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time",
                            "-read_intervals", "%+#1", "-of", "csv=p=0", str(raw_video)],
                           capture_output=True, text=True, check=True).stdout.split()  # fmt: skip
    t0 = float(first[0]) if first else None
    wallclock = t0 is not None and abs(t0 - ff_wall) < 5
    video = out / "walk.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-n", "-i", str(raw_video), "-c", "copy", "-movflags", "+faststart", str(video)], check=True)
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,nb_frames",
                                       "-of", "json", str(video)], capture_output=True, text=True, check=True).stdout)  # fmt: skip
    base = t0 if wallclock else ff_wall
    for s in samples:
        s["videoSeconds"] = round(s["wall"] - base, 3)
    (out / "samples.jsonl").write_text("".join(json.dumps(s) + "\n" for s in samples))
    turn_rots = len([s for s in st if s["kind"] != "stop"])
    summary, problems = validate(samples, [e[:2] + (0,) for e in events], cells, len(st), turn_rots)
    require(n_rot == turn_rots, "rotation count")
    (out / "complete.json").write_text(json.dumps(dict(
        status=status, problems=problems, movement=summary, renderer=renderer, pack=pack.name, sha256=pack_sha,
        normalModFiles=mods, recorderMod=False, variant=a.variant, light=a.light,
        world=dict(name=lab.WORLD, worldId=WORLD_ID, seed=SEED, sourceDigest=C.digest(source_manifest), sourceUnchanged=True),
        originalLabFilesUnchanged=sorted(originals), video=dict(file=video.name, sha256=C.sha(video.read_bytes()), probe=probe,
        alignment="x11grab wallclock pts" if wallclock else "ffmpeg spawn time (approx. +0.1..0.5 s)"),
        sampleObservationNote="sample wall times record the reader observation, not the exact rendered frame or server tick",
        teleports=dict(absolute=1, zeroTranslationRotations=n_rot + sum(e[0] == "LANE" for e in events), routeTurns=n_rot, laneCorrections=sum(e[0] == "LANE" for e in events)), stallJumps=len(jumps),
        limitations=["camera turns are server zero-translation rotations at corners, not mouse input",
                     "W/S/Space/2 are real XTest key events; server yaw corrections bring the walker back toward the surveyed lane"],
        scripts=script_hashes,
    ), indent=2))  # fmt: skip
    print("walk", status, json.dumps(summary), "problems:", problems or "none", flush=True)
    require(not problems, "Movement validation failed: %s" % problems)


if __name__ == "__main__":
    if sys.argv[1:] == ["--dry-run"]:
        dry_run()
    else:
        main(sys.argv[1:])
