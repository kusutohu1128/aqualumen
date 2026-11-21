"""Covered stone patio with a solid eave over the open sea (stdlib only).

Local block coordinates, world = ORIGIN + local; cells are integer lower corners, boxes (lo, hi) hi-exclusive.
x east, y up, z south. Floor cells y=0 (walking surface y=1). Roof cells y=5 cover z 0..5, so the eave
(drip) line is the plane z=6: floor columns z<=5 are sheltered by a solid block, z>=6 see the sky.

Two matched floor strips cross the eave line: minecraft:stone (x 3..5) and minecraft:smooth_stone (x 7..9),
z 1..11, framed by polished deepslate. A real warm lantern hangs from the eave row at cell (6,4,5): every
matched sheltered/exposed pair (z=4.5/6.5 near, z=2.5/8.5 far) sits at the same horizontal distance from
it. Pose A puts the lantern's mirror reflection on the exposed stone strip, pose B on exposed smooth stone;
both see every patch, so the same places are compared from two angles.
"""

import math

ORIGIN = (400, 63, -440)  # open ocean, water surface at y=63.0; biome checked from the saved region file
LO, HI = (-1, 0, -1), (13, 7, 13)  # inclusive reserved cell bounds (all air in the source world)
CELLS = (HI[0] - LO[0] + 1) * (HI[1] - LO[1] + 1) * (HI[2] - LO[2] + 1)
WIDTH, HEIGHT = 1280, 720
FOV = 70  # vertical degrees; options.txt fov = (FOV - 70) / 40 = 0, fovEffectScale 0
EYE = 1.62
PATCH = 11
PLAYER = "AqualumenRain"
TIME = 13000  # dusk, sun just below the western horizon
FLOOR_TOP = 1.0
EAVE_Z = 6.0

AIR = "minecraft:air"
STONE = "minecraft:stone"
SMOOTH = "minecraft:smooth_stone"
BORDER = "minecraft:polished_deepslate"
ROOF = "minecraft:dark_oak_planks"
WALL = "minecraft:spruce_planks"
POST = "minecraft:stripped_spruce_log[axis=y]"
LANTERN = "minecraft:lantern[hanging=true,waterlogged=false]"
LAMP = {"on": LANTERN, "off": AIR}
LAMP_CELL = (6, 4, 5)
# Hanging lantern model: body 5/16..12/16 in x/z, 1/16..8/16 high, handle above. Glow centre:
LAMP_CENTRE = (6.5, 4.0 + 4.5 / 16, 5.5)


def box(x0, x1, y0, y1, z0, z1):
    return ((x0, y0, z0), (x1 + 1, y1 + 1, z1 + 1))


STONE_BOX = box(3, 5, 0, 0, 1, 11)
SMOOTH_BOX = box(7, 9, 0, 0, 1, 11)
ROOF_BOX = box(0, 12, 5, 5, 0, 5)
SHELL = [
    (box(0, 12, 0, 0, 0, 12), BORDER),  # floor frame (strips overwrite)
    (STONE_BOX, STONE),
    (SMOOTH_BOX, SMOOTH),
    (box(0, 12, 1, 4, 0, 0), WALL),  # back wall, face z=1
    (box(0, 0, 1, 4, 5, 5), POST),  # front posts under the eave row
    (box(12, 12, 1, 4, 5, 5), POST),
    (ROOF_BOX, ROOF),
]
LAMP_BOX = box(*[c for c in LAMP_CELL for _ in (0, 1)])
STATIC_NAMES = ["frame", "stone", "smooth", "wall", "post-w", "post-e", "roof"]


def solids(lamp):
    out = list(SHELL)
    if lamp == "on":
        out.append((LAMP_BOX, LANTERN))
    return out


def cells(lamp):
    grid = {(x, y, z): AIR for x in range(LO[0], HI[0] + 1) for y in range(LO[1], HI[1] + 1) for z in range(LO[2], HI[2] + 1)}
    for (lo, hi), block in solids(lamp):
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


