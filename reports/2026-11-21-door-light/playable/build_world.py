"""Offline generator for the standalone "Aqualumen Lantern House" Minecraft Java 1.21.1 save.

stdlib only.  Writes a fresh superflat (plains) world: level.dat + Anvil region files with the
two-room sunset house from ../house.py (same dark-oak door, same two lamps), exterior doors,
a porch, a path and a few real oak/birch trees with one wall torch.  No datapack, no command
block, no marker file, no player UUID, nothing copied from any existing save.

    python3 -I build_world.py <output-dir>      # creates <output-dir>/Aqualumen-Lantern-House
"""

import datetime
import gzip
import importlib.util
import io
import random
import struct
import sys
import zlib
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORLD_NAME = "Aqualumen-Lantern-House"
LEVEL_NAME = "Aqualumen Lantern House"
DATA_VERSION = 3955  # Minecraft 1.21.1
SEED = 2026112101
GROUND_Y = -61  # top grass layer (superflat: bedrock -64, dirt -63..-62, grass -61)
MIN_Y = -64
ORIGIN = (0, GROUND_Y, 0)  # house local (x, y, z) -> world; local y=0 is the grass layer
TIME = 11800
LAST_PLAYED_MS = int(datetime.datetime(2026, 11, 21, 4, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=9))).timestamp() * 1000)

_spec = importlib.util.spec_from_file_location("aql_house", HERE.parent / "house.py")
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)

# --------------------------------------------------------------------------- NBT writer
T_BYTE, T_SHORT, T_INT, T_LONG, T_FLOAT, T_DOUBLE, T_BYTES, T_STRING, T_LIST, T_COMPOUND, T_INTS, T_LONGS = range(1, 13)


def _s(v):
    assert "\0" not in v and all(ord(c) < 0x10000 for c in v)  # BMP only: same bytes as Java modified UTF-8
    raw = v.encode("utf-8")
    return struct.pack(">H", len(raw)) + raw


def _payload(t, v):
    if t == T_BYTE:
        return struct.pack(">b", v)
    if t == T_SHORT:
        return struct.pack(">h", v)
    if t == T_INT:
        return struct.pack(">i", v)
    if t == T_LONG:
        return struct.pack(">q", v)
    if t == T_FLOAT:
        return struct.pack(">f", v)
    if t == T_DOUBLE:
        return struct.pack(">d", v)
    if t == T_STRING:
        return _s(v)
    if t == T_LONGS:
        return struct.pack(">i", len(v)) + b"".join(struct.pack(">q", x) for x in v)
    if t == T_LIST:
        sub, items = v
        return bytes([sub]) + struct.pack(">i", len(items)) + b"".join(_payload(sub, x) for x in items)
    if t == T_COMPOUND:
        return b"".join(bytes([tt]) + _s(k) + _payload(tt, vv) for k, (tt, vv) in v.items()) + b"\0"
    raise ValueError(t)


def nbt_bytes(root):
    return b"\x0a" + _s("") + _payload(T_COMPOUND, root)


S = lambda x: (T_STRING, x)
I = lambda x: (T_INT, x)
SH = lambda x: (T_SHORT, x)
B = lambda x: (T_BYTE, int(x))
F = lambda x: (T_FLOAT, x)
D = lambda x: (T_DOUBLE, x)
LG = lambda x: (T_LONG, x)
C = lambda x: (T_COMPOUND, x)
L = lambda t, x: (T_LIST, (t, [i[1] for i in x] if t == T_COMPOUND else list(x)))
EMPTY_LIST = (T_LIST, (T_BYTE, []))


# --------------------------------------------------------------------------- block grid
def parse_state(text):
    if "[" not in text:
        return text, {}
    name, rest = text.split("[", 1)
    return name, dict(kv.split("=", 1) for kv in rest.rstrip("]").split(","))


grid = {}  # world (x, y, z) -> block state string; anything absent is the superflat default
block_entities = {}  # world (x, y, z) -> compound fields


def put(x, y, z, block):
    grid[(x, y, z)] = block


def fill(x0, x1, y0, y1, z0, z1, block):
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                put(x, y, z, block)


