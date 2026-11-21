"""Native Minecraft geometry for the one-bounce fixture in reference.py (stdlib only).

Local block coordinates match reference.py metres: the white receiver face is z=0 (cells z=-1),
the one-bounce east face is x=12 (cells x=12, y 0..6, z 0..9), the hooded lantern cell is (9,2,4).
World = ORIGIN + local. Cells are integer lower corners; boxes are (lo, hi) with hi exclusive.

Two deliberate translations of reference.py, both re-verified against its own integrator in selftest():
  first-leg baffle  reference (10,0,1)-(11,7,9)  -> native x=10, z 2..8  (box (10,0,2)-(11,7,9))
  second-leg baffle reference (6,0,1)-(12,7,2)   -> native z=2, x 6..11 (box (6,0,2)-(12,7,3))
so that the receiver camera at z=1.85 sits in air and never looks through either baffle.
"""

import math

ORIGIN = (400, 150, -410)
LO, HI = (-1, -1, -1), (12, 7, 10)  # inclusive reserved cell bounds
CELLS = (HI[0] - LO[0] + 1) * (HI[1] - LO[1] + 1) * (HI[2] - LO[2] + 1)
WIDTH, HEIGHT = 1280, 720
FOV = 65  # vertical degrees; options.txt fov = (FOV - 70) / 40, fovEffectScale 0
EYE = 1.62  # standing/spectator eye height
PATCH = 11  # odd square patch in pixels
PLAYER = "AqualumenOptics"

BLACK = "minecraft:black_concrete"
WHITE = "minecraft:white_concrete"
AIR = "minecraft:air"
EAST = {
    "red": "minecraft:red_concrete",
    "neutral": "minecraft:polished_deepslate",
    "black": BLACK,
}
LAMP = {
    "lantern": "minecraft:lantern[hanging=false,waterlogged=false]",
    "soul": "minecraft:soul_lantern[hanging=false,waterlogged=false]",
    "off": AIR,
}
RECEIVERS = ((8.0, 2.5, 0.0), (9.5, 2.5, 0.0), (11.0, 2.5, 0.0))
LAMP_CELL = (9, 2, 4)
HOOD_CELLS = ((9, 2, 3), (9, 2, 5), (8, 2, 4), (9, 1, 4), (9, 3, 4))  # N, S, W, down (support), up


def box(x0, x1, y0, y1, z0, z1):
    """Inclusive cell ranges -> (lo, hi) box."""
    return ((x0, y0, z0), (x1 + 1, y1 + 1, z1 + 1))


SHELL = [
    (box(-1, 12, -1, -1, -1, 10), BLACK),  # floor
    (box(-1, 12, 7, 7, -1, 10), BLACK),  # ceiling
    (box(-1, -1, 0, 6, -1, 10), BLACK),  # west
    (box(0, 11, 0, 6, 10, 10), BLACK),  # south
    (box(12, 12, 0, 6, -1, -1), BLACK),  # north-east edge column
    (box(12, 12, 0, 6, 10, 10), BLACK),  # south-east edge column
    (box(0, 11, 0, 6, -1, -1), WHITE),  # receiver wall, face z=0
] + [(box(x, x, y, y, z, z), BLACK) for x, y, z in HOOD_CELLS]
EAST_BOX = box(12, 12, 0, 6, 0, 9)
FIRST_BOX = box(10, 10, 0, 6, 2, 8)
SECOND_BOX = box(6, 11, 0, 6, 2, 2)
LAMP_BOX = box(*[c for c in LAMP_CELL for _ in (0, 1)])