def basis(yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    f = (-math.sin(y) * math.cos(p), -math.sin(p), math.cos(y) * math.cos(p))
    r = (-math.cos(y), 0.0, -math.sin(y))
    u = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
    return f, r, u


def look(eye, target):
    d = [t - e for t, e in zip(target, eye)]
    yaw = math.degrees(math.atan2(-d[0], d[2]))
    pitch = math.degrees(-math.atan2(d[1], math.hypot(d[0], d[2])))
    return dict(eye=tuple(eye), yaw=round(yaw, 2), pitch=round(pitch, 2))


def mirror(eye, light=LAMP_CENTRE, plane=FLOOR_TOP):
    """Specular reflection point of `light` on the horizontal floor for a camera at `eye`."""
    image = (light[0], 2 * plane - light[1], light[2])
    t = (eye[1] - plane) / (eye[1] - image[1])
    return tuple(eye[i] + (image[i] - eye[i]) * t for i in range(3))


def eye_for_mirror(target_xz, eye_y, back):
    """Camera eye that reflects the lantern at floor point target_xz, `back` metres beyond it (+z side)."""
    lx, ly, lz = LAMP_CENTRE
    f = (eye_y - FLOOR_TOP) / ((eye_y - FLOOR_TOP) + (ly - FLOOR_TOP))
    # M = E + f (L - E)  =>  E = (M - f L) / (1 - f), horizontally
    return ((target_xz[0] - f * lx) / (1 - f), eye_y, (target_xz[1] - f * lz) / (1 - f))


EYE_Y = 3.8
MEASURE_POSES = ("a", "b")
_A = eye_for_mirror((4.5, 9.0), EYE_Y, None)
_B = eye_for_mirror((8.5, 9.0), EYE_Y, None)
POSES = {
    "a": look(_A, (6.5, 2.2, 3.0)),
    "b": look(_B, (6.5, 2.2, 3.0)),
    # production view from the sea, south-east and above the eave: whole patio, roof, lantern and rain
    "wide": look((15.2, 5.6, 16.4), (5.8, 1.8, 4.6)),
}
for _p in POSES.values():  # rounded so that the datapack tp and pose checks are exact
    _p["eye"] = tuple(round(v, 3) for v in _p["eye"])
    _p["yaw"] = round(_p["yaw"], 1)
    _p["pitch"] = round(_p["pitch"], 1)


def feet(pose):
    x, y, z = pose["eye"]
    return world((x, y - EYE, z))


TAN = math.tan(math.radians(FOV) / 2)
ASPECT = WIDTH / HEIGHT


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def project(pose, point):
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


def first_hit(lamp, origin, d):
    best = (math.inf, None, None)
    for b, block in solids(lamp):
        if block == LANTERN:  # treat the lantern by its model box only
            b = ((6 + 5 / 16, 4 + 1 / 16, 5 + 5 / 16), (6 + 11 / 16, 4 + 10 / 16, 5 + 11 / 16))
        t = hit(origin, d, *b)
        if t is not None and t < best[0] + 1e-9:  # coplanar: later entry wins, as in cells()
            best = (t, block, b)
    t = best[0]
    return best[1], best[2], (tuple(origin[i] + d[i] * t for i in range(3)) if t < math.inf else None)


# Fixed world places, measured from every pose. kind: material/exposure/lamp-distance role.
SAMPLES = [
    dict(name="stone-shelter-near", point=(4.5, FLOOR_TOP, 4.5), block=STONE, exposed=False, pair="stone-near"),
    dict(name="stone-exposed-near", point=(4.5, FLOOR_TOP, 6.5), block=STONE, exposed=True, pair="stone-near"),
    dict(name="stone-shelter-far", point=(4.5, FLOOR_TOP, 2.5), block=STONE, exposed=False, pair="stone-far"),
    dict(name="stone-exposed-far", point=(4.5, FLOOR_TOP, 8.5), block=STONE, exposed=True, pair="stone-far"),
    dict(name="smooth-shelter-near", point=(8.5, FLOOR_TOP, 4.5), block=SMOOTH, exposed=False, pair="smooth-near"),
    dict(name="smooth-exposed-near", point=(8.5, FLOOR_TOP, 6.5), block=SMOOTH, exposed=True, pair="smooth-near"),
    dict(name="smooth-shelter-far", point=(8.5, FLOOR_TOP, 2.5), block=SMOOTH, exposed=False, pair="smooth-far"),
    dict(name="smooth-exposed-far", point=(8.5, FLOOR_TOP, 8.5), block=SMOOTH, exposed=True, pair="smooth-far"),
    dict(name="stone-mirror-a", point=None, block=STONE, exposed=True, pair=None, mirrorOf="a"),
    dict(name="smooth-mirror-b", point=None, block=SMOOTH, exposed=True, pair=None, mirrorOf="b"),
    dict(name="wall-neutral-w", point=(2.0, 2.5, 1.0), block=WALL, exposed=False, pair=None),
    dict(name="wall-neutral-e", point=(11.0, 2.5, 1.0), block=WALL, exposed=False, pair=None),
    dict(name="frame-exposed", point=(6.5, FLOOR_TOP, 7.5), block=BORDER, exposed=True, pair="frame"),
    dict(name="frame-shelter", point=(6.5, FLOOR_TOP, 3.5), block=BORDER, exposed=False, pair="frame"),
]
for _s in SAMPLES:
    if _s.get("mirrorOf"):
        _s["point"] = tuple(round(v, 4) for v in mirror(POSES[_s["mirrorOf"]]["eye"]))


def samples(pose_name, lamp="on"):
    pose = POSES[pose_name]
    out = []
    for s in SAMPLES:
        u, v, depth = project(pose, s["point"])
        cx, cy = math.floor(u), math.floor(v)
        h = PATCH // 2
        rect = [cx - h, cy - h, cx + h + 1, cy + h + 1]
        corners = [(rect[0], rect[1]), (rect[2], rect[1]), (rect[0], rect[3]), (rect[2], rect[3])]
        footprint = []
        for px, py in corners + [(u, v)]:
            block, _, p = first_hit(lamp, pose["eye"], ray(pose, px, py))
            footprint.append(dict(pixel=[px, py], block=block, local=[round(c, 4) for c in p] if p else None))
        inside = 30 <= rect[0] and rect[2] <= WIDTH - 30 and 30 <= rect[1] and rect[3] <= HEIGHT - 30 and depth > 0
        valid = inside and all(f["block"] == s["block"] for f in footprint)
        out.append(dict(name=s["name"], local=list(s["point"]), world=list(world(s["point"])), block=s["block"],
                        exposed=s["exposed"], pair=s["pair"], projected=[round(u, 3), round(v, 3)],
                        depth=round(depth, 4), patch=rect, footprint=footprint, valid=valid))
    return out


def sky_column_clear(point):
    """Vertical ray from just above a floor point to the sky: no solid of the fixture in the way."""
    origin = (point[0], point[1] + 1e-3, point[2])
    blocker = first_hit("on", origin, (0.0, 1.0, 0.0))[0]
    return blocker is None


def pose_record(name):
    p = POSES[name]
    return dict(name=name, eyeLocal=[round(v, 4) for v in p["eye"]], eyeWorld=[round(v, 4) for v in world(p["eye"])],
                feetWorld=[round(v, 4) for v in feet(p)], yaw=p["yaw"], pitch=p["pitch"], fovVertical=FOV,
                width=WIDTH, height=HEIGHT)


def visible(pose_name, lamp="on", step=16):
    pose = POSES[pose_name]
    seen = {}
    for py in [max(y, 0.5) for y in range(0, HEIGHT, step)]:
        for px in [max(x, 0.5) for x in range(0, WIDTH, step)]:
            block = first_hit(lamp, pose["eye"], ray(pose, px, py))[0] or "sky/sea"
            seen[block] = seen.get(block, 0) + 1
    return seen


def selftest():
    rep = {}
    for lamp in ("on", "off"):
        g = cells(lamp)
        assert len(g) == CELLS == 1800
    # every sample: exposure follows the eave geometry; matched pairs share material and lamp distance
    pairs = {}
    for s in SAMPLES:
        assert sky_column_clear(s["point"]) == s["exposed"] or s["block"] == WALL, s["name"]
        if s["block"] in (STONE, SMOOTH, BORDER):
            assert abs(s["point"][1] - FLOOR_TOP) < 1e-9
            assert (s["point"][2] >= EAVE_Z) == s["exposed"], s["name"]
        if s["pair"]:
            pairs.setdefault(s["pair"], []).append(s)
    for name, (a, b) in pairs.items():
        assert a["block"] == b["block"] and a["exposed"] != b["exposed"], name
        da = math.dist(a["point"], LAMP_CENTRE)
        db = math.dist(b["point"], LAMP_CENTRE)
        assert abs(da - db) < 1e-9, (name, da, db)
        assert min(abs(a["point"][2] - EAVE_Z), abs(b["point"][2] - EAVE_Z)) >= 0.5
    # mirror points land on the intended exposed strip, well inside it
    for s, lo, hi in ((SAMPLES[8], STONE_BOX[0], STONE_BOX[1]), (SAMPLES[9], SMOOTH_BOX[0], SMOOTH_BOX[1])):
        x, y, z = s["point"]
        assert lo[0] + 0.6 < x < hi[0] - 0.6 and EAVE_Z + 1.0 < z < hi[2] - 0.6, s
    for name, pose in POSES.items():
        e = pose["eye"]
        g = cells("on")
        cell = tuple(math.floor(c) for c in e)
        assert g.get(cell, AIR) == AIR, name
        f = basis(pose["yaw"], pose["pitch"])[0]
        lu, lv, ld = project(pose, LAMP_CENTRE)
        assert ld > 1 and 60 < lu < WIDTH - 60 and 40 < lv < HEIGHT - 40, (name, "lantern not in view", lu, lv)
        block = first_hit("on", e, [c - o for c, o in zip(LAMP_CENTRE, e)])[0]
        assert block == LANTERN, (name, "lantern hidden", block)
        for s in samples(name):
            if name in MEASURE_POSES:
                assert s["valid"], (name, s["name"], s["patch"], s["footprint"])
            if s["valid"]:
                assert max(abs(a - b) for a, b in zip(s["footprint"][-1]["local"], s["local"])) < 1e-6, (name, s["name"])
        if name == "wide":  # the production view still shows every material pair across the eave
            ok = {s["name"] for s in samples(name) if s["valid"]}
            assert {"stone-shelter-near", "stone-exposed-near", "smooth-shelter-near", "smooth-exposed-near"} <= ok, ok
        # identical footprint with the lamp removed (the lantern never covers a patch)
        for s0, s1 in zip(samples(name, "on"), samples(name, "off")):
            assert [f["block"] for f in s0["footprint"]] == [f["block"] for f in s1["footprint"]]
        rep[name] = dict(pose=pose_record(name), lantern=[round(lu, 1), round(lv, 1)], visible=visible(name))
    # pose A and B see the same places from different angles
    assert POSES["a"]["yaw"] != POSES["b"]["yaw"]
    return rep


if __name__ == "__main__":
    import json

    rep = selftest()
    for name in POSES:
        print(name, json.dumps(rep[name]["pose"]), "lantern px", rep[name]["lantern"])
        print("   visible", json.dumps(rep[name]["visible"], sort_keys=True))
        for s in samples(name):
            print("   %-22s %s %s depth %.2f" % (s["name"], s["projected"], s["patch"], s["depth"]))
    print("mirror a", SAMPLES[8]["point"], "mirror b", SAMPLES[9]["point"])
    print("fixture selftest ok")
