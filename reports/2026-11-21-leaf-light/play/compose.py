"""Read-only composition search at one tree: for ring viewpoints, which ground torch cells are seen *through* natural leaves?
For each (eye, flame) the ray is traced through the saved voxels (Amanatides-Woo). Leaf path length in metres, blockers = any
non-leaf, non-passable block. Usage: python3 -I compose.py tx ty tz   (tree base) > compose.json
"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "reports/2026-11-20-local-light/forest-tools"))
from worldread import World

w = World()
tx, ty, tz = map(int, sys.argv[1:4])
PASS = {"minecraft:air", "minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern", "minecraft:large_fern", "minecraft:poppy",
        "minecraft:dandelion", "minecraft:cornflower", "minecraft:azure_bluet", "minecraft:oxeye_daisy", "minecraft:allium",
        "minecraft:lily_of_the_valley", "minecraft:red_mushroom", "minecraft:brown_mushroom"}


def trace(a, b):
    """Return (leaf_length, blocked_by) along a->b."""
    d = [b[i] - a[i] for i in range(3)]
    L = math.sqrt(sum(v * v for v in d))
    cell = [math.floor(v) for v in a]
    step = [1 if v > 0 else -1 for v in d]
    tmax, tdel = [], []
    for i in range(3):
        if d[i] == 0:
            tmax.append(1e30); tdel.append(1e30)
        else:
            nxt = cell[i] + (1 if step[i] > 0 else 0)
            tmax.append((nxt - a[i]) / d[i]); tdel.append(abs(1 / d[i]))
    t, leaf, last = 0.0, 0.0, 0.0
    end = [math.floor(v) for v in b]
    while True:
        name = w.name(*cell)
        i = tmax.index(min(tmax))
        t_exit = min(min(tmax), 1.0)
        if name and name.endswith("_leaves"):
            leaf += (t_exit - t) * L
        elif name not in PASS and cell != end:
            return leaf, name
        t = t_exit
        if t >= 1.0 or cell == end:
            return leaf, None
        cell[i] += step[i]; tmax[i] += tdel[i]


def standable(x, z):
    for y in (ty - 1, ty, ty + 1):
        below, a1, a2 = w.name(x, y - 1, z), w.name(x, y, z), w.name(x, y + 1, z)
        if below in ("minecraft:grass_block", "minecraft:dirt", "minecraft:podzol", "minecraft:coarse_dirt") and a1 in PASS and a2 in PASS:
            return y
    return None


cx, cz = tx + 0.5, tz + 0.5
views, flames = [], []
RINGS = tuple(float(v) for v in sys.argv[4].split(",")) if len(sys.argv) > 4 else (3.5, 4.5, 5.5)
DMAX = float(sys.argv[5]) if len(sys.argv) > 5 else 9.5
for r in RINGS:
    for k in range(36):
        ang = math.radians(k * 10)
        x, z = math.floor(cx + r * math.cos(ang)), math.floor(cz + r * math.sin(ang))
        y = standable(x, z)
        if y is not None:
            views.append({"feet": [x + 0.5, y, z + 0.5], "ring": r, "ang": k * 10})
for x in range(tx - 6, tx + 7):
    for z in range(tz - 6, tz + 7):
        y = standable(x, z)
        if y is not None and math.hypot(x + .5 - cx, z + .5 - cz) <= 4.2 and (w.name(x, y, z) in PASS):
            flames.append({"cell": [x, y, z], "p": [x + 0.5, y + 0.7, z + 0.5]})
out = []
for v in views:
    eye = [v["feet"][0], v["feet"][1] + 1.62, v["feet"][2]]
    for f in flames:
        dist = math.dist(eye, f["p"])
        if not 5.0 <= dist <= DMAX:
            continue
        leaf, blk = trace(eye, f["p"])
        if blk is None and 0.8 <= leaf <= 2.8:
            yaw = math.degrees(math.atan2(-(f["p"][0] - eye[0]), f["p"][2] - eye[2]))  # MC yaw: 0 = +Z, 90 = -X
            out.append({"view": v, "eye": eye, "flame": f["cell"], "leaf_m": round(leaf, 2), "dist": round(dist, 2), "yaw": round(yaw, 1)})
print(json.dumps({"tree": [tx, ty, tz], "views": len(views), "flames": len(flames), "pairs": len(out), "unchanged": w.unchanged(), "rows": out}))
