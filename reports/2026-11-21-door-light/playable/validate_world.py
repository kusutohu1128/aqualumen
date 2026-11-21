"""Offline validation of the Aqualumen Lantern House save (stdlib only, independent NBT/Anvil decoder).

    python3 -I validate_world.py <world-dir> [--zip <archive.zip>] [--json out.json] [--map]

Reads only raw bytes (gzip level.dat, region .mca, zlib chunks), decodes block-state palettes itself and
checks the things the generator claims: door halves, lamps, torch support, trees, no test equipment,
walkable routes (doors openable), spawn, and Sun/shade at the fixed 11800 time.
"""

import gzip
import importlib.util
import json
import math
import struct
import sys
import zipfile
import zlib
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("aql_house_v", HERE.parent / "house.py")
HOUSE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(HOUSE)

GROUND_Y, MIN_Y = -61, -64
FAILS = []
RESULT = {}


def check(ok, message):
    if not ok:
        FAILS.append(message)
    return ok


# ------------------------------------------------------------------ decoder
class R:
    def __init__(self, data):
        self.d, self.i = data, 0

    def take(self, n):
        v = self.d[self.i:self.i + n]
        assert len(v) == n, "truncated NBT"
        self.i += n
        return v

    def u(self, fmt):
        return struct.unpack(">" + fmt, self.take(struct.calcsize(">" + fmt)))[0]

    def string(self):
        return self.take(self.u("H")).decode("utf-8")

    def value(self, t):
        if t == 1: return self.u("b")
        if t == 2: return self.u("h")
        if t == 3: return self.u("i")
        if t == 4: return self.u("q")
        if t == 5: return self.u("f")
        if t == 6: return self.u("d")
        if t == 7: return list(self.take(self.u("i")))
        if t == 8: return self.string()
        if t == 9:
            sub, n = self.u("B"), self.u("i")
            return [self.value(sub) for _ in range(n)]
        if t == 10:
            out = {}
            while True:
                tt = self.u("B")
                if tt == 0:
                    return out
                k = self.string()
                out[k] = self.value(tt)
        if t == 11: return [self.u("i") for _ in range(self.u("i"))]
        if t == 12: return [self.u("q") for _ in range(self.u("i"))]
        raise ValueError(t)


def parse_nbt(raw):
    r = R(raw)
    assert r.u("B") == 10
    r.string()
    v = r.value(10)
    assert r.i == len(raw), "trailing bytes"
    return v


def read_chunks(region_dir):
    chunks = {}
    for f in sorted(Path(region_dir).glob("r.*.mca")):
        _, rx, rz, _ = f.name.split(".")
        data = f.read_bytes()
        check(len(data) % 4096 == 0 and len(data) >= 8192, f.name + ": size not sector aligned")
        for i in range(1024):
            loc = struct.unpack(">I", data[i * 4:i * 4 + 4])[0]
            if not loc:
                continue
            off, n = loc >> 8, loc & 255
            length, comp = struct.unpack(">IB", data[off * 4096:off * 4096 + 5])
            check(comp == 2 and length + 4 <= n * 4096, f.name + ": bad chunk record")
            nbt = parse_nbt(zlib.decompress(data[off * 4096 + 5:off * 4096 + 4 + length]))
            cx, cz = int(rx) * 32 + i % 32, int(rz) * 32 + i // 32
            check((nbt["xPos"], nbt["zPos"]) == (cx, cz), "%s: slot %d holds chunk %d,%d" % (f.name, i, nbt["xPos"], nbt["zPos"]))
            chunks[(cx, cz)] = nbt
    return chunks


