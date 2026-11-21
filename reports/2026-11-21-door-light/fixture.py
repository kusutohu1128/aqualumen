"""World-local datapack for the door-light house (pure; no world access).

Handshake (same protocol as the indirect-light runner, prefix AQD_):
  BEGIN -> set dynamic cells (door halves, both lamps) and the cow -> teleport ->
  after CHECK ticks verify every reserved cell with its exact block state, the house entity
  census (exactly one tagged NoAI cow at its feet position in cow roles, otherwise none) and the
  player pose -> READY / FAIL -> re-verify every 10 ticks, DRIFT on change.
"""

import json
import re

import house as H

NS = "aqd"
PACK_NAME = "DoorLight"
EVENT_RE = re.compile(r"\[Server\] AQD_(READY|FAIL|DRIFT|BEGIN|ABORT|BUILT)_([a-z0-9-]+)_END")
ERROR_RE = re.compile(r"\[Render thread/ERROR\]|/ERROR\].*(aqd:|function|DoorLight)")
COW_TAG = "aqd_cow"
COW = "@e[type=minecraft:cow,tag=%s]" % COW_TAG


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def w(p):
    return " ".join(str(v) for v in H.world(p))


def wf(p):
    return " ".join(H.fmt(v) for v in H.world(p))


def count(cell, block):
    return "execute if block %s %s run scoreboard players add #n %s 1" % (w(cell), block, NS)


def census():
    lo, hi = H.HOUSE_INTERIOR
    return "execute store result score #e %s positioned %s if entity @e[type=!minecraft:player,dx=%d,dy=%d,dz=%d]" % (
        NS, w(lo), hi[0] - lo[0] - 1, hi[1] - lo[1] - 1, hi[2] - lo[2] - 1,
    )


def set_dynamic(r):
    """Door: clear upper (the lower half follows by shape update), clear lower, then place lower,
    then upper. Lamps: plain setblock (chain above the hanging lantern is static)."""
    d = H.dynamic_blocks(r)
    out = [
        "setblock %s %s" % (w(H.DOOR_UPPER), H.AIR),
        "setblock %s %s" % (w(H.DOOR_LOWER), H.AIR),
    ]
    if d[H.DOOR_LOWER] != H.AIR:
        out += [
            "setblock %s %s" % (w(H.DOOR_LOWER), d[H.DOOR_LOWER]),
            "setblock %s %s" % (w(H.DOOR_UPPER), d[H.DOOR_UPPER]),
        ]
    out += [
        "setblock %s %s" % (w(H.WARM_CELL), d[H.WARM_CELL]),
        "setblock %s %s" % (w(H.SOUL_CELL), d[H.SOUL_CELL]),
    ]
    return out


def cow_commands(r):
    if not r["cow"]:
        return ["kill %s" % COW]
    xyz = wf(H.COW_FEET)
    return [
        'execute unless entity %s run summon minecraft:cow %s {Tags:["%s"],NoAI:1b,Silent:1b,Invulnerable:1b,'
        "PersistenceRequired:1b,Rotation:[90f,0f]}" % (COW, xyz, COW_TAG),
        "tp %s %s 90 0" % (COW, xyz),
    ]