# Eye positions (local metres) with Minecraft yaw/pitch: yaw 180 faces north (-z), pitch>0 looks down.
POSES = {
    "receiver": dict(eye=(9.5, 2.5, 1.85), yaw=180.0, pitch=0.0),
    # translated 0.2 m east, 0.5 m up, 0.15 m closer; turned 4 deg west and 4 deg down
    "moved": dict(eye=(9.7, 3.0, 1.7), yaw=176.0, pitch=4.0),
    # side view from the south-west corner: sees the lit east face, hood and white wall together
    "wide": dict(eye=(1.2, 4.6, 9.2), yaw=-128.0, pitch=16.0),
}
ROLES = [
    # name, east, lamp, first, second, pose, purpose
    ("red", "red", "lantern", False, False, "receiver", "one-bounce from red east face"),
    ("neutral", "neutral", "lantern", False, False, "receiver", "matched-luminance neutral face"),
    ("black", "black", "lantern", False, False, "receiver", "near-zero reflector"),
    ("off", "red", "off", False, False, "receiver", "lamp removed (air)"),
    ("first-block", "red", "lantern", True, False, "receiver", "lamp->east leg blocked"),
    ("second-block", "red", "lantern", False, True, "receiver", "east->receiver leg blocked"),
    ("soul", "red", "soul", False, False, "receiver", "cyan emitter on red face"),
    ("moved", "red", "lantern", False, False, "moved", "camera moved/rotated, same receivers"),
    ("red-repeat", "red", "lantern", False, False, "receiver", "return to red after all toggles"),
    ("wide-red", "red", "lantern", False, False, "wide", "user-facing red face side view"),
    ("wide-neutral", "neutral", "lantern", False, False, "wide", "user-facing neutral side view"),
]
ROLE_NAMES = [r[0] for r in ROLES]


def role(name):
    n, east, lamp, first, second, pose, purpose = ROLES[ROLE_NAMES.index(name)]
    return dict(name=n, east=east, lamp=lamp, first=first, second=second, pose=pose, purpose=purpose)


def solids(r):
    """Ordered (box, block) list for a role; later entries win when expanded to cells."""
    out = list(SHELL) + [(EAST_BOX, EAST[r["east"]])]
    if r["lamp"] != "off":
        out.append((LAMP_BOX, LAMP[r["lamp"]]))
    if r["first"]:
        out.append((FIRST_BOX, BLACK))
    if r["second"]:
        out.append((SECOND_BOX, BLACK))
    return out


def cells(r):
    grid = {
        (x, y, z): AIR
        for x in range(LO[0], HI[0] + 1)
        for y in range(LO[1], HI[1] + 1)
        for z in range(LO[2], HI[2] + 1)
    }
    for (lo, hi), block in solids(r):
        for x in range(lo[0], hi[0]):
            for y in range(lo[1], hi[1]):
                for z in range(lo[2], hi[2]):
                    assert (x, y, z) in grid, "solid outside reserved bounds"
                    grid[x, y, z] = block
    return grid


def world(p):
    return tuple(o + v for o, v in zip(ORIGIN, p))


def fmt(v):
    return ("%.4f" % v).rstrip("0").rstrip(".")


def feet(pose):
    x, y, z = pose["eye"]
    return world((x, y - EYE, z))


