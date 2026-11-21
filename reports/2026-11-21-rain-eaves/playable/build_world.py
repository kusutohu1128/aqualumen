"""Offline generator for the standalone "Aqualumen Rain Walk" Minecraft Java 1.21.1 survival save.

stdlib only.  Fresh superflat-plains world (features/structures off), written from scratch:
no datapack, no command block, no marker file, no player UUID, nothing copied from any save.

Reuses (read-only, imported): the NBT writer / palette packer of the Lantern House generator
(reports/2026-11-21-door-light/playable/build_world.py) and the matched stone/smooth-stone eave
geometry + specular-mirror maths of reports/2026-11-21-rain-eaves/fixture/fixture.py.

Route (local x east, z south, y up; local y = 0 is the grass layer, world y = local y - 61):

    spawn (3.5, 12.5) on the open end of a timber patio, facing north (yaw 180)
      -> W along x = 3.5 through the eave (lantern hangs under it) and a back-wall doorway
      -> path north to a torch oak -> a cut and a timber-framed mine tunnel under a low wooded ridge
      -> path north to a stone bank on a small reed inlet
    S walks the same line back.  Every cell on the line is flat, ground level, 2+ blocks of headroom.

    python3 -I build_world.py <output-dir>      # creates <output-dir>/Aqualumen-Rain-Walk
"""

import datetime
import gzip
import importlib.util
import io
import math
import random
import struct
import sys
import zlib
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORTS = HERE.parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LH = _load("aql_lantern_build", REPORTS / "2026-11-21-door-light/playable/build_world.py")
FX = _load("aql_rain_fixture", REPORTS / "2026-11-21-rain-eaves/fixture/fixture.py")
S, I, SH, B, F, D, LG, C, L = LH.S, LH.I, LH.SH, LH.B, LH.F, LH.D, LH.LG, LH.C, LH.L
T_STRING, T_DOUBLE, T_FLOAT, T_COMPOUND, T_LONGS = LH.T_STRING, LH.T_DOUBLE, LH.T_FLOAT, LH.T_COMPOUND, LH.T_LONGS
EMPTY_LIST, nbt_bytes, container = LH.EMPTY_LIST, LH.nbt_bytes, LH.container

WORLD_NAME = "Aqualumen-Rain-Walk"
LEVEL_NAME = "Aqualumen Rain Walk"
DATA_VERSION = 3955  # Minecraft 1.21.1
SEED = 2026112102
GROUND_Y = -61  # world y of the grass layer == local y 0
MIN_LOCAL_Y = -3  # bedrock
LAST_PLAYED_MS = int(datetime.datetime(2026, 11, 21, 5, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=9))).timestamp() * 1000)

# Weather / time: late afternoon, raining; the vanilla cycle flips rain off after RAIN_TICKS (170 s), then runs on its own.
DAY_TIME = 10000  # 16:00 in game time: Sun still up, sets (tick 12000) while it rains
RAIN_TICKS = 3600  # 180 s

# ---------------------------------------------------------------------------- blocks
AIR = "minecraft:air"
GRASS = "minecraft:grass_block[snowy=false]"
DIRT = "minecraft:dirt"
STONE = "minecraft:stone"
COBBLE = "minecraft:cobblestone"
MOSSY = "minecraft:mossy_cobblestone"
ANDESITE = "minecraft:andesite"
GRAVEL = "minecraft:gravel"
SAND = "minecraft:sand"
PATH = "minecraft:dirt_path"
WATER = "minecraft:water[level=0]"
OAK_LOG_X = "minecraft:oak_log[axis=x]"
OAK_LOG_Y = "minecraft:oak_log[axis=y]"
OAK_PLANKS = "minecraft:oak_planks"
SPRUCE_PLANKS = "minecraft:spruce_planks"  # patio floor frame + back wall
POST = "minecraft:stripped_spruce_log[axis=y]"
ROOF = "minecraft:dark_oak_planks"  # == fixture ROOF
LANTERN = FX.LANTERN  # minecraft:lantern[hanging=true,waterlogged=false]
SMOOTH = FX.SMOOTH
STONE_STRIP = FX.STONE
BENCH = "minecraft:spruce_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]"
CHAIN = "minecraft:chain[axis=y,waterlogged=false]"