def loc(p):  # house local -> world
    return (p[0] + ORIGIN[0], p[1] + ORIGIN[1], p[2] + ORIGIN[2])


def door(kind, facing, hinge, is_open):
    return {
        half: "minecraft:%s_door[facing=%s,half=%s,hinge=%s,open=%s,powered=false]"
        % (kind, facing, half, hinge, "true" if is_open else "false")
        for half in ("lower", "upper")
    }


AIR = "minecraft:air"
GRASS = "minecraft:grass_block[snowy=false]"
DIRT = "minecraft:dirt"
BEDROCK = "minecraft:bedrock"
PATH = "minecraft:dirt_path"
PORCH = "minecraft:stone_bricks"
PORCH_MOSS = "minecraft:mossy_stone_bricks"

DOOR_A_X, DOOR_B_X = 6, 14  # exterior doors in the north wall (z=0) of Room A / Room B


def build_house():
    # Shell, furniture, lamp chain: exactly house.py's palette.
    for c, b in H.STATIC.items():
        put(*loc(c), b)
    # Dynamic cells: house.py's "closed-both" role = closed dark-oak door + warm lantern + soul lantern.
    for c, b in H.dynamic_blocks(H.role("closed-both")).items():
        put(*loc(c), b)
    # Foundation: cobblestone under the perimeter walls and the partition.
    for x in range(0, 19):
        for z in range(0, 13):
            if x in (0, 11, 18) or z in (0, 12):
                put(*loc((x, -1, z)), "minecraft:cobblestone")
    # Exterior doors, closed, panel flush with the outer face, with stripped dark-oak frame posts.
    for cx in (DOOR_A_X, DOOR_B_X):
        d = door("dark_oak", "south", "left", False)
        put(*loc((cx, 1, 0)), d["lower"])
        put(*loc((cx, 2, 0)), d["upper"])
        for fx in (cx - 1, cx + 1):
            fill(fx, fx, GROUND_Y + 1, GROUND_Y + 4, 0, 0, H.FRAME)
    # Porch floor flush with the ground along the whole front.
    rng = random.Random(7)
    for x in range(3, 18):
        for z in range(-3, 0):
            put(x, GROUND_Y, z, PORCH_MOSS if rng.random() < 0.12 else PORCH)


def build_path():
    for z in range(-22, -3):
        for x in (5, 6, 7):
            put(x, GROUND_Y, z, PATH)


# --------------------------------------------------------------------------- trees
def tree(x, z, species, height, rng):
    """Small vanilla-shaped tree. Returns (log cells, leaf cells); leaves are persistent."""
    log = "minecraft:%s_log[axis=y]" % species
    top = GROUND_Y + height  # y of the highest log
    logs = [(x, GROUND_Y + 1 + i, z) for i in range(height)]
    for p in logs:
        put(*p, log)
    leaves = set()

    def ring(y, r):
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if (dx, dz) == (0, 0) and y <= top:
                    continue  # trunk
                if abs(dx) == r and abs(dz) == r and (r == 1 or rng.random() < 0.7):
                    continue  # rounded corners
                leaves.add((x + dx, y, z + dz))

    ring(top - 2, 2)
    ring(top - 1, 2)
    ring(top, 1)
    ring(top + 1, 1)
    return logs, {c for c in leaves if c not in grid}


def finish_leaves(all_logs, all_leaves, species_of):
    """distance=1..7 from the nearest log (BFS); persistent=true so nothing ever decays."""
    dirs = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    dist, q = {}, deque()
    for l in all_logs:
        for d in dirs:
            n = (l[0] + d[0], l[1] + d[1], l[2] + d[2])
            if n in all_leaves and n not in dist:
                dist[n] = 1
                q.append(n)
    while q:
        c = q.popleft()
        for d in dirs:
            n = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
            if n in all_leaves and n not in dist and dist[c] < 7:
                dist[n] = dist[c] + 1
                q.append(n)
    for c in all_leaves:
        put(*c, "minecraft:%s_leaves[distance=%d,persistent=true,waterlogged=false]" % (species_of[c], dist.get(c, 7)))


