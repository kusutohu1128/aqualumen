"""Read-only walking plan over saved V2 blocks: BFS between key cells + string pulling into <=9 m straight legs.
Usage: python3 -I plan.py > route-plan.json
A leg is accepted only if every 0.4 m sample (and +-0.3 m lateral offsets) lands on standable cells with |dy|<=1 per step.
"""
import json, math, sys
from collections import deque
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "reports/2026-11-20-local-light/forest-tools"))
from worldread import World

site = json.loads((Path(__file__).with_name("site.json")).read_text())
PASS = {"minecraft:air", "minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern", "minecraft:large_fern", "minecraft:poppy",
        "minecraft:dandelion", "minecraft:cornflower", "minecraft:azure_bluet", "minecraft:oxeye_daisy", "minecraft:allium",
        "minecraft:lily_of_the_valley", "minecraft:red_mushroom", "minecraft:brown_mushroom", "minecraft:glow_lichen"}


class SafeWorld(World):
    def chunk(self, cx, cz):
        try:
            return super().chunk(cx, cz)
        except KeyError:
            self.chunks[(cx, cz)] = None
            return None


w = SafeWorld()


def free(x, y, z):
    return w.name(x, y, z) in PASS


def stand(x, y, z):
    b = w.name(x, y - 1, z)
    return b is not None and b not in PASS and b not in ("minecraft:water", "minecraft:lava") and "leaves" not in b and free(x, y, z) and free(x, y + 1, z)


def column(x, z, y0):
    for y in (y0, y0 + 1, y0 - 1):
        if stand(x, y, z):
            return y
    return None


def bfs(a, b):
    prev = {a: None}
    q = deque([a])
    while q:
        p = q.popleft()
        if p[0] == b[0] and p[2] == b[2]:
            path = []
            while p:
                path.append(p); p = prev[p]
            return path[::-1]
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            y = column(p[0] + dx, p[2] + dz, p[1])
            if y is None:
                continue
            n = (p[0] + dx, y, p[2] + dz)
            if n in prev or (y > p[1] and not free(p[0], p[1] + 2, p[2])):
                continue
            # keep one block of side clearance when possible: penalise nothing, but require both neighbours standable-ish
            prev[n] = p; q.append(n)
    return None


def leg_ok(a, b):
    n = max(1, int(math.dist((a[0], a[2]), (b[0], b[2])) / 0.4))
    y = a[1]
    for i in range(n + 1):
        t = i / n
        for off in (0.0, 0.3, -0.3):
            dx, dz = b[0] - a[0], b[2] - a[2]
            L = math.hypot(dx, dz) or 1
            x, z = a[0] + dx * t - dz / L * off, a[2] + dz * t + dx / L * off
            yy = column(math.floor(x), math.floor(z), y)
            if yy is None:
                return False
            if off == 0.0:
                y = yy
    return True


def pull(path):
    pts = [(c[0] + 0.5, c[1], c[2] + 0.5) for c in path]
    out, i = [pts[0]], 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and (not leg_ok(pts[i], pts[j]) or math.dist((pts[i][0], pts[i][2]), (pts[j][0], pts[j][2])) > 9
                              or abs(pts[j][1] - pts[i][1]) > 1):
            j -= 1
        out.append(pts[j]); i = j
    return out


tx, ty, tz = site["tree"]["base"]
keys = {
    "spawn": (559, 63, 423),
    "place-north": (564, 64, 416),
    "place-south": (563, 64, 426),
    "view": (559, 63, 423),
    "water": (556, 63, 419),
    "cave": (598, 71, 427),
}
for k in range(12):
    ang = math.radians(k * 30 + 30)
    keys[f"ring{k}"] = (round(tx + .5 + 4.5 * math.cos(ang)), None, round(tz + .5 + 4.5 * math.sin(ang)))
fixed = {}
for k, c in keys.items():
    y = column(c[0], c[2], ty if c[1] is None else c[1])
    fixed[k] = None if y is None else (c[0], y, c[2])
legs = {}
for a, b in (("spawn", "place-north"), ("place-north", "view"), ("view", "place-south"), ("place-south", "view"), ("view", "water"), ("water", "cave"), ("cave", "spawn")):
    p = bfs(fixed[a], fixed[b])
    legs[f"{a}->{b}"] = {"cells": len(p) if p else None, "waypoints": pull(p) if p else None}
for k in range(12):  # orbit legs, each BFS-checked (the tree to the south blocks the straight chord)
    a, b = f"ring{k}", f"ring{(k + 1) % 12}"
    p = bfs(fixed[a], fixed[b])
    legs[f"{a}->{b}"] = {"cells": len(p) if p else None, "waypoints": pull(p) if p else None}
print(json.dumps({"keys": {k: v for k, v in fixed.items()}, "legs": legs, "unchanged": w.unchanged()}, indent=1))