grid = {}  # local (x, y, z) -> block state string; absent = superflat default
block_entities = {}  # local (x, y, z) -> compound fields
surface = {}  # (x, z) -> y of the highest ground block (for trees / decor)


def put(x, y, z, block):
    grid[(x, y, z)] = block


def fill(x0, x1, y0, y1, z0, z1, block):
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                put(x, y, z, block)


def get(x, y, z):
    if (x, y, z) in grid:
        return grid[(x, y, z)]
    return default_block(y)


def default_block(y):
    if y == MIN_LOCAL_Y:
        return "minecraft:bedrock"
    if y in (MIN_LOCAL_Y + 1, MIN_LOCAL_Y + 2):
        return DIRT
    if y == 0:
        return GRASS
    return AIR


def ground_top(x, z):
    return surface.get((x, z), 0)


# ---------------------------------------------------------------------------- geometry constants
PATIO_X = (0, 12)  # fixture: floor/roof/wall x 0..12
PATIO_Z = (0, 14)  # fixture strips ran z 1..11; extended south to z 14 so the player can spawn on them
ROUTE_X = 3  # route centre line: cell x = 3 (x 3.0..4.0, centre 3.5); tunnel, doorway and path are x 2..4
PATH_X = (2, 4)
SPAWN = (3.5, 12.5)  # feet; eye = floor + 1.62
TUNNEL_Z = (-54, -36)  # interior cells z -54..-36 (south portal at -36, north portal at -54)
CHAMBER_Z = (-48, -44)
FRAME_Z = (-36, -40, -50, -54)
HILL = dict(cx=3.5, cz=-45.0, ax=22.0, az=13.0, h=9.0)
LAKE = dict(cx=3.5, cz=-88.0, ax=14.0, az=8.5)
END_Z = -77  # last path cell before the stone bank
TORCH_TREE = (6, -9)


# ---------------------------------------------------------------------------- patio (fixture geometry, translated by 0)
def build_patio():
    x0, x1 = PATIO_X
    z0, z1 = PATIO_Z
    fill(x0, x1, 0, 0, z0, z1, SPRUCE_PLANKS)  # frame; the strips overwrite it
    fill(*[v for v in (3, 5, 0, 0, 1, z1)], STONE_STRIP)  # fixture STONE_BOX x 3..5, z 1..(11->14)
    fill(*[v for v in (7, 9, 0, 0, 1, z1)], SMOOTH)  # fixture SMOOTH_BOX x 7..9
    fill(0, 12, 1, 4, 0, 0, SPRUCE_PLANKS)  # back wall, face z = 1
    fill(2, 4, 1, 3, 0, 0, AIR)  # doorway x 2..4 on the route line
    for x in (1, 5):
        fill(x, x, 1, 3, 0, 0, POST)  # jamb posts
    fill(0, 0, 1, 4, 5, 5, POST)  # front posts under the eave row (fixture: x 0 and 12)
    fill(12, 12, 1, 4, 5, 5, POST)
    fill(0, 12, 5, 5, 0, 5, ROOF)  # roof; eave (drip) plane z = 6
    put(6, 4, 5, LANTERN)  # fixture LAMP_CELL: hangs from roof cell (6,5,5)
    for x in (1, 10, 11):
        put(x, 1, 1, BENCH)  # benches along the back wall, away from the measured strips
    # patio ground is flush with the grass layer: surface y = 0
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            surface[(x, z)] = 0


# ---------------------------------------------------------------------------- ridge + tunnel
def hill_height(x, z):
    hh = HILL
    dx = (x + 0.5 - hh["cx"]) / hh["ax"]
    dz = (z + 0.5 - hh["cz"]) / hh["az"]
    r2 = dx * dx + dz * dz
    if r2 >= 1.0:
        return 0
    base = hh["h"] * math.sqrt(1.0 - r2)
    noise = 0.7 * math.sin(x * 0.43 + 1.1) * math.cos(z * 0.31 + 0.4) + 0.5 * math.sin(x * 0.17 - z * 0.23)
    h = int(math.floor(base + noise + 0.5))
    return max(h, 0) if base > 0.6 else 0


def in_tunnel_range(z):
    return TUNNEL_Z[0] <= z <= TUNNEL_Z[1]


