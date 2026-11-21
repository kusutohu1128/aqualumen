"""Read-only walkability BFS over saved AqualumenNaturalV2 blocks (1-block steps up/down, no swimming).
Usage: python3 -I route.py sx sy sz  -> nearest reachable water edge and deepest/closest cave cell within 160 steps
A 'cave cell' = standable cell with >= 3 solid blocks directly above and >= 5 m below the surface of its column.
"""
import sys, json
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
PASS = {"minecraft:air", "minecraft:cave_air", "minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern", "minecraft:large_fern",
        "minecraft:poppy", "minecraft:dandelion", "minecraft:cornflower", "minecraft:azure_bluet", "minecraft:oxeye_daisy", "minecraft:allium",
        "minecraft:lily_of_the_valley", "minecraft:red_mushroom", "minecraft:brown_mushroom", "minecraft:glow_lichen", "minecraft:vine"}
NOSTAND = {"minecraft:water", "minecraft:lava"}


def free(x, y, z):
    n = w.name(x, y, z)
    return n in PASS


def stand(x, y, z):
    b = w.name(x, y - 1, z)
    return b is not None and b not in PASS and b not in NOSTAND and "leaves" not in b and free(x, y, z) and free(x, y + 1, z)


def solid_cover(x, y, z):
    return sum(1 for k in range(2, 12) if (w.name(x, y + k, z) or "").endswith(("stone", "dirt", "deepslate", "andesite", "diorite", "granite")))


sx, sy, sz = map(int, sys.argv[1:4])
dist = {(sx, sy, sz): 0}
q = deque([(sx, sy, sz)])
water = cave = None
while q:
    p = q.popleft(); d = dist[p]
    if d > 160:
        continue
    x, y, z = p
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if water is None and w.name(x + dx, y - 1, z + dz) == "minecraft:water":
            water = (p, d)
        for dy in (0, 1, -1):
            n = (x + dx, y + dy, z + dz)
            if n in dist or not stand(*n):
                continue
            if dy == 1 and not free(x, y + 2, z):
                continue
            dist[n] = d + 1
            q.append(n)
            if cave is None or solid_cover(*n) > solid_cover(*cave[0]) and d + 1 < 150:
                if solid_cover(*n) >= 6:
                    cave = (n, d + 1)
print(json.dumps({"reachable": len(dist), "water_edge": water, "cave_best": cave, "unchanged": w.unchanged()}))
