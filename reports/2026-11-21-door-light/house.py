"""Two-room house geometry for the native door-light fixture (stdlib only).

Local block coordinates, world = ORIGIN + local; cells are integer lower corners.
x east, y up, z south.  Minecraft yaw 0 faces +z, -90 faces +x; pitch > 0 looks down.

  Room A (west, x 1..10, z 1..11): low afternoon Sun through a west glass-pane window
     (x=0, z 2..3, y 2..3) lays a strip on the oak floor; a matte white_concrete receiver
     runner (x 4..10, z 5..7) lies in front of the doorway; an independent soul lantern stands
     on the floor at (4,1,9) next to a smooth_stone receiver (x 5..6, z 9..10).
  Partition x=11 with the doorway at (11, 1..2, 6), framed by stripped dark-oak posts.
  Room B (east, x 12..17, windowless): warm lantern hanging from a chain at (13,3,6), 2 m
     behind the doorway on its axis.  Neither camera can see the lantern (verified below).

This module exposes the same interface the indirect-light capture runner reads from its
fixture module (PLAYER, POSES, ROLE_NAMES, role, feet, fmt, samples, WIDTH, ...).  Projection
math is imported from that fixture rather than duplicated.
"""

import importlib.util
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "aql_indirect_fixture", HERE.parent / "2026-11-21-indirect-light/fixture.py"
)
IF = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(IF)

ORIGIN = (400, 160, -410)
LO, HI = (-1, -1, -1), (19, 7, 13)  # inclusive reserved cell bounds
CELLS = (HI[0] - LO[0] + 1) * (HI[1] - LO[1] + 1) * (HI[2] - LO[2] + 1)
WIDTH, HEIGHT, FOV, EYE, PATCH = IF.WIDTH, IF.HEIGHT, IF.FOV, IF.EYE, IF.PATCH
PLAYER = "AqualumenOptics"
TIME = 11800  # Sun ~15.5 deg above the western horizon (vanilla celestial angle, no path rotation)
fmt = IF.fmt
project = IF.project
ray = IF.ray

AIR = "minecraft:air"
WHITE = "minecraft:white_concrete"
STONE = "minecraft:smooth_stone"
OAK_FLOOR = "minecraft:oak_planks"
SPRUCE_FLOOR = "minecraft:spruce_planks"
WALL = "minecraft:spruce_planks"
PLINTH = "minecraft:stone_bricks"
POST = "minecraft:stripped_spruce_log[axis=y]"
FRAME = "minecraft:stripped_dark_oak_log[axis=y]"
CEIL = "minecraft:spruce_planks"
BEAM = "minecraft:dark_oak_log[axis=z]"
ROOF = "minecraft:dark_oak_slab[type=bottom,waterlogged=false]"
PANE_NS = "minecraft:glass_pane[east=false,north=true,south=true,waterlogged=false,west=false]"
PANE_EW = "minecraft:glass_pane[east=true,north=false,south=false,waterlogged=false,west=true]"
CHAIN = "minecraft:chain[axis=y,waterlogged=false]"
WARM = "minecraft:lantern[hanging=true,waterlogged=false]"
SOUL = "minecraft:soul_lantern[hanging=false,waterlogged=false]"


def door(kind, half, is_open):
    return "minecraft:%s_door[facing=east,half=%s,hinge=left,open=%s,powered=false]" % (
        kind,
        half,
        "true" if is_open else "false",
    )


DOORS = {
    "dark-closed": ("dark_oak", False),
    "dark-open": ("dark_oak", True),
    "oak-closed": ("oak", False),
    "none": None,
}
DOOR_LOWER, DOOR_UPPER = (11, 1, 6), (11, 2, 6)
WARM_CELL, CHAIN_CELL, SOUL_CELL = (13, 3, 6), (13, 4, 6), (4, 1, 9)
WARM_CENTRE = (13.5, 3.4, 6.5)  # hanging lantern body
SOUL_CENTRE = (4.5, 1.35, 9.5)  # standing lantern body
COW_FEET = (11.5, 1.0, 6.5)  # in the bare doorway, NoAI, facing west (yaw 90)
COW_BOX = ((10.75, 1.0, 6.03), (12.25, 2.45, 6.97))  # conservative model box for camera rays
COW_HITBOX = ((11.05, 1.0, 6.05), (11.95, 2.4, 6.95))  # vanilla 0.9 x 1.4 hitbox for light paths
HOUSE_INTERIOR = ((0, 0, 0), (19, 6, 13))  # entity census volume: whole house incl. walls
DYNAMIC = (DOOR_LOWER, DOOR_UPPER, WARM_CELL, SOUL_CELL)