def build_ridge():
    rng = random.Random(31)
    heights = {}
    for x in range(-24, 32):
        for z in range(-62, -28):
            h = hill_height(x, z)
            if 0 <= x <= 6 and TUNNEL_Z[0] - 1 <= z <= TUNNEL_Z[1] + 1:
                h = max(h, 6)  # solid cover over the tunnel and its portal walls
            if 1 <= x <= 5 and not in_tunnel_range(z):
                h = 0  # open cut (5 wide) leading to each portal
            heights[(x, z)] = h
    for (x, z), h in heights.items():
        surface[(x, z)] = h
        if h <= 0:
            continue
        for y in range(0, h + 1):
            if y == h:
                put(x, y, z, GRASS)
            elif y >= h - 3:
                put(x, y, z, DIRT)
            else:
                put(x, y, z, STONE)
    # the rock around the tunnel is stone all the way up to the ceiling plane (no dirt in the mine walls)
    for (x, y, z), b in list(grid.items()):
        if b == DIRT and y <= 4 and -1 <= x <= 7 and TUNNEL_Z[0] - 1 <= z <= TUNNEL_Z[1] + 1:
            grid[(x, y, z)] = STONE
    # tunnel: air x 2..4, y 1..3; chamber widens to x 0..6 (z -48..-44)
    floor_rng = random.Random(41)
    for z in range(TUNNEL_Z[0], TUNNEL_Z[1] + 1):
        wide = CHAMBER_Z[0] <= z <= CHAMBER_Z[1]
        xs = range(0, 7) if wide else range(2, 5)
        for x in xs:
            fill(x, x, 1, 3, z, z, AIR)
            put(x, 0, z, floor_rng.choice([COBBLE, COBBLE, GRAVEL, ANDESITE]))
    # timber frames: posts in the wall plane (x 1 and 5), beam in the ceiling plane (y 4) -> headroom stays 3
    for z in FRAME_Z:
        for x in (1, 5):
            fill(x, x, 1, 3, z, z, OAK_LOG_Y)
        fill(1, 5, 4, 4, z, z, OAK_LOG_X)
    # ore flecks in stone that touches the tunnel air (coal common, iron rare); posts/beams untouched
    for (x, y, z), b in sorted(grid.items()):
        if b != STONE or not (1 <= y <= 4) or not (-1 <= x <= 7 and TUNNEL_Z[0] - 1 <= z <= TUNNEL_Z[1] + 1):
            continue
        near_air = any(get(x + dx, y + dy, z + dz) == AIR for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, -1, 0), (0, 1, 0)))
        if near_air:
            r = rng.random()
            if r < 0.14:
                put(x, y, z, "minecraft:coal_ore")
            elif r < 0.19:
                put(x, y, z, "minecraft:iron_ore")
    # wall torches: portal fronts (on the portal posts) and inside, on frame posts
    for x in (1, 5):
        put(x, 2, TUNNEL_Z[1] + 1, "minecraft:wall_torch[facing=south]")  # south portal, front face of post at z -36
        put(x, 2, TUNNEL_Z[0] - 1, "minecraft:wall_torch[facing=north]")  # north portal, front face of post at z -54
    put(2, 2, -40, "minecraft:wall_torch[facing=east]")  # on post (1,2,-40)
    # chamber lantern: chain from the ceiling, off the walking line (x 5)
    put(5, 3, -46, CHAIN)
    put(5, 2, -46, LANTERN)
    return heights


# ---------------------------------------------------------------------------- path
def build_path():
    for z in range(-1, END_Z - 1, -1):
        if in_tunnel_range(z):
            continue
        for x in range(PATH_X[0], PATH_X[1] + 1):
            put(x, 0, z, PATH)
            surface[(x, z)] = 0


# ---------------------------------------------------------------------------- lake / inlet / bank / reeds
def lake_water(x, z):
    lk = LAKE
    dx = (x + 0.5 - lk["cx"]) / lk["ax"]
    dz = (z + 0.5 - lk["cz"]) / lk["az"]
    wob = 0.10 * math.sin(x * 0.6 + z * 0.35) + 0.06 * math.sin(z * 0.9 - x * 0.2)
    if dx * dx + dz * dz <= 1.0 + wob:
        return True
    if -17 <= x <= -5:  # inlet arm toward the west, narrowing
        half = 1.5 + 1.0 * (x + 17) / 12.0
        centre = -88.0 + 0.5 * math.sin(x * 0.4)
        return abs(z + 0.5 - centre) <= half
    return False