def datapack(roles, C):
    """{relative path: text}. C is the imported indirect-light capture module (tp/pose_selector)."""
    lo_w, hi_w = H.world(H.LO), H.world(H.HI)
    files = {
        "pack.mcmeta": json.dumps({"pack": {"pack_format": 48, "description": "Private Aqualumen door-light house"}}),
        "data/minecraft/tags/function/tick.json": json.dumps({"values": [NS + ":tick"]}),
    }
    fn = {}
    first = H.role(roles[0])
    fn["tick"] = ["execute as @a[name=%s,tag=!aqd_started] run function %s:start" % (H.PLAYER, NS)]
    fn["start"] = [
        "tag @s add aqd_started",
        "gamerule doDaylightCycle false",
        "gamerule doWeatherCycle false",
        "gamerule doMobSpawning false",
        "gamerule doMobLoot false",
        "gamerule doEntityDrops false",
        "gamerule doTileDrops false",  # a door half removed by shape update would otherwise drop
        "gamerule randomTickSpeed 0",
        "gamerule doFireTick false",
        "gamerule sendCommandFeedback false",
        "gamerule commandBlockOutput false",
        "gamerule announceAdvancements false",
        "difficulty peaceful",
        "weather clear",
        "time set %d" % H.TIME,
        "gamemode spectator @s",
        "scoreboard objectives add %s dummy" % NS,
        "scoreboard players set #attempt %s 0" % NS,
        "scoreboard players set #built %s 0" % NS,
        "forceload add %d %d %d %d" % (lo_w[0], lo_w[2], hi_w[0], hi_w[2]),
        C.tp(H.POSES[first["pose"]]),
        "schedule function %s:setup 20t replace" % NS,
    ]
    corners = [(x, lo_w[1], z) for x in (lo_w[0], hi_w[0]) for z in (lo_w[2], hi_w[2])]
    loaded = " ".join("if loaded %d %d %d" % c for c in corners)
    fn["setup"] = [
        "scoreboard players add #attempt %s 1" % NS,
        "scoreboard players set #loaded %s 0" % NS,
        "execute %s run scoreboard players set #loaded %s 1" % (loaded, NS),
        "execute if score #loaded %s matches 0 if score #attempt %s matches ..60 run schedule function %s:setup 20t replace" % (NS, NS, NS),
        "execute if score #loaded %s matches 0 if score #attempt %s matches 61.. run say AQD_ABORT_unloaded_END" % (NS, NS),
        "execute if score #loaded %s matches 1 if score #built %s matches 0 run function %s:reserve" % (NS, NS, NS),
    ]
    grid0 = H.cells(first)
    # Positive AIR count over the whole reserve + no entities in it before any write.
    reserve = ["scoreboard players set #n %s 0" % NS]
    reserve += [count(c, H.AIR) for c in sorted(grid0)]
    reserve += [
        census(),
        "execute if score #n %s matches %d if score #e %s matches 0 run function %s:build" % (NS, H.CELLS, NS, NS),
        "execute unless score #n %s matches %d run say AQD_ABORT_reserved_END" % (NS, H.CELLS),
        "execute unless score #e %s matches 0 run say AQD_ABORT_entities_END" % NS,
    ]
    fn["reserve"] = reserve
    build = ["scoreboard players set #built %s 1" % NS]
    # Static cells in a deterministic order: solids bottom-up (posts/walls before panes, chain after ceiling).
    order = sorted((c for c, b in H.STATIC.items() if b != H.AIR), key=lambda c: (c[1], "glass_pane" in H.STATIC[c], c))
    build += ["setblock %s %s" % (w(c), H.STATIC[c]) for c in order]
    build += ["say AQD_BUILT_house_END", "schedule function %s:s0 20t replace" % NS]
    fn["build"] = build
    dyn = set(H.DYNAMIC)
    fn["vstatic"] = [count(c, b) for c, b in sorted(grid0.items()) if c not in dyn]
    n = len(roles)
    for i, name in enumerate(roles):
        r = H.role(name)
        pose = H.POSES[r["pose"]]
        grid = H.cells(r)
        assert all(grid[c] == b for c, b in grid0.items() if c not in dyn)
        scene = ["schedule clear %s:h%d" % (NS, j) for j in range(n)]
        scene += ["say AQD_BEGIN_%s_END" % name, "time set %d" % H.TIME, "weather clear"]
        scene += set_dynamic(r) + cow_commands(r)
        scene += [
            C.tp(pose),
            "schedule function %s:c%d %dt replace" % (NS, i, C.CHECK),
            "schedule function %s:s%d %dt replace" % (NS, (i + 1) % n, C.PERIOD),
        ]
        fn["s%d" % i] = scene
        want_e = 1 if r["cow"] else 0
        cow_ok = (
            " positioned %s if entity @e[type=minecraft:cow,tag=%s,distance=..0.02,limit=1,y_rotation=89.95..90.05]"
            % (wf(H.COW_FEET), COW_TAG)
            if r["cow"]
            else ""
        )
        fn["v%d" % i] = (
            ["scoreboard players set #n %s 0" % NS, "scoreboard players set #ok %s 0" % NS, "function %s:vstatic" % NS]
            + [count(c, grid[c]) for c in sorted(dyn)]
            + [
                census(),
                "execute if score #n %s matches %d if score #e %s matches %d%s positioned %s if entity %s run scoreboard players set #ok %s 1"
                % (NS, H.CELLS, NS, want_e, cow_ok, " ".join(H.fmt(v) for v in H.feet(pose)), C.pose_selector(pose), NS),
            ]
        )
        fn["c%d" % i] = [
            "function %s:v%d" % (NS, i),
            "execute if score #ok %s matches 1 run say AQD_READY_%s_END" % (NS, name),
            "execute if score #ok %s matches 0 run say AQD_FAIL_%s_END" % (NS, name),
            "schedule function %s:h%d 10t replace" % (NS, i),
        ]
        fn["h%d" % i] = [
            "function %s:v%d" % (NS, i),
            "execute if score #ok %s matches 0 run say AQD_DRIFT_%s_END" % (NS, name),
            "schedule function %s:h%d 10t replace" % (NS, i),
        ]
    assert C.CHECK + 10 < C.PERIOD
    for k, lines in fn.items():
        files["data/%s/function/%s.mcfunction" % (NS, k)] = "\n".join(lines) + "\n"
    return files