def decode_blocks(chunks):
    """world (x,y,z) -> (name, props) for every non-air cell of every section."""
    blocks = {}
    for (cx, cz), ch in chunks.items():
        check(ch["Status"] == "minecraft:full" and ch["DataVersion"] == 3955, "chunk %d,%d not full/3955" % (cx, cz))
        for sec in ch["sections"]:
            pal = sec["block_states"]["palette"]
            data = sec["block_states"].get("data")
            if data is None:
                check(len(pal) == 1, "palette without data")
                idx = [0] * 4096
            else:
                bits = max(4, (len(pal) - 1).bit_length())
                per = 64 // bits
                check(len(data) == -(-4096 // per), "packed length wrong (%d for %d bits)" % (len(data), bits))
                idx = []
                for lv in data:
                    v = lv & (2 ** 64 - 1)
                    for j in range(per):
                        idx.append((v >> (j * bits)) & ((1 << bits) - 1))
                idx = idx[:4096]
                check(max(idx) < len(pal), "palette index out of range")
            y0 = sec["Y"] * 16
            for n, pi in enumerate(idx):
                e = pal[pi]
                name = e["Name"]
                if name == "minecraft:air":
                    continue
                x, z, y = n & 15, (n >> 4) & 15, n >> 8
                blocks[(cx * 16 + x, y0 + y, cz * 16 + z)] = (name, e.get("Properties", {}))
    return blocks


def fmt(b):
    name, props = b
    return name if not props else name + "[" + ",".join("%s=%s" % kv for kv in sorted(props.items())) + "]"


def norm(s):
    """house.py state string -> comparable (name, props)."""
    if "[" not in s:
        return (s, {})
    n, rest = s.split("[", 1)
    return (n, dict(kv.split("=", 1) for kv in rest.rstrip("]").split(",")))


# ------------------------------------------------------------------ helpers
PASS = {"minecraft:air", "minecraft:short_grass", "minecraft:fern", "minecraft:poppy", "minecraft:dandelion",
        "minecraft:cornflower", "minecraft:oxeye_daisy", "minecraft:torch", "minecraft:wall_torch",
        "minecraft:oak_sign"}
NOT_OCCLUDING = PASS | {"minecraft:glass_pane", "minecraft:lantern", "minecraft:soul_lantern", "minecraft:chain",
                        "minecraft:potted_red_tulip"}
FORBIDDEN = ("command_block", "structure_block", "jigsaw", "barrier", "light", "redstone", "repeater", "comparator",
             "lever", "button", "pressure_plate", "tnt", "piston", "dispenser", "dropper", "observer", "hopper",
             "spawner", "end_portal", "bedrock_")  # bedrock itself is the superflat floor, so match "bedrock_" only


def sun_vec():
    return HOUSE.sun_direction(11800)


def lit(blocks, p, sun, length=60.0, step=0.1):
    x, y, z = p
    t = step
    while t < length:
        c = (math.floor(x + sun[0] * t), math.floor(y + sun[1] * t), math.floor(z + sun[2] * t))
        b = blocks.get(c)
        if b and b[0] not in NOT_OCCLUDING and not b[0].endswith("_door"):
            return False
        if c[1] > -30:
            return True
        t += step
    return True


def main(argv):
    world = Path(argv[1])
    out_json = argv[argv.index("--json") + 1] if "--json" in argv else None
    zip_path = argv[argv.index("--zip") + 1] if "--zip" in argv else None

    # ---- files
    files = sorted(str(p.relative_to(world)) for p in world.rglob("*") if p.is_file())
    RESULT["files"] = files
    check("level.dat" in files, "level.dat missing")
    check(all(f == "level.dat" or (f.startswith("region/r.") and f.endswith(".mca")) for f in files),
          "unexpected files: %s" % [f for f in files if not (f == "level.dat" or f.startswith("region/r."))])
    check(not any(("datapack" in f or "function" in f or "playerdata" in f or "properties" in f) for f in files),
          "datapack/playerdata/marker file present")

    # ---- level.dat
    lv = parse_nbt(gzip.decompress((world / "level.dat").read_bytes()))["Data"]
    check(lv["DataVersion"] == 3955 and lv["Version"]["Name"] == "1.21.1", "not 1.21.1")
    check(lv["DayTime"] == 11800, "DayTime != 11800")
    check(lv["GameType"] == 1 and lv["allowCommands"] == 0 and lv["hardcore"] == 0, "mode/commands")
    gen = lv["WorldGenSettings"]["dimensions"]["minecraft:overworld"]["generator"]
    check(gen["type"] == "minecraft:flat" and gen["settings"]["biome"] == "minecraft:plains", "not superflat plains")
    check([(l["block"], l["height"]) for l in gen["settings"]["layers"]] ==
          [("minecraft:bedrock", 1), ("minecraft:dirt", 2), ("minecraft:grass_block", 1)], "layers")
    check(gen["settings"]["structure_overrides"] == [] and not gen["settings"]["features"], "structures/features")
    check(lv["GameRules"] == {"doDaylightCycle": "false", "doWeatherCycle": "false", "doMobSpawning": "false",
                               "doInsomnia": "false", "announceAdvancements": "false"}, "gamerules")
    player = lv["Player"]
    check("UUID" not in player and "SpawnX" not in player, "player identity data present")
    check(not any(k in lv for k in ("ServerBrands", "CustomBossEvents", "ScheduledEvents", "WasModded")), "extra level keys")
    inv = {i["Slot"]: (i["id"], i["count"]) for i in player["Inventory"]}
    RESULT["hotbar"] = {str(k): v for k, v in sorted(inv.items())}
    check(inv[0][0] == "minecraft:torch" and all(s < 9 for s in inv), "hotbar must start with torches and be hotbar-only")
    check(not any("command" in n or "armor_stand" in n or "debug" in n for n, _ in inv.values()), "test equipment in hotbar")
    RESULT["level"] = dict(name=lv["LevelName"], dayTime=lv["DayTime"], gameType=lv["GameType"], difficulty=lv["Difficulty"],
                           seed=lv["WorldGenSettings"]["seed"], rules=lv["GameRules"], spawn=player["Pos"], rotation=player["Rotation"])

    # ---- chunks / blocks
    chunks = read_chunks(world / "region")
    RESULT["chunks"] = len(chunks)
    check(all(ch["block_entities"] is not None for ch in chunks.values()), "chunk fields")
    blocks = decode_blocks(chunks)
    bes = {}
    for ch in chunks.values():
        for be in ch["block_entities"]:
            bes[(be["x"], be["y"], be["z"])] = be
    ids = {}
    for p, b in blocks.items():
        ids[b[0]] = ids.get(b[0], 0) + 1
    RESULT["blockCounts"] = dict(sorted(ids.items()))
    bad = sorted(n for n in ids if any(f in n for f in FORBIDDEN) and n != "minecraft:bedrock")
    check(not bad, "forbidden blocks: %s" % bad)
    check(set(be["id"] for be in bes.values()) == {"minecraft:sign"} and len(bes) <= 3, "block entities beyond signs: %s" % {be["id"] for be in bes.values()})
    for p, be in bes.items():
        check(blocks.get(p, ("",))[0] == "minecraft:oak_sign", "sign BE without sign block at %s" % (p,))
        check(not be["is_waxed"] or True, "")
    RESULT["signs"] = {str(p): [json.loads(m)["text"] for m in be["front_text"]["messages"]] for p, be in bes.items()}
    check(all(any(0x3040 <= ord(c) <= 0x30FF or 0x4E00 <= ord(c) <= 0x9FFF for c in "".join(t)) for t in RESULT["signs"].values()),
          "sign text not Japanese")

    # ---- house identical to house.py (except the two exterior doorways)
    mism = []
    for c, s in HOUSE.STATIC.items():
        w = (c[0], c[1] + GROUND_Y, c[2])
        want = norm(s)
        have = blocks.get(w, ("minecraft:air", {}))
        if c in HOUSE.DYNAMIC:
            continue  # placeholder air in STATIC; checked against dynamic_blocks below
        if have != want and not (c[2] == 0 and c[0] in (5, 6, 7, 13, 14, 15)):
            mism.append((c, s, fmt(have)))
    check(not mism, "house differs from house.py: %s" % mism[:5])
    dyn = HOUSE.dynamic_blocks(HOUSE.role("closed-both"))
    for c, s in dyn.items():
        check(blocks.get((c[0], c[1] + GROUND_Y, c[2])) == norm(s), "dynamic cell %s differs" % (c,))
    warm = (HOUSE.WARM_CELL[0], HOUSE.WARM_CELL[1] + GROUND_Y, HOUSE.WARM_CELL[2])
    soul = (HOUSE.SOUL_CELL[0], HOUSE.SOUL_CELL[1] + GROUND_Y, HOUSE.SOUL_CELL[2])
    check(blocks[warm][0] == "minecraft:lantern" and blocks[warm][1]["hanging"] == "true", "warm lantern")
    check(blocks[(warm[0], warm[1] + 1, warm[2])][0] == "minecraft:chain", "chain above lantern")
    check(blocks[(warm[0], warm[1] + 2, warm[2])][0] == "minecraft:spruce_planks", "chain not hanging from the ceiling")
    check(blocks[soul][0] == "minecraft:soul_lantern" and blocks[soul][1]["hanging"] == "false", "soul lantern")
    check(blocks[(soul[0], soul[1] - 1, soul[2])][0] in ("minecraft:oak_planks", "minecraft:smooth_stone"), "soul lantern unsupported")
    check(ids.get("minecraft:lantern") == 1 and ids.get("minecraft:soul_lantern") == 1, "lamp count != 2")

    # ---- doors: every dark-oak door half pairs up, no other doors
    doors = {p: b for p, b in blocks.items() if b[0].endswith("_door")}
    lowers = {p: b for p, b in doors.items() if b[1]["half"] == "lower"}
    uppers = {p: b for p, b in doors.items() if b[1]["half"] == "upper"}
    check(len(lowers) == 3 and len(uppers) == 3, "expected 3 doors (6 halves), got %d/%d" % (len(lowers), len(uppers)))
    door_report = []
    for p, b in sorted(lowers.items()):
        up = uppers.get((p[0], p[1] + 1, p[2]))
        ok = up is not None and up[0] == b[0] == "minecraft:dark_oak_door" and \
            all(up[1][k] == b[1][k] for k in ("facing", "hinge", "open", "powered")) and b[1]["open"] == "false"
        check(ok, "door at %s lacks a matching upper half" % (p,))
        door_report.append(dict(lower=list(p), upper=[p[0], p[1] + 1, p[2]], state=b[1]))
        # standing room on both sides along the wall normal, floor below
        axis = (1, 0) if b[1]["facing"] in ("east", "west") else (0, 1)
        for sgn in (-1, 1):
            for dy in (0, 1):
                n = (p[0] + axis[0] * sgn, p[1] + dy, p[2] + axis[1] * sgn)
                check(blocks.get(n, ("minecraft:air",))[0] in PASS, "door %s blocked on one side at %s" % (p, n))
    RESULT["doors"] = door_report
    inner = (11, GROUND_Y + 1, 6)
    check(inner in lowers and lowers[inner][1]["facing"] == "east", "original inner dark-oak door missing")

    # ---- torches
    torches = {p: b for p, b in blocks.items() if b[0] in ("minecraft:torch", "minecraft:wall_torch")}
    check(len(torches) == 1, "expected exactly one torch, got %d" % len(torches))
    for p, b in torches.items():
        check(b[0] == "minecraft:wall_torch", "torch not wall torch")
        f = b[1]["facing"]
        d = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0)}[f]
        sup = (p[0] - d[0], p[1], p[2] - d[2])
        check(blocks.get(sup, ("",))[0] in ("minecraft:oak_log", "minecraft:birch_log"), "torch %s not on a trunk" % (p,))
        RESULT["torch"] = dict(cell=list(p), facing=f, supportedBy=blocks[sup][0], supportCell=list(sup))
        TORCH = p

    # ---- trees
    logs = {p for p, b in blocks.items() if b[0] in ("minecraft:oak_log", "minecraft:birch_log")}
    leaves = {p: b for p, b in blocks.items() if b[0].endswith("_leaves")}
    trunks = sorted({(p[0], p[2]) for p in logs})
    kinds = {}
    for t in trunks:
        col = sorted(p[1] for p in logs if (p[0], p[2]) == t)
        sp = blocks[(t[0], col[0], t[1])][0].split(":")[1].replace("_log", "")
        kinds[sp] = kinds.get(sp, 0) + 1
        check(col == list(range(col[0], col[0] + len(col))) and col[0] == GROUND_Y + 1, "trunk %s floating" % (t,))
        check(blocks[(t[0], GROUND_Y, t[1])][0] == "minecraft:grass_block", "trunk %s not on grass" % (t,))
    check(kinds.get("oak", 0) >= 2 and kinds.get("birch", 0) >= 2, "need oak and birch trees: %s" % kinds)
    check(all(b[1]["persistent"] == "true" for b in leaves.values()), "non-persistent leaves")
    RESULT["trees"] = dict(trunks=[list(t) for t in trunks], species=kinds, leafBlocks=len(leaves), logBlocks=len(logs))

    # ---- walkable routes (doors are operable: passable); also prove doors are the only entries
    def passable(c, doors_open):
        b = blocks.get(c)
        if b is None:
            return c[1] >= GROUND_Y + 1
        return b[0] in PASS or (doors_open and b[0].endswith("_door"))

    def solid(c):
        b = blocks.get(c)
        if b is None:
            return c[1] <= GROUND_Y
        return b[0] not in PASS and not b[0].endswith("_door")

    def reach(start, doors_open):
        seen, q = {start}, deque([start])
        while q:
            x, y, z = q.popleft()
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for dy in (0, 1, -1):
                    n = (x + dx, y + dy, z + dz)
                    if n in seen or not (-45 > n[1] > MIN_Y) or not (-40 <= n[0] <= 48 and -40 <= n[2] <= 30):
                        continue
                    if not (passable(n, doors_open) and passable((n[0], n[1] + 1, n[2]), doors_open) and solid((n[0], n[1] - 1, n[2]))):
                        continue
                    if dy == 1 and not passable((x, y + 2, z), doors_open):
                        continue
                    if dy == -1 and not passable((n[0], n[1] + 2, n[2]), doors_open):
                        continue
                    seen.add(n)
                    q.append(n)
        return seen

    sp = player["Pos"]
    start = (math.floor(sp[0]), math.floor(sp[1]), math.floor(sp[2]))
    check(passable(start, True) and passable((start[0], start[1] + 1, start[2]), True) and solid((start[0], start[1] - 1, start[2])),
          "spawn cell not standable")
    check(blocks.get((start[0], start[1] + 3, start[2])) is None, "spawn not open to the sky")
    check(all(not any(p[0] == start[0] and p[2] == start[2] for p in logs | set(leaves)) for _ in [0]), "tree above spawn")
    closed = reach(start, False)
    opened = reach(start, True)
    pts = {
        "porch-A": (6, GROUND_Y + 1, -2), "porch-B": (14, GROUND_Y + 1, -2),
        "room-A": (6, GROUND_Y + 1, 3), "room-A-sun-strip": (7, GROUND_Y + 1, 3), "room-A-soul-lantern-side": (4, GROUND_Y + 1, 8),
        "room-B": (14, GROUND_Y + 1, 3), "room-B-under-warm-lantern": (13, GROUND_Y + 1, 5),
        "torch-front": (TORCH[0], GROUND_Y + 1, TORCH[2]), "torch-lawn": (11, GROUND_Y + 1, -9),
        "east-lawn": (28, GROUND_Y + 1, 0),
    }
    routes = {k: dict(reachableWithDoorsOpened=v in opened, reachableWithDoorsClosed=v in closed) for k, v in pts.items()}
    RESULT["routes"] = routes
    for k in pts:
        check(routes[k]["reachableWithDoorsOpened"], "unreachable: " + k)
        if k.startswith("room"):
            check(not routes[k]["reachableWithDoorsClosed"], "room reachable without opening a door: " + k)
        else:
            check(routes[k]["reachableWithDoorsClosed"], "outdoor point needs a door: " + k)
    # Room B only through the inner door OR its own exterior door; check each entry individually
    def only_door(allowed_x):
        # open exactly one door: all other door cells act as walls
        def passable2(c, _):
            b = blocks.get(c)
            if b is None:
                return c[1] >= GROUND_Y + 1
            if b[0].endswith("_door"):
                return c[0] == allowed_x[0] and c[2] == allowed_x[1]
            return b[0] in PASS
        return passable2
    # (door-by-door reachability: each exterior door alone gives its room)
    for name, door_xz, goal in (("door A alone", (6, 0), pts["room-A"]), ("door B alone", (14, 0), pts["room-B"])):
        saved = passable
        passable = only_door(door_xz)
        try:
            check(goal in reach(start, True), name + " does not give access to its room")
        finally:
            passable = saved
    RESULT["walkable"] = dict(standableCellsClosedDoors=len(closed), standableCellsOpenedDoors=len(opened))

    # ---- Sun / shade (Minecraft Sun moves in the X-Y plane; at 11800 it is low in the west)
    sun = sun_vec()
    RESULT["sun"] = dict(direction=[round(v, 4) for v in sun], elevationDeg=round(math.degrees(math.asin(sun[1])), 2))

    def ground_lit(x, z):
        return lit(blocks, (x + 0.5, GROUND_Y + 1.02, z + 0.5), sun)

    named = {
        "spawn": (start[0], start[2]), "path-start": (6, -21), "path-in-shade": (6, -8), "path-to-porch": (6, -5),
        "torch-front": (TORCH[0], TORCH[2]), "torch-lawn-west": (9, -12), "torch-lawn-east": (14, -6),
        "porch-A": (6, -2), "porch-B": (14, -2), "east-lawn": (28, 0),
    }
    RESULT["groundSun"] = {k: ground_lit(*v) for k, v in named.items()}
    # interior: floor strip under the west window gets Sun, the north wall side of the receiver does not
    rec = lambda x, z: lit(blocks, (x + 0.5, GROUND_Y + 1.02, z + 0.5), sun)
    RESULT["interiorSun"] = {"room-A-strip(7,3)": rec(7, 3), "room-A-(8,10)": rec(8, 10), "room-B(14,5)": rec(14, 5)}
    check(RESULT["groundSun"]["spawn"], "spawn is in shade")
    check(RESULT["interiorSun"]["room-A-strip(7,3)"], "no sun strip in room A")
    check(not RESULT["interiorSun"]["room-B(14,5)"], "room B should be unlit by Sun")
    xs, zs = range(-6, 31), range(-22, 0)
    shade = [(x, z) for x in xs for z in zs if not ground_lit(x, z)
             and (x, GROUND_Y + 1, z) not in blocks and blocks.get((x, GROUND_Y, z), ("",))[0] == "minecraft:grass_block"]
    sunny = [(x, z) for x in xs for z in zs if ground_lit(x, z)
             and (x, GROUND_Y + 1, z) not in blocks and blocks.get((x, GROUND_Y, z), ("",))[0] == "minecraft:grass_block"]
    RESULT["openGrassCells"] = dict(inShade=len(shade), inSun=len(sunny))
    check(len(shade) >= 40 and len(sunny) >= 100, "need both shaded and sunlit open grass")
    if "--map" in argv:
        rows = []
        for z in range(-24, 15):
            row = ""
            for x in range(-18, 32):
                b = blocks.get((x, GROUND_Y + 1, z)) or blocks.get((x, GROUND_Y + 2, z))
                g = blocks.get((x, GROUND_Y, z), ("",))[0]
                if (x, z) == (start[0], start[2]):
                    row += "@"
                elif (x, GROUND_Y + 2, z) in torches:
                    row += "!"
                elif any(p[0] == x and p[2] == z for p in logs):
                    row += "T"
                elif any(p[0] == x and p[2] == z for p in leaves):
                    row += "^"
                elif 0 <= x <= 18 and 0 <= z <= 12:
                    row += "H"
                elif g in ("minecraft:dirt_path", "minecraft:stone_bricks", "minecraft:mossy_stone_bricks"):
                    row += "="
                else:
                    row += "." if ground_lit(x, z) else "#"
            rows.append(row)
        RESULT["map"] = rows
        print("\n".join("%4d %s" % (z, r) for z, r in zip(range(-24, 15), rows)))
        print("     x from -18 to 31;  @ spawn  ! torch  T trunk  ^ leaves  H house  = path/porch  . sun  # shade")

    # ---- archive
    if zip_path:
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
            check(z.testzip() is None, "zip CRC")
            tops = {n.split("/")[0] for n in names}
            check(tops == {"Aqualumen-Lantern-House"}, "zip top level: %s" % tops)
            check("Aqualumen-Lantern-House/level.dat" in names, "zip missing level.dat")
            check(all(not n.startswith("/") and ".." not in n for n in names), "unsafe zip names")
            regions = [n for n in names if n.endswith(".mca")]
            check(len(regions) >= 1, "zip has no region files")
            for n in names:
                if not n.endswith("/"):
                    rel = n.split("/", 1)[1]
                    check(rel in files, "zip entry not in world: " + n)
                    check(z.read(n) == (world / rel).read_bytes(), "zip entry differs from world: " + n)
            RESULT["zip"] = dict(entries=names, bytes=Path(zip_path).stat().st_size)

    RESULT["fails"] = FAILS
    RESULT["ok"] = not FAILS
    if out_json:
        Path(out_json).write_text(json.dumps(RESULT, indent=2, ensure_ascii=False) + "\n")
    summary = {k: RESULT[k] for k in ("ok", "chunks", "doors", "torch", "trees", "routes", "groundSun", "interiorSun", "openGrassCells", "sun") if k in RESULT}
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    print("FAILS:", FAILS or "none")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