def build_lake():
    rng = random.Random(53)
    water = set()
    for x in range(-24, 28):
        for z in range(-104, -72):
            if lake_water(x, z):
                water.add((x, z))
    ring1 = {(x + dx, z + dz) for x, z in water for dx in (-1, 0, 1) for dz in (-1, 0, 1)} - water
    ring2 = {(x + dx, z + dz) for x, z in ring1 for dx in (-1, 0, 1) for dz in (-1, 0, 1)} - water - ring1
    for x, z in sorted(water):
        put(x, -2, z, rng.choice([SAND, SAND, SAND, GRAVEL]))
        put(x, -1, z, WATER)
        put(x, 0, z, WATER)
        surface[(x, z)] = -1  # water: not ground for trees/flora
    cane_bases = []
    for x, z in sorted(ring1 | ring2):
        south_bank = z > -88 and -7 <= x <= 14
        if south_bank:
            r = rng.random()
            put(x, 0, z, STONE if r < 0.40 else COBBLE if r < 0.80 else MOSSY)
            surface[(x, z)] = 0
        elif (x, z) in ring1:
            put(x, 0, z, SAND if rng.random() < 0.7 else GRASS)
            surface[(x, z)] = 0
            cane_bases.append((x, z))
    # reeds: sugar cane on a base block that has water in one of its four neighbours (vanilla rule)
    cane = []
    for x, z in cane_bases:
        if get(x, 0, z) not in (SAND, GRASS):
            continue
        if not any((x + dx, z + dz) in water for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            continue
        if 0 <= x <= 7 and z > -88:
            continue
        if rng.random() < 0.55:
            for i in range(rng.choice([1, 2, 2, 3])):
                put(x, 1 + i, z, "minecraft:sugar_cane[age=0]")
            cane.append((x, z))
    # a few lily pads on open water
    pads = 0
    for x, z in sorted(water):
        if pads < 12 and all((x + dx, z + dz) in water for dx in (-1, 0, 1) for dz in (-1, 0, 1)) and rng.random() < 0.06:
            put(x, 1, z, "minecraft:lily_pad")
            pads += 1
    return water, cane


# ---------------------------------------------------------------------------- trees
def log_block(species, axis="y"):
    return "minecraft:%s_log[axis=%s]" % (species, axis)


def make_tree(x, z, species, height, base_y, leaves):
    """Trunk at (x, z) standing on ground y base_y; returns log cells; leaf cells added to `leaves`."""
    logs = [(x, base_y + 1 + i, z) for i in range(height)]
    for p in logs:
        put(*p, log_block(species))
    top = base_y + height
    cells = set()
    if species == "spruce":
        for dy, r in ((1, 0), (0, 1), (-1, 2), (-2, 1), (-3, 2), (-4, 3)):
            y = top + dy
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if abs(dx) + abs(dz) <= r and not (dx == 0 and dz == 0 and y <= top):
                        cells.add((x + dx, y, z + dz))
    else:
        rng = random.Random(x * 7919 + z * 104729)

        def ring(y, r):
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if (dx, dz) == (0, 0) and y <= top:
                        continue
                    if abs(dx) == r and abs(dz) == r and (r == 1 or rng.random() < 0.7):
                        continue
                    cells.add((x + dx, y, z + dz))

        ring(top - 2, 2), ring(top - 1, 2), ring(top, 1), ring(top + 1, 1)
    for c in cells:
        if c not in grid or grid[c] == AIR:
            leaves[c] = species
    return logs


def finish_leaves(all_logs, leaves):
    dirs = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    dist, q = {}, deque()
    for l in all_logs:
        for d in dirs:
            n = (l[0] + d[0], l[1] + d[1], l[2] + d[2])
            if n in leaves and n not in dist:
                dist[n] = 1
                q.append(n)
    while q:
        c = q.popleft()
        for d in dirs:
            n = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
            if n in leaves and n not in dist and dist[c] < 7:
                dist[n] = dist[c] + 1
                q.append(n)
    for c, sp in sorted(leaves.items()):
        if c in grid and grid[c] != AIR:
            continue
        put(*c, "minecraft:%s_leaves[distance=%d,persistent=true,waterlogged=false]" % (sp, dist.get(c, 7)))


FIXED_TREES = [  # (x, z, species, trunk height); all >= 3 cells off the x 1..5 route corridor
    (6, -9, "oak", 6),  # the torch oak; torch on its west face, seen through the doorway from the spawn
    (-5, -4, "birch", 6), (-9, -12, "oak", 5), (-4, -20, "spruce", 8), (-11, -25, "birch", 6),
    (12, -14, "birch", 6), (10, -22, "spruce", 8), (16, -6, "oak", 6), (18, -27, "birch", 6),
    (-8, -66, "oak", 5), (9, -64, "birch", 6), (-11, -72, "spruce", 8), (13, -71, "oak", 5),
    (-13, -76, "birch", 6), (-8, 20, "oak", 5), (16, 19, "birch", 6), (-14, 6, "spruce", 8), (22, 8, "oak", 5),
]
TORCH = (TORCH_TREE[0] - 1, 2, TORCH_TREE[1])  # west face of the torch oak, facing west


def build_trees(water):
    leaves, all_logs = {}, []
    placed = []
    for x, z, sp, h in FIXED_TREES:
        all_logs += make_tree(x, z, sp, h, ground_top(x, z), leaves)
        placed.append((x, z))
    # wooded ridge: deterministic scatter on the hill top, away from the route corridor and cuts
    rng = random.Random(67)
    tries = 0
    while tries < 900 and len(placed) < len(FIXED_TREES) + 30:
        tries += 1
        x, z = rng.randrange(-20, 28), rng.randrange(-58, -33)
        h = ground_top(x, z)
        if h < 3 or -2 <= x <= 8 or any(abs(x - px) < 4 and abs(z - pz) < 4 for px, pz in placed):
            continue
        sp = rng.choice(["oak", "spruce", "spruce", "birch", "oak"])
        height = 4 + rng.randrange(0, 3) if sp != "spruce" else 6 + rng.randrange(0, 3)
        all_logs += make_tree(x, z, sp, height, h, leaves)
        placed.append((x, z))
    finish_leaves(all_logs, leaves)
    put(*TORCH, "minecraft:wall_torch[facing=west]")
    return placed


# ---------------------------------------------------------------------------- decor
def build_decor(trees, water):
    rng = random.Random(23)
    flora = ["minecraft:short_grass"] * 9 + ["minecraft:fern", "minecraft:poppy", "minecraft:dandelion", "minecraft:cornflower",
                                              "minecraft:oxeye_daisy"]
    for x in range(-24, 32):
        for z in range(-100, 24):
            top = ground_top(x, z)
            if top < 0 or get(x, top, z) != GRASS or get(x, top + 1, z) != AIR:
                continue
            if -1 <= x <= 13 and -2 <= z <= 15:
                continue  # patio and apron
            if 1 <= x <= 5:
                continue  # route corridor stays clean
            if any(abs(x - tx) <= 1 and abs(z - tz) <= 1 for tx, tz in trees):
                continue
            if rng.random() < 0.10:
                put(x, top + 1, z, rng.choice(flora))


# ---------------------------------------------------------------------------- signs
def sign(x, y, z, rotation, lines):
    put(x, y, z, "minecraft:oak_sign[rotation=%d,waterlogged=false]" % rotation)
    msgs = ['{"text":"%s"}' % t for t in lines]
    empty = L(T_STRING, ['{"text":""}'] * 4)
    block_entities[(x, y, z)] = {
        "id": S("minecraft:sign"), "x": I(x), "y": I(y + GROUND_Y), "z": I(z), "is_waxed": B(False),
        "front_text": C({"messages": L(T_STRING, msgs), "color": S("black"), "has_glowing_text": B(False)}),
        "back_text": C({"messages": empty, "color": S("black"), "has_glowing_text": B(False)}),
    }


SIGNS = [  # rotation 0 = text faces south, i.e. readable by someone coming from the south
    (1, 1, 9, 0, ["北へ まっすぐ", "木 → 坑道 → 池", "(Sキーで もどる)", ""]),
    (6, 1, -75, 0, ["池の ほとり", "南へ もどると", "坑道 と テラス", ""]),
]


# ---------------------------------------------------------------------------- spawn / optics
EYE_H = 1.62


def spawn_eye():
    return (SPAWN[0], 1.0 + EYE_H, SPAWN[1])  # local coords; floor top y = 1.0


def spawn_rotation():
    """yaw 180 (north); pitch frames both the lantern and its mirror reflection on the exposed stone strip."""
    eye = spawn_eye()
    m = FX.mirror(eye)

    def elevation(pt):
        return math.degrees(math.atan2(pt[1] - eye[1], math.hypot(pt[0] - eye[0], pt[2] - eye[2])))

    # Minecraft pitch is positive downwards; centre the frame between the two elevation angles
    return 180.0, round(-(elevation(m) + elevation(FX.LAMP_CENTRE)) / 2, 1)


# ---------------------------------------------------------------------------- chunks / regions
def chunk_nbt(cx, cz, chunk_cells):
    by_sec = {}
    for (x, y, z) in chunk_cells:
        by_sec.setdefault((y + GROUND_Y) // 16, []).append((x, y, z))
    sec_ys = sorted(set(by_sec) | {-4})
    sections = []
    for sy in sec_ys:
        states = []
        for ly in range(16):
            wy = sy * 16 + ly
            y = wy - GROUND_Y
            for lz in range(16):
                for lx in range(16):
                    p = (cx * 16 + lx, y, cz * 16 + lz)
                    states.append(grid.get(p, default_block(y)))
        pal, longs = container(states)
        bs = {"palette": pal}
        if longs is not None:
            bs["data"] = (T_LONGS, longs)
        sections.append(C({"Y": B(sy), "block_states": C(bs), "biomes": C({"palette": L(T_STRING, ["minecraft:plains"])})}))
    bes = [C(be) for p, be in sorted(block_entities.items()) if p[0] >> 4 == cx and p[2] >> 4 == cz]
    root = {
        "DataVersion": I(DATA_VERSION), "xPos": I(cx), "zPos": I(cz), "yPos": I(-4),
        "Status": S("minecraft:full"), "LastUpdate": LG(0), "InhabitedTime": LG(0),
        "isLightOn": B(False),  # the game computes sky/block light when it loads the chunk
        "sections": L(T_COMPOUND, sections),
        "block_entities": L(T_COMPOUND, bes),
        "structures": C({"References": C({}), "starts": C({})}),
        "block_ticks": EMPTY_LIST, "fluid_ticks": EMPTY_LIST,
    }
    return nbt_bytes(root)


CHUNK_RANGE = (range(-3, 3), range(-8, 2))  # chunk x -3..2 (x -48..47), chunk z -8..1 (z -128..31)


def write_regions(world):
    cells_by_chunk = {}
    for p in grid:
        cells_by_chunk.setdefault((p[0] >> 4, p[2] >> 4), []).append(p)
    chunks = [(cx, cz) for cx in CHUNK_RANGE[0] for cz in CHUNK_RANGE[1]]
    assert all(c in set(chunks) for c in cells_by_chunk), "content outside the written chunk range"
    by_region = {}
    for cx, cz in chunks:
        by_region.setdefault((cx >> 5, cz >> 5), []).append((cx, cz))
    (world / "region").mkdir()
    for (rx, rz), cs in sorted(by_region.items()):
        header, body, sector = bytearray(8192), bytearray(), 2
        for cx, cz in cs:
            raw = zlib.compress(chunk_nbt(cx, cz, cells_by_chunk.get((cx, cz), [])), 6)
            rec = struct.pack(">IB", len(raw) + 1, 2) + raw
            rec += b"\0" * (-len(rec) % 4096)
            n = len(rec) // 4096
            i = ((cx & 31) + (cz & 31) * 32) * 4
            header[i:i + 4] = struct.pack(">I", (sector << 8) | n)
            header[4096 + i:4096 + i + 4] = struct.pack(">I", 1)  # fixed timestamp: reproducible bytes
            sector += n
            body += rec
        (world / "region" / ("r.%d.%d.mca" % (rx, rz))).write_bytes(bytes(header) + bytes(body))
    return chunks


# ---------------------------------------------------------------------------- level.dat
# Slot 0 stays empty and is the selected slot, so the hand starts empty whichever tag spelling a reader honours.
HOTBAR = [(1, "minecraft:torch", 16), (2, "minecraft:lantern", 4), (3, "minecraft:soul_lantern", 4), (4, "minecraft:wooden_pickaxe", 1)]


def level_dat():
    def noise(setting, source):
        return {"type": S("minecraft:noise"), "settings": S("minecraft:" + setting), "biome_source": C(source)}

    flat = {
        "type": S("minecraft:flat"),
        "settings": C({
            "biome": S("minecraft:plains"), "features": B(False), "lakes": B(False), "structure_overrides": EMPTY_LIST,
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
    yaw, pitch = spawn_rotation()
    pos = (SPAWN[0], GROUND_Y + 1.0, SPAWN[1])
    inventory = [C({"Slot": B(s), "id": S(n), "count": I(c)}) for s, n, c in HOTBAR]
    player = {
        "Pos": L(T_DOUBLE, pos), "Motion": L(T_DOUBLE, [0.0, 0.0, 0.0]), "Rotation": L(T_FLOAT, [yaw, pitch]),
        "Dimension": S("minecraft:overworld"), "OnGround": B(True), "Air": SH(300), "Fire": SH(-20), "FallDistance": F(0.0),
        "Health": F(20.0), "foodLevel": I(20), "foodSaturationLevel": F(5.0), "foodExhaustionLevel": F(0.0),
        "foodTickTimer": I(0), "XpLevel": I(0), "XpP": F(0.0), "XpTotal": I(0), "Score": I(0),
        "playerGameType": I(0), "SelectedItemSlot": I(0), "Inventory": L(T_COMPOUND, inventory),
        "abilities": C({"flying": B(False), "mayfly": B(False), "instabuild": B(False), "invulnerable": B(False),
                        "mayBuild": B(True), "flySpeed": F(0.05), "walkSpeed": F(0.1)}),
    }
    data = {
        "DataVersion": I(DATA_VERSION), "version": I(19133),
        "Version": C({"Id": I(DATA_VERSION), "Name": S("1.21.1"), "Series": S("main"), "Snapshot": B(False)}),
        "LevelName": S(LEVEL_NAME), "GameType": I(0), "Difficulty": B(0), "DifficultyLocked": B(False),
        "hardcore": B(False), "allowCommands": B(False), "initialized": B(True), "DragonFight": C({}),
        "SpawnX": I(int(SPAWN[0] // 1)), "SpawnY": I(GROUND_Y + 1), "SpawnZ": I(int(SPAWN[1] // 1)), "SpawnAngle": F(yaw),
        "Time": LG(DAY_TIME), "DayTime": LG(DAY_TIME), "LastPlayed": LG(LAST_PLAYED_MS),
        "raining": B(True), "rainTime": I(RAIN_TICKS), "thundering": B(False), "thunderTime": I(0), "clearWeatherTime": I(0),
        "WanderingTraderSpawnChance": I(25), "WanderingTraderSpawnDelay": I(24000),
        "BorderCenterX": D(0.0), "BorderCenterZ": D(0.0), "BorderSize": D(59999968.0), "BorderSafeZone": D(5.0),
        "BorderDamagePerBlock": D(0.2), "BorderWarningBlocks": D(5.0), "BorderWarningTime": D(15.0),
        "BorderSizeLerpTime": LG(0), "BorderSizeLerpTarget": D(59999968.0),
        "DataPacks": C({"Enabled": L(T_STRING, ["vanilla"]), "Disabled": L(T_STRING, ["bundle", "trade_rebalance"])}),
        "enabled_features": L(T_STRING, ["minecraft:vanilla"]),
        "GameRules": C({}),  # every rule at its vanilla default: doDaylightCycle, doWeatherCycle, doMobSpawning ... all on
        "WorldGenSettings": C({"seed": LG(SEED), "generate_features": B(False), "bonus_chest": B(False), "dimensions": C(dims)}),
        "Player": C(player),
    }
    return nbt_bytes({"Data": C(data)})


# ---------------------------------------------------------------------------- main
def build(out):
    world = Path(out) / WORLD_NAME
    if world.exists():
        raise SystemExit("refusing to overwrite " + str(world))
    build_patio()
    build_ridge()
    build_path()
    water, cane = build_lake()
    trees = build_trees(water)
    build_decor(trees, water)
    for x, y, z, rot, lines in SIGNS:
        sign(x, y, z, rot, lines)
    world.mkdir(parents=True)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as g:
        g.write(level_dat())
    (world / "level.dat").write_bytes(buf.getvalue())
    chunks = write_regions(world)
    print("chunks", len(chunks), "cells", len(grid), "trees", len(trees), "water", len(water), "cane", len(cane))
    return world


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(build(sys.argv[1]))