# (x, z, species, trunk height).  At TIME the Sun is low in the west (-x): the western trees throw long
# shade strips east over the path and the torch oak; the east birches give shaded lawn corners.
TREES = [
    (2, -9, "oak", 5),  # the torch oak: ahead-left of the spawn
    (-12, -11, "birch", 6),
    (-11, -6, "oak", 5),
    (-14, -3, "birch", 6),
    (23, -7, "birch", 6),
    (25, 6, "oak", 5),
]
TORCH = (TREES[0][0], GROUND_Y + 2, TREES[0][1] - 1)  # on the spawn-facing (north) side of the torch oak's trunk


def build_trees():
    rng = random.Random(11)
    logs, leaves, species_of = [], set(), {}
    for x, z, sp, h in TREES:
        lg, lv = tree(x, z, sp, h, rng)
        logs += lg
        leaves |= lv
        for c in lv:
            species_of[c] = sp
    finish_leaves(logs, leaves, species_of)
    put(*TORCH, "minecraft:wall_torch[facing=north]")


def build_decor():
    rng = random.Random(23)
    flora = ["minecraft:short_grass"] * 8 + ["minecraft:fern", "minecraft:poppy", "minecraft:dandelion",
                                              "minecraft:cornflower", "minecraft:oxeye_daisy"]
    for x in range(-18, 32):
        for z in range(-24, 18):
            if (x, GROUND_Y + 1, z) in grid or (x, GROUND_Y, z) in grid:
                continue
            if -1 <= x <= 19 and -4 <= z <= 13:
                continue  # house, porch and their margin
            if 4 <= x <= 8 and z < 0:
                continue  # path corridor
            if any(abs(x - tx) <= 1 and abs(z - tz) <= 1 for tx, tz, _, _ in TREES):
                continue
            if rng.random() < 0.10:
                put(x, GROUND_Y + 1, z, rng.choice(flora))
    # keep a clean, flat lawn beside the path for placing torches
    for x in range(8, 16):
        for z in range(-14, -4):
            grid.pop((x, GROUND_Y + 1, z), None)


# --------------------------------------------------------------------------- signs
def sign(x, z, rotation, lines):
    y = GROUND_Y + 1
    put(x, y, z, "minecraft:oak_sign[rotation=%d,waterlogged=false]" % rotation)
    msgs = ['{"text":"%s"}' % t for t in lines]
    empty = L(T_STRING, ['{"text":""}'] * 4)
    block_entities[(x, y, z)] = {
        "id": S("minecraft:sign"),
        "x": I(x), "y": I(y), "z": I(z),
        "is_waxed": B(False),
        "front_text": C({"messages": L(T_STRING, msgs), "color": S("black"), "has_glowing_text": B(False)}),
        "back_text": C({"messages": empty, "color": S("black"), "has_glowing_text": B(False)}),
    }


# rotation 8 = text faces north, i.e. readable by someone walking south along the path
SIGNS = [
    (9, -14, 8, ["たいまつは", "木の みきに", "あります", ""]),
    (9, -2, 8, ["ドアは", "右クリックで", "開きます", ""]),
]


# --------------------------------------------------------------------------- chunks / regions
def container(states):
    """4096 state strings in YZX order -> (palette NBT list, packed longs or None)."""
    pal, index, ids = [], {}, []
    for s in states:
        if s not in index:
            index[s] = len(pal)
            pal.append(s)
        ids.append(index[s])
    entries = []
    for s in pal:
        name, props = parse_state(s)
        e = {"Name": S(name)}
        if props:
            e["Properties"] = C({k: S(v) for k, v in props.items()})
        entries.append(C(e))
    if len(pal) == 1:
        return L(T_COMPOUND, entries), None
    bits = max(4, (len(pal) - 1).bit_length())
    per = 64 // bits
    longs = []
    for i in range(0, 4096, per):
        v = 0
        for j, idv in enumerate(ids[i:i + per]):
            v |= idv << (j * bits)
        longs.append(v - (1 << 64) if v >= 1 << 63 else v)
    return L(T_COMPOUND, entries), longs


def default_block(y):
    if y == MIN_Y:
        return BEDROCK
    if y in (MIN_Y + 1, MIN_Y + 2):
        return DIRT
    if y == GROUND_Y:
        return GRASS
    return AIR