def basis(yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    f = (-math.sin(y) * math.cos(p), -math.sin(p), math.cos(y) * math.cos(p))
    r = (-math.cos(y), 0.0, -math.sin(y))
    u = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
    return f, r, u


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


TAN = math.tan(math.radians(FOV) / 2)
ASPECT = WIDTH / HEIGHT


def project(pose, point):
    """Continuous window coordinates (u right, v down, pixel edges at integers) and view depth."""
    f, r, u = basis(pose["yaw"], pose["pitch"])
    d = [a - b for a, b in zip(point, pose["eye"])]
    depth = dot(d, f)
    nx = dot(d, r) / depth / (TAN * ASPECT) if depth > 0 else math.inf
    ny = dot(d, u) / depth / TAN if depth > 0 else math.inf
    return (nx + 1) * WIDTH / 2, (1 - ny) * HEIGHT / 2, depth


def ray(pose, px, py):
    f, r, u = basis(pose["yaw"], pose["pitch"])
    nx, ny = px / WIDTH * 2 - 1, 1 - py / HEIGHT * 2
    return tuple(f[i] + r[i] * nx * TAN * ASPECT + u[i] * ny * TAN for i in range(3))


def hit(origin, direction, lo, hi):
    t0, t1 = 0.0, math.inf
    for a in range(3):
        if abs(direction[a]) < 1e-12:
            if not lo[a] <= origin[a] <= hi[a]:
                return None
            continue
        p, q = (lo[a] - origin[a]) / direction[a], (hi[a] - origin[a]) / direction[a]
        t0, t1 = max(t0, min(p, q)), min(t1, max(p, q))
    return t0 if t0 <= t1 else None


def first_hit(r, pose, px, py):
    d = ray(pose, px, py)
    best = (math.inf, None, None)
    for (lo, hi), block in solids(r):
        t = hit(pose["eye"], d, lo, hi)
        if t is not None and t < best[0]:
            best = (t, block, (lo, hi))
    t = best[0]
    return best[1], best[2], tuple(pose["eye"][i] + d[i] * t for i in range(3))


def samples(r):
    """Projected receiver centres and verified PATCH x PATCH windows (receiver/moved poses only)."""
    pose = POSES[r["pose"]]
    out = []
    for point in RECEIVERS:
        u, v, depth = project(pose, point)
        cx, cy = math.floor(u), math.floor(v)
        h = PATCH // 2
        rect = [cx - h, cy - h, cx + h + 1, cy + h + 1]  # x0, y0, x1, y1 (exclusive)
        corners = [(rect[0], rect[1]), (rect[2], rect[1]), (rect[0], rect[3]), (rect[2], rect[3])]
        footprint = []
        for px, py in corners + [(u, v)]:
            block, _, p = first_hit(r, pose, px, py)
            footprint.append(dict(pixel=[px, py], block=block, local=[round(c, 4) for c in p]))
        out.append(
            dict(
                local=list(point),
                world=list(world(point)),
                projected=[round(u, 3), round(v, 3)],
                depth=round(depth, 4),
                patch=rect,
                footprint=footprint,
            )
        )
    return out


def pose_record(name):
    p = POSES[name]
    return dict(
        name=name,
        eyeLocal=list(p["eye"]),
        eyeWorld=list(world(p["eye"])),
        feetWorld=list(feet(p)),
        yaw=p["yaw"],
        pitch=p["pitch"],
        fovVertical=FOV,
        width=WIDTH,
        height=HEIGHT,
    )


def eye_clearance(r, pose):
    e = pose["eye"]
    best = math.inf
    for (lo, hi), _ in solids(r):
        d = math.sqrt(sum(max(lo[a] - e[a], 0, e[a] - hi[a]) ** 2 for a in range(3)))
        best = min(best, d)
    return best


def visible_blocks(r, step=16):
    pose = POSES[r["pose"]]
    seen = {}
    xs = list(range(0, WIDTH, step)) + [WIDTH - 0.5]
    ys = list(range(0, HEIGHT, step)) + [HEIGHT - 0.5]
    for py in [max(y, 0.5) for y in ys]:
        for px in [max(x, 0.5) for x in xs]:
            block, b, _ = first_hit(r, pose, px, py)
            key = (block, b)
            seen[key] = seen.get(key, 0) + 1
    return seen


def selftest(reference=None):
    report = {}
    for name in ROLE_NAMES:
        r = role(name)
        grid = cells(r)
        assert len(grid) == CELLS == 1512
        pose = POSES[r["pose"]]
        e = pose["eye"]
        assert grid[tuple(math.floor(c) for c in e)] == AIR, name + ": eye inside a block"
        clearance = eye_clearance(r, pose)
        assert clearance >= 0.12, (name, clearance)  # > near plane 0.05 and in-wall probe margin
        # feet-to-eye column stays inside the room interior
        assert 0 < e[1] - EYE and e[1] < 7 and 0 < e[0] < 12 and 0 < e[2] < 10
        seen = visible_blocks(r)
        names = {k[0] for k in seen}
        if r["pose"] in ("receiver", "moved"):
            east = [k for k in seen if k[1] == EAST_BOX]
            assert not east, name + ": east face visible from receiver camera"
            assert not any(k[1] in (LAMP_BOX, FIRST_BOX, SECOND_BOX) for k in seen), name
            assert all(k[1] in [b for b, _ in SHELL] for k in seen), name
            for s in samples(r):
                x0, y0, x1, y1 = s["patch"]
                assert 40 <= x0 and x1 <= WIDTH - 40 and 40 <= y0 and y1 <= HEIGHT - 40, (name, s)
                for f in s["footprint"]:
                    assert f["block"] == WHITE, (name, f)
                    x, y, z = f["local"]
                    assert abs(z) < 1e-9 and 0.3 < x < 11.7 and 0.3 < y < 6.7, (name, f)
                # receiver point itself is the first surface hit at its projected centre
                assert max(abs(a - b) for a, b in zip(s["footprint"][-1]["local"], s["local"])) < 1e-6
                assert s["depth"] > 1.0
            # frustum margin to the east face: corners of x=12 face, z 0..2 nearest strip
            for y in (0, 7):
                for z in (0, 10):
                    u, v, depth = project(pose, (12, y, z))
                    assert depth <= 0 or u > WIDTH * 1.08, (name, u)
        else:
            assert EAST[r["east"]] in names and WHITE in names and BLACK in names, name
            assert sum(n for k, n in seen.items() if k[1] == EAST_BOX) > 120, name
            assert sum(n for k, n in seen.items() if k[0] == WHITE) > 120, name
            hood = [b for b, _ in SHELL[7:]]
            assert any(k[1] in hood for k in seen), name + ": hood not in side view"
        report[name] = {"%s" % k[0]: n for k, n in seen.items()}
    # Every receiver role shares identical receiver projection, except the deliberate moved camera.
    base = [s["patch"] for s in samples(role("red"))]
    for name in ROLE_NAMES:
        r = role(name)
        if r["pose"] == "receiver":
            assert [s["patch"] for s in samples(r)] == base
    assert [s["patch"] for s in samples(role("moved"))] != base
    if reference is not None:
        crosscheck(reference)
    return report


def crosscheck(ref):
    import numpy as np

    as_box = lambda c: (tuple(c), tuple(v + 1 for v in c))
    assert sorted(ref.HOOD) == sorted(as_box(c) for c in HOOD_CELLS)
    assert np.allclose(ref.SOURCE, [c + 0.5 for c in LAMP_CELL])
    assert np.allclose(ref.RECEIVERS, RECEIVERS)
    assert EAST_BOX == ((12, 0, 0), (13, 7, 10))  # reference integrates face x=12, y 0..7, z 0..10
    # Room shell lies entirely outside the interior [0,12]x[0,7]x[0,10] the reference integrates through.
    for (lo, hi), _ in SHELL[:7]:
        assert any(hi[a] <= (0, 0, 0)[a] or lo[a] >= (12, 7, 10)[a] for a in range(3)), (lo, hi)
    hood = list(ref.HOOD)
    base = ref.transport(24, hood)
    assert np.all(base > 0)
    first = ref.transport(24, hood + [FIRST_BOX])
    second = ref.transport(24, hood + [SECOND_BOX])
    assert np.all(first == 0), first
    assert np.all(second == 0), second
    # Receiver cameras do not occlude anything the reference integrates (camera has no geometry), and
    # the sight lines from every receiver camera to every receiver are unblocked by every role's solids.
    for name in ROLE_NAMES:
        r = role(name)
        if r["pose"] == "wide":
            continue
        boxes = [b for b, blk in solids(r) if blk != WHITE]
        eye = np.array(POSES[r["pose"]]["eye"])
        targets = np.array(RECEIVERS) + [0, 0, 1e-6]
        assert not ref.blocked(eye, targets, boxes).any(), name
    return dict(base=base.tolist(), first=first.tolist(), second=second.tolist())


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    reference = None
    try:
        import numpy  # noqa: F401

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import reference
    except ImportError:
        print("numpy unavailable: skipped reference.py cross-check", file=sys.stderr)
    seen = selftest(reference)
    if reference is not None:
        print(json.dumps(crosscheck(reference)))
    for name in ROLE_NAMES:
        r = role(name)
        line = name + " " + r["pose"]
        if r["pose"] != "wide":
            line += " " + json.dumps([s["projected"] for s in samples(r)])
        print(line, json.dumps(seen[name], sort_keys=True))
    print("fixture selftest ok", "with" if reference else "without", "reference cross-check")