def _static():
    g = {}

    def put(x0, x1, y0, y1, z0, z1, block):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    g[x, y, z] = block

    # floor
    put(0, 18, 0, 0, 0, 12, PLINTH)
    put(1, 10, 0, 0, 1, 11, OAK_FLOOR)
    put(12, 17, 0, 0, 1, 11, SPRUCE_FLOOR)
    put(4, 10, 0, 0, 5, 7, WHITE)  # warm receiver runner along the doorway axis
    put(5, 6, 0, 0, 9, 10, STONE)  # soul receiver
    # walls: stone plinth course, spruce above
    for x0, x1, z0, z1 in ((0, 0, 0, 12), (18, 18, 0, 12), (0, 18, 0, 0), (0, 18, 12, 12), (11, 11, 0, 12)):
        put(x0, x1, 1, 1, z0, z1, PLINTH)
        put(x0, x1, 2, 4, z0, z1, WALL)
    for x, z in ((0, 0), (0, 12), (18, 0), (18, 12), (11, 0), (11, 12)):
        put(x, x, 1, 4, z, z, POST)
    put(11, 11, 1, 4, 5, 5, FRAME)
    put(11, 11, 1, 4, 7, 7, FRAME)
    # windows
    put(0, 0, 2, 3, 2, 3, PANE_NS)  # west, Room A: low Sun
    put(3, 4, 2, 3, 12, 12, PANE_EW)  # south, Room A: sky only
    # ceiling, beams, roof with overhang
    put(0, 18, 5, 5, 0, 12, CEIL)
    for x in (3, 7, 14):
        put(x, x, 5, 5, 0, 12, BEAM)
    put(-1, 19, 6, 6, -1, 13, ROOF)
    # furniture
    put(6, 8, 1, 2, 11, 11, "minecraft:bookshelf")
    put(9, 9, 1, 1, 11, 11, "minecraft:barrel[facing=up,open=false]")
    put(9, 9, 2, 2, 11, 11, "minecraft:potted_red_tulip")
    put(17, 17, 1, 2, 9, 11, "minecraft:bookshelf")
    put(16, 16, 1, 1, 1, 1, "minecraft:crafting_table")
    put(17, 17, 1, 1, 1, 2, "minecraft:barrel[facing=up,open=false]")
    put(*[c for c in CHAIN_CELL for _ in (0, 1)], CHAIN)
    # doorway and lamp cells are dynamic: start as air
    for c in DYNAMIC:
        g[c] = AIR
    return g


STATIC = _static()

# Eye positions (local metres)
POSES = {
    # north-west corner of Room A looking south-east across the receivers to the doorway
    "main": dict(eye=(1.6, 3.3, 1.7), yaw=-58.0, pitch=17.0),
    # south-west user view: window strip, doorway, soul lantern in the foreground
    "wide": dict(eye=(1.7, 3.0, 10.6), yaw=-118.0, pitch=12.0),
}

