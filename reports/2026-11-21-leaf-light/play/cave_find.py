"""Read-only: find walkable natural cave mouths near a point in AqualumenNaturalV2.
A cave cell = air at y <= local surface height (surface ignores leaves/logs/plants); a mouth = such a cell
4-adjacent to a cell above the surface column top, connected through air to >=40 cave cells >=5 m below the surface.
Usage: python3 -I cave_find.py x z radius
"""
import sys
from collections import deque
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "reports/2026-11-20-local-light/forest-tools"))
from worldread import World


class SafeWorld(World):
    def chunk(self, cx, cz):
        try:
            return super().chunk(cx, cz)
        except KeyError:
            self.chunks[(cx, cz)] = None
            return None


w = SafeWorld()
X, Z, R = map(int, sys.argv[1:4])
PASS = {"minecraft:air", "minecraft:cave_air", "minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern", "minecraft:large_fern",
        "minecraft:vine", "minecraft:glow_lichen"}
H = {}
for x in range(X - R, X + R + 1):
    for z in range(Z - R, Z + R + 1):
        for y in range(120, 40, -1):
            n = w.name(x, y, z)
            if n and n not in PASS and not n.endswith("_leaves") and not n.endswith("_log") and "flower" not in n and n not in ("minecraft:poppy", "minecraft:dandelion"):
                H[(x, z)] = y; break
air = set()
for (x, z), h in H.items():
    for y in range(max(40, h - 40), h):
        if w.name(x, y, z) == "minecraft:air":
            air.add((x, y, z))
print("underground-ish air cells", len(air))
seen, comps = set(), []
for c in air:
    if c in seen:
        continue
    comp, q = [], deque([c]); seen.add(c)
    while q:
        p = q.popleft(); comp.append(p)
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (p[0] + d[0], p[1] + d[1], p[2] + d[2])
            if n in air and n not in seen:
                seen.add(n); q.append(n)
    comps.append(comp)
res = []
for comp in comps:
    deep = [p for p in comp if H[(p[0], p[2])] - p[1] >= 5]
    if len(deep) < 40:
        continue
    mouth = [p for p in comp if H[(p[0], p[2])] - p[1] <= 1 and any(
        (p[0] + dx, p[2] + dz) in H and H[(p[0] + dx, p[2] + dz)] < p[1] for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    # cells at the open surface: a cave cell directly below sky-exposed air
    exits = [p for p in comp if H[(p[0], p[2])] - p[1] <= 1]
    if exits:
        m = min(exits, key=lambda p: (p[0] - X) ** 2 + (p[2] - Z) ** 2)
        res.append((round(((m[0] - X) ** 2 + (m[2] - Z) ** 2) ** .5), m, len(comp), len(deep), min(p[1] for p in comp)))
res.sort()
for r in res[:10]:
    print("dist", r[0], "mouth", r[1], "cells", r[2], "deep", r[3], "min_y", r[4])
print("unchanged", w.unchanged())