def check_datapack(files, roles):
    lo_w, hi_w = H.world(H.LO), H.world(H.HI)
    coord = re.compile(r"(?:block|fill|setblock|loaded|summon minecraft:cow|positioned|tp \S+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)")
    for path, text in files.items():
        for line in text.splitlines():
            for m in coord.finditer(line):
                x, y, z = map(float, m.groups())
                require(lo_w[0] <= x <= hi_w[0] + 1 and lo_w[1] <= y <= hi_w[1] + 1 and lo_w[2] <= z <= hi_w[2] + 1,
                        "Command outside the reserved volume: " + line)
    fdir = "data/%s/function/" % NS
    reserve = files[fdir + "reserve.mcfunction"].splitlines()
    require(sum("minecraft:air run" in l for l in reserve) == H.CELLS, "reserve does not cover every cell")
    static = files[fdir + "vstatic.mcfunction"].splitlines()
    for i, name in enumerate(roles):
        v = files[fdir + "v%d.mcfunction" % i].splitlines()
        require(len(static) + sum(l.startswith("execute if block") for l in v) == H.CELLS, name)
        require("AQD_READY_%s_END" % name in files[fdir + "c%d.mcfunction" % i], name)
    for k in ("reserve", "build"):
        require("tp " not in files[fdir + k + ".mcfunction"], "setup teleports")
    for path, text in files.items():
        nm = path.rsplit("/", 1)[-1]
        if re.search(r"^(fill|setblock|summon|kill) ", text, re.M) or "run summon" in text:
            require(nm == "build.mcfunction" or re.fullmatch(r"s\d+\.mcfunction", nm), path)
    require(all("kill @e[type=minecraft:cow,tag=%s]" % COW_TAG == l for t in files.values() for l in t.splitlines() if l.startswith("kill")),
            "kill must target only the tagged fixture cow")


def door_update(grid, cell, block):
    """Minimal vanilla door shape-update model for setblock: removing one half turns the
    other half to air; placing an upper half over a matching lower copies its properties."""
    grid[cell] = block
    x, y, z = cell
    for other, half in (((x, y + 1, z), "lower"), ((x, y - 1, z), "upper")):
        ob = grid.get(other, H.AIR)
        if "_door[" in ob and ("half=%s" % half) in ob and "_door[" not in block:
            grid[other] = H.AIR
    if "_door[" in block and "half=upper" in block:
        below = (x, y - 1, z)
        lb = grid.get(below, H.AIR)
        if "_door[" in lb:
            grid[below] = block.replace("half=upper", "half=lower")