# (name, door, warm, soul, cow, pose)
ROLES = [
    ("wide-open-both", "dark-open", True, True, False, "wide"),
    ("closed-warm", "dark-closed", True, False, False, "main"),
    ("open-warm", "dark-open", True, False, False, "main"),
    ("off-closed", "dark-closed", False, False, False, "main"),
    ("off-open", "dark-open", False, False, False, "main"),
    ("closed-soul", "dark-closed", False, True, False, "main"),
    ("open-soul", "dark-open", False, True, False, "main"),
    ("closed-both", "dark-closed", True, True, False, "main"),
    ("open-both", "dark-open", True, True, False, "main"),
    ("nodoor-warm", "none", True, False, False, "main"),
    ("nodoor-off", "none", False, False, False, "main"),
    ("oak-warm", "oak-closed", True, False, False, "main"),
    ("oak-off", "oak-closed", False, False, False, "main"),
    ("cow-warm", "none", True, False, True, "main"),
    ("cow-off", "none", False, False, True, "main"),
    ("open-repeat", "dark-open", True, False, False, "main"),
    ("returned-closed", "dark-closed", True, False, False, "main"),
    ("wide-closed-both", "dark-closed", True, True, False, "wide"),
]
ROLE_NAMES = [r[0] for r in ROLES]
PURPOSE = {
    "closed-warm": "warm lantern only, dark oak door closed",
    "open-warm": "warm lantern only, dark oak door open",
    "off-closed": "both lamps removed (air), door closed: Sun/sky baseline",
    "off-open": "both lamps removed (air), door open: Sun/sky baseline",
    "closed-soul": "soul lantern only, door closed",
    "open-soul": "soul lantern only, door open",
    "closed-both": "both lamps, door closed",
    "open-both": "both lamps, door open",
    "nodoor-warm": "warm only, doorway cells air (no door)",
    "nodoor-off": "no door, both lamps removed",
    "oak-warm": "warm only, closed oak door (texture cut-outs)",
    "oak-off": "closed oak door, both lamps removed",
    "cow-warm": "warm only, no door, NoAI cow standing in the doorway",
    "cow-off": "cow in the doorway, both lamps removed",
    "open-repeat": "repeat of open-warm with the same fixed camera",
    "returned-closed": "closed-warm again, entered directly from open-repeat",
    "wide-open-both": "user-facing view, door open, both lamps",
    "wide-closed-both": "user-facing view, door closed, both lamps",
}

# Named reception points on the floor top (y=1) / wall, sampled in every main-pose role.
RECEIVERS = [
    ("warm", (9.0, 1.0, 6.5), WHITE),
    ("warm-near", (9.8, 1.0, 6.8), WHITE),
    ("far", (5.5, 1.0, 6.5), WHITE),  # reached only through the upper door half (oak cut-outs)
    ("soul", (5.9, 1.0, 9.9), STONE),
    ("sun", (7.0, 1.0, 3.0), OAK_FLOOR),
    ("north-wall", (8.5, 3.6, 1.0), WALL),
]


def role(name):
    n, door_kind, warm, soul, cow, pose = ROLES[ROLE_NAMES.index(name)]
    return dict(name=n, door=door_kind, warm=warm, soul=soul, cow=cow, pose=pose, purpose=PURPOSE[n])


def dynamic_blocks(r):
    d = DOORS[r["door"]]
    return {
        DOOR_LOWER: door(d[0], "lower", d[1]) if d else AIR,
        DOOR_UPPER: door(d[0], "upper", d[1]) if d else AIR,
        WARM_CELL: WARM if r["warm"] else AIR,
        SOUL_CELL: SOUL if r["soul"] else AIR,
    }


def cells(r):
    grid = {
        (x, y, z): AIR
        for x in range(LO[0], HI[0] + 1)
        for y in range(LO[1], HI[1] + 1)
        for z in range(LO[2], HI[2] + 1)
    }
    for c, b in STATIC.items():
        assert c in grid, ("static cell outside reserve", c)
        grid[c] = b
    grid.update(dynamic_blocks(r))
    return grid


def world(p):
    return tuple(o + v for o, v in zip(ORIGIN, p))


def feet(pose):
    x, y, z = pose["eye"]
    return world((x, y - EYE, z))


def block_id(b):
    return b.split("[", 1)[0]


# ------------------------------------------------------------------ ray casting


def seg_box(a, b, lo, hi):
    """Parametric entry t in [0,1] of segment a->b into the open box, or None."""
    d = [b[i] - a[i] for i in range(3)]
    t0, t1 = 0.0, 1.0
    for i in range(3):
        if abs(d[i]) < 1e-12:
            if not lo[i] < a[i] < hi[i]:
                return None
            continue
        p, q = (lo[i] - a[i]) / d[i], (hi[i] - a[i]) / d[i]
        t0, t1 = max(t0, min(p, q)), min(t1, max(p, q))
    return t0 if t0 < t1 else None