def chunk_nbt(cx, cz):
    sec_y = MIN_Y // 16  # -4: everything lies in y -64..-49
    assert max(p[1] for p in grid) < MIN_Y + 16
    states = []
    for ly in range(16):
        for lz in range(16):
            for lx in range(16):
                p = (cx * 16 + lx, MIN_Y + ly, cz * 16 + lz)
                states.append(grid.get(p, default_block(p[1])))
    palette, longs = container(states)
    bs = {"palette": palette}
    if longs is not None:
        bs["data"] = (T_LONGS, longs)
    section = {
        "Y": B(sec_y),
        "block_states": C(bs),
        "biomes": C({"palette": L(T_STRING, ["minecraft:plains"])}),
    }
    bes = [C(be) for p, be in sorted(block_entities.items()) if p[0] >> 4 == cx and p[2] >> 4 == cz]
    root = {
        "DataVersion": I(DATA_VERSION),
        "xPos": I(cx), "zPos": I(cz), "yPos": I(sec_y),
        "Status": S("minecraft:full"),
        "LastUpdate": LG(0), "InhabitedTime": LG(0),
        "isLightOn": B(False),  # the game computes sky/block light when it loads the chunk
        "sections": L(T_COMPOUND, [C(section)]),
        "block_entities": L(T_COMPOUND, bes),
        "structures": C({"References": C({}), "starts": C({})}),
        "block_ticks": EMPTY_LIST, "fluid_ticks": EMPTY_LIST,
    }
    return nbt_bytes(root)


def write_regions(world, chunks):
    by_region = {}
    for cx, cz in chunks:
        by_region.setdefault((cx >> 5, cz >> 5), []).append((cx, cz))
    (world / "region").mkdir()
    for (rx, rz), cs in sorted(by_region.items()):
        header, body, sector = bytearray(8192), bytearray(), 2
        for cx, cz in cs:
            raw = zlib.compress(chunk_nbt(cx, cz), 6)
            rec = struct.pack(">IB", len(raw) + 1, 2) + raw
            rec += b"\0" * (-len(rec) % 4096)
            n = len(rec) // 4096
            i = ((cx & 31) + (cz & 31) * 32) * 4
            header[i:i + 4] = struct.pack(">I", (sector << 8) | n)
            header[4096 + i:4096 + i + 4] = struct.pack(">I", 1)  # fixed timestamp: reproducible bytes
            sector += n
            body += rec
        (world / "region" / ("r.%d.%d.mca" % (rx, rz))).write_bytes(bytes(header) + bytes(body))


# --------------------------------------------------------------------------- level.dat
SPAWN = (6.5, GROUND_Y + 1.0, -16.5)
SPAWN_YAW, SPAWN_PITCH = 0.0, 7.0  # +z = south: straight down the path at the house; torch oak ~27 deg to the left

HOTBAR = [  # ordinary creative hotbar; the full creative inventory is available as usual
    ("minecraft:torch", 64), ("minecraft:lantern", 16), ("minecraft:soul_lantern", 16),
    ("minecraft:dark_oak_door", 4), ("minecraft:oak_planks", 64), ("minecraft:stone_bricks", 64),
    ("minecraft:oak_sapling", 8), ("minecraft:birch_sapling", 8),
]
GAME_RULES = {"doDaylightCycle": "false", "doWeatherCycle": "false", "doMobSpawning": "false",
              "doInsomnia": "false", "announceAdvancements": "false"}