def simulate(files, roles, C, cycles=2):
    fdir = "data/%s/function/" % NS
    grid = {H.world(c): H.AIR for c in H.cells(H.role(roles[0]))}
    num = r"(-?[\d.]+)"
    set_re = re.compile(r"^setblock (-?\d+) (-?\d+) (-?\d+) (\S+)$")
    tp_re = re.compile(r"^tp %s %s %s %s %s %s$" % (H.PLAYER, num, num, num, num, num))
    count_re = re.compile(r"^execute if block (-?\d+) (-?\d+) (-?\d+) (\S+) run scoreboard")
    state = dict(player=None, cow=None)

    def run(name):
        for line in files[fdir + name + ".mcfunction"].splitlines():
            if m := set_re.match(line):
                c = tuple(map(int, m.groups()[:3]))
                require(c in grid, "setblock outside fixture")
                door_update(grid, c, m.group(4))
            elif m := tp_re.match(line):
                state["player"] = tuple(map(float, m.groups()))
            elif line.startswith("kill "):
                state["cow"] = None
            elif "run summon minecraft:cow" in line and state["cow"] is None:
                state["cow"] = "summoned"
            elif line.startswith("tp @e[type=minecraft:cow"):
                require(state["cow"] is not None, "teleporting a missing cow")
                state["cow"] = tuple(map(float, line.split()[2:5]))

    run("build")
    built = {H.world(c): (H.AIR if c in H.DYNAMIC else b) for c, b in H.cells(H.role(roles[0])).items()}
    require(grid == built, "build does not produce the static house with empty dynamic cells")
    for _ in range(cycles):
        for i, name in enumerate(roles):
            run("s%d" % i)
            r = H.role(name)
            want = {H.world(c): b for c, b in H.cells(r).items()}
            bad = [c for c in grid if grid[c] != want[c]]
            require(not bad, "%s: simulated cells differ, e.g. %s" % (name, [(c, grid[c], want[c]) for c in bad[:3]]))
            pose = H.POSES[r["pose"]]
            p = state["player"]
            require(p is not None and max(abs(a - b) for a, b in zip(p[:3], H.feet(pose))) < 1e-9
                    and (p[3], p[4]) == (pose["yaw"], pose["pitch"]), name + ": teleport pose")
            require((state["cow"] == H.world(H.COW_FEET)) if r["cow"] else state["cow"] is None, name + ": cow")
            lines = files[fdir + "vstatic.mcfunction"].splitlines() + files[fdir + "v%d.mcfunction" % i].splitlines()
            hits = [m for m in map(count_re.match, lines) if m]
            require(len(hits) == H.CELLS and len({tuple(map(int, m.groups()[:3])) for m in hits}) == H.CELLS, name + ": count")
            require(all(grid[tuple(map(int, m.groups()[:3]))] == m.group(4) for m in hits),
                    name + ": verification expects a different block than the scene builds")
    return True


def plan(roles, C):
    rows = []
    for name in roles:
        r = H.role(name)
        row = dict(r, blocks={"%s" % (list(H.world(c)),): b for c, b in H.dynamic_blocks(r).items()},
                   cowFeetWorld=list(H.world(H.COW_FEET)) if r["cow"] else None,
                   camera=H.pose_record(r["pose"]), lightPaths=H.light_paths(r))
        if r["pose"] == "main":
            row["samples"] = H.samples(r)
        rows.append(row)
    return dict(
        fixture="reports/2026-11-21-door-light/house.py + fixture.py",
        origin=H.ORIGIN,
        reservedCells=dict(local=[H.LO, H.HI], world=[H.world(H.LO), H.world(H.HI)], count=H.CELLS),
        time=H.TIME,
        sunDirection=[round(v, 4) for v in H.sun_direction()],
        lamps=dict(warm=dict(cell=list(H.world(H.WARM_CELL)), block=H.WARM, chain=list(H.world(H.CHAIN_CELL))),
                   soul=dict(cell=list(H.world(H.SOUL_CELL)), block=H.SOUL)),
        door=dict(lower=list(H.world(H.DOOR_LOWER)), upper=list(H.world(H.DOOR_UPPER)), states=H.DOORS),
        receivers=[dict(name=n, local=list(p), world=list(H.world(p)), block=b) for n, p, b in H.RECEIVERS],
        sampleMethod=(
            "vertical fov %d, %dx%d, fovEffectScale 0, bobView off, spectator eye = feet + %.2f; patch [x0,y0,x1,y1) "
            "%dx%d; corners + centre ray first-hit the named receiver block in every main role, with every non-air "
            "cell (and a conservative cow box) treated as a full occluder" % (H.FOV, H.WIDTH, H.HEIGHT, H.EYE, H.PATCH, H.PATCH)
        ),
        timing=dict(periodTicks=C.PERIOD, checkTicks=C.CHECK, settleSeconds=C.SETTLE, dwellSeconds=C.DWELL, pairSeconds=C.PAIR),
        roles=rows,
    )