# Sub-block shapes in 1/16 units (lo, hi) for the light-path tests.
PANEL = {  # door panels: facing=east, hinge=left
    False: ((0, 0, 0), (3, 16, 16)),  # closed: west 3/16 of the cell
    True: ((0, 0, 0), (16, 16, 3)),  # open (hinge left -> SOUTH_AABB): north 3/16
}


def occluders(r, light=False, cow_box=True):
    """Boxes (lo, hi) for opaque geometry. light=True uses real door panels and treats
    panes/lanterns/chains/potted plants as non-occluding; otherwise every non-air cell
    is a full box (conservative for camera rays)."""
    out = []
    for c, b in cells(r).items():
        if b == AIR:
            continue
        lo, hi = c, tuple(v + 1 for v in c)
        if light:
            i = block_id(b)
            if i in ("minecraft:glass_pane", "minecraft:lantern", "minecraft:soul_lantern",
                     "minecraft:chain", "minecraft:potted_red_tulip"):
                continue
            if i.endswith("_door"):
                s = PANEL["open=true" in b]
                lo = tuple(c[k] + s[0][k] / 16 for k in range(3))
                hi = tuple(c[k] + s[1][k] / 16 for k in range(3))
        out.append((lo, hi, c, b))
    if r["cow"] and cow_box:
        b = COW_HITBOX if light else COW_BOX
        out.append((b[0], b[1], None, "cow"))
    return out


def first_hit(r, pose, px, py, boxes=None):
    d = ray(pose, px, py)
    e = pose["eye"]
    far = tuple(e[i] + d[i] * 60 for i in range(3))
    best = (math.inf, None, None)
    for lo, hi, c, b in boxes if boxes is not None else occluders(r):
        t = seg_box(e, far, lo, hi)
        if t is not None and t < best[0]:
            best = (t, b, c)
    t = best[0]
    return best[1], best[2], tuple(e[i] + (far[i] - e[i]) * t for i in range(3))


def clear(a, b, boxes, eps=1e-6):
    """True when the open segment a->b misses every box (endpoints excluded)."""
    for lo, hi, _, _ in boxes:
        t = seg_box(a, b, lo, hi)
        if t is not None and eps < t < 1 - eps:
            return False
    return True


def sun_direction(time=TIME):
    d = (time / 24000.0 - 0.25) % 1.0
    e = 0.5 - math.cos(d * math.pi) / 2
    a = (d * 2 + e) / 3 * 2 * math.pi
    return (-math.sin(a), math.cos(a), 0.0)


def samples(r):
    """Projected receiver patches for main-pose roles; empty for user-facing views."""
    if r["pose"] != "main":
        return []
    pose = POSES[r["pose"]]
    boxes = occluders(r)
    out = []
    for name, point, block in RECEIVERS:
        u, v, depth = project(pose, point)
        cx, cy = math.floor(u), math.floor(v)
        h = PATCH // 2
        rect = [cx - h, cy - h, cx + h + 1, cy + h + 1]
        corners = [(rect[0], rect[1]), (rect[2], rect[1]), (rect[0], rect[3]), (rect[2], rect[3])]
        footprint = []
        for px, py in corners + [(u, v)]:
            b, c, p = first_hit(r, pose, px, py, boxes)
            footprint.append(dict(pixel=[px, py], block=b, cell=list(c) if c else None, local=[round(q, 4) for q in p]))
        out.append(
            dict(name=name, local=list(point), world=list(world(point)), expectBlock=block,
                 projected=[round(u, 3), round(v, 3)], depth=round(depth, 4), patch=rect, footprint=footprint)
        )
    return out


def pose_record(name):
    p = POSES[name]
    return dict(name=name, eyeLocal=list(p["eye"]), eyeWorld=list(world(p["eye"])), feetWorld=list(feet(p)),
                yaw=p["yaw"], pitch=p["pitch"], fovVertical=FOV, width=WIDTH, height=HEIGHT)


def light_paths(r):
    """Geometric (shape-aware, unlit-by-bounce) visibility of each lamp from each receiver."""
    boxes = occluders(r, light=True)
    sun = sun_direction()
    out = {}
    for name, p, _ in RECEIVERS:
        q = (p[0], p[1] + 1e-4, p[2] + (1e-4 if name == "north-wall" else 0))
        row = dict(
            warm=bool(r["warm"]) and clear(q, WARM_CENTRE, boxes),
            soul=bool(r["soul"]) and clear(q, SOUL_CENTRE, boxes),
            sun=clear(q, tuple(q[i] + sun[i] * 40 for i in range(3)), boxes),
        )
        out[name] = row
    return out