def level_dat():
    def noise(setting, source):
        return {"type": S("minecraft:noise"), "settings": S("minecraft:" + setting), "biome_source": C(source)}

    flat = {
        "type": S("minecraft:flat"),
        "settings": C({
            "biome": S("minecraft:plains"),
            "features": B(False),
            "lakes": B(False),
            "structure_overrides": EMPTY_LIST,
            "layers": L(T_COMPOUND, [C({"block": S("minecraft:bedrock"), "height": I(1)}),
                                     C({"block": S("minecraft:dirt"), "height": I(2)}),
                                     C({"block": S("minecraft:grass_block"), "height": I(1)})]),
        }),
    }
    dims = {
        "minecraft:overworld": C({"type": S("minecraft:overworld"), "generator": C(flat)}),
        "minecraft:the_nether": C({"type": S("minecraft:the_nether"), "generator": C(noise("nether", {"type": S("minecraft:multi_noise"), "preset": S("minecraft:nether")}))}),
        "minecraft:the_end": C({"type": S("minecraft:the_end"), "generator": C(noise("end", {"type": S("minecraft:the_end")}))}),
    }
    inventory = [C({"Slot": B(i), "id": S(name), "count": I(n)}) for i, (name, n) in enumerate(HOTBAR)]
    player = {
        "Pos": L(T_DOUBLE, SPAWN),
        "Motion": L(T_DOUBLE, [0.0, 0.0, 0.0]),
        "Rotation": L(T_FLOAT, [SPAWN_YAW, SPAWN_PITCH]),
        "Dimension": S("minecraft:overworld"),
        "OnGround": B(True), "Air": SH(300), "Fire": SH(-20), "FallDistance": F(0.0),
        "Health": F(20.0), "foodLevel": I(20), "foodSaturationLevel": F(5.0), "foodExhaustionLevel": F(0.0),
        "foodTickTimer": I(0), "XpLevel": I(0), "XpP": F(0.0), "XpTotal": I(0), "Score": I(0),
        "playerGameType": I(1), "selectedItemSlot": I(0),
        "Inventory": L(T_COMPOUND, inventory),
        "abilities": C({"flying": B(False), "mayfly": B(True), "instabuild": B(True), "invulnerable": B(True),
                        "mayBuild": B(True), "flySpeed": F(0.05), "walkSpeed": F(0.1)}),
    }
    data = {
        "DataVersion": I(DATA_VERSION), "version": I(19133),
        "Version": C({"Id": I(DATA_VERSION), "Name": S("1.21.1"), "Series": S("main"), "Snapshot": B(False)}),
        "LevelName": S(LEVEL_NAME), "GameType": I(1), "Difficulty": B(0), "DifficultyLocked": B(False),
        "hardcore": B(False), "allowCommands": B(False), "initialized": B(True), "DragonFight": C({}),
        "SpawnX": I(int(SPAWN[0] // 1)), "SpawnY": I(int(SPAWN[1])), "SpawnZ": I(int(SPAWN[2] // 1)),
        "SpawnAngle": F(SPAWN_YAW),
        "Time": LG(TIME), "DayTime": LG(TIME), "LastPlayed": LG(LAST_PLAYED_MS),
        "raining": B(False), "thundering": B(False), "rainTime": I(0), "thunderTime": I(0),
        "clearWeatherTime": I(1000000), "WanderingTraderSpawnChance": I(0), "WanderingTraderSpawnDelay": I(0),
        "BorderCenterX": D(0.0), "BorderCenterZ": D(0.0), "BorderSize": D(59999968.0),
        "BorderSafeZone": D(5.0), "BorderDamagePerBlock": D(0.2), "BorderWarningBlocks": D(5.0),
        "BorderWarningTime": D(15.0), "BorderSizeLerpTime": LG(0), "BorderSizeLerpTarget": D(59999968.0),
        "DataPacks": C({"Enabled": L(T_STRING, ["vanilla"]), "Disabled": L(T_STRING, ["bundle", "trade_rebalance"])}),
        "enabled_features": L(T_STRING, ["minecraft:vanilla"]),
        "GameRules": C({k: S(v) for k, v in GAME_RULES.items()}),
        "WorldGenSettings": C({"seed": LG(SEED), "generate_features": B(False), "bonus_chest": B(False),
                               "dimensions": C(dims)}),
        "Player": C(player),
    }
    return nbt_bytes({"Data": C(data)})


# --------------------------------------------------------------------------- main
def build(out):
    world = Path(out) / WORLD_NAME
    if world.exists():
        raise SystemExit("refusing to overwrite " + str(world))
    build_house()
    build_path()
    build_trees()
    build_decor()
    for x, z, rot, lines in SIGNS:
        sign(x, z, rot, lines)
    world.mkdir(parents=True)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as g:
        g.write(level_dat())
    (world / "level.dat").write_bytes(buf.getvalue())
    write_regions(world, [(cx, cz) for cx in range(-2, 3) for cz in range(-3, 2)])
    return world


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(build(sys.argv[1]))