def selftest():
    import itertools

    report = {}
    assert CELLS == 21 * 9 * 15
    assert (WIDTH, HEIGHT, FOV) == (1280, 720, 65)
    for name in ROLE_NAMES:
        r = role(name)
        g = cells(r)
        assert len(g) == CELLS
        pose = POSES[r["pose"]]
        e = pose["eye"]
        assert g[tuple(math.floor(c) for c in e)] == AIR, name
        f = feet(pose)
        assert g[tuple(math.floor(c - o) for c, o in zip(f, ORIGIN))] == AIR, name + ": feet in a block"
        boxes = occluders(r)
        clearance = min(
            math.sqrt(sum(max(lo[a] - e[a], 0, e[a] - hi[a]) ** 2 for a in range(3))) for lo, hi, _, _ in boxes
        )
        assert clearance >= 0.12, (name, clearance)
        # Neither lantern is directly visible from either camera, even through a bare doorway.
        bare = occluders(dict(r, door="none", cow=False), light=True)
        assert not clear(e, WARM_CENTRE, bare), name + ": warm lantern visible"
        for s in samples(r):
            x0, y0, x1, y1 = s["patch"]
            assert 30 <= x0 and x1 <= WIDTH - 30 and 30 <= y0 and y1 <= HEIGHT - 30, (name, s["name"], s["patch"])
            for fp in s["footprint"]:
                assert fp["block"] == s["expectBlock"], (name, s["name"], fp)
            assert max(abs(a - b) for a, b in zip(s["footprint"][-1]["local"], s["local"])) < 1e-6, (name, s)
        report[name] = light_paths(r)
    # identical patches for every main-pose role
    base = [s["patch"] for s in samples(role("open-warm"))]
    for name in ROLE_NAMES:
        if role(name)["pose"] == "main":
            assert [s["patch"] for s in samples(role(name))] == base, name
    # light-path expectations
    lp = report
    assert lp["open-warm"]["warm"]["warm"] and lp["open-warm"]["warm-near"]["warm"]
    assert lp["nodoor-warm"]["warm"]["warm"]
    assert not lp["closed-warm"]["warm"]["warm"] and not lp["closed-warm"]["warm-near"]["warm"]
    assert not lp["open-warm"]["north-wall"]["warm"] and not lp["open-warm"]["soul"]["warm"]
    assert lp["open-soul"]["soul"]["soul"] and lp["closed-soul"]["soul"]["soul"]
    assert all(lp[n]["sun"]["sun"] for n in ROLE_NAMES if role(n)["pose"] == "main")
    assert not any(lp[n][k]["sun"] for n in ROLE_NAMES for k in ("warm", "soul", "north-wall"))
    # the cow shadows part of the receiver: at least one warm sample point is blocked
    cow = occluders(role("cow-warm"), light=True)
    pts = [(x, 1.0001, z) for x, z in itertools.product((7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5), (5.5, 6.0, 6.5, 7.0, 7.5))]
    nocow = occluders(role("nodoor-warm"), light=True)
    lit = sum(clear(p, WARM_CENTRE, nocow) for p in pts)
    shaded = sum(clear(p, WARM_CENTRE, nocow) and not clear(p, WARM_CENTRE, cow) for p in pts)
    assert shaded > 0, "cow casts no shadow on the receiver tiles"
    report["cowShadowGrid"] = dict(points=len(pts), litWithoutCow=lit, shadedByCow=shaded)
    report["sunDirection"] = [round(v, 4) for v in sun_direction()]
    report["sunElevationDeg"] = round(math.degrees(math.asin(sun_direction()[1])), 2)
    return report


if __name__ == "__main__":
    import json

    rep = selftest()
    for s in samples(role("open-warm")):
        print(s["name"], s["projected"], s["patch"], s["depth"])
    print(json.dumps({k: rep[k] for k in ("open-warm", "closed-warm", "cow-warm", "cowShadowGrid", "sunElevationDeg")}, indent=1))
    print("house selftest ok")
