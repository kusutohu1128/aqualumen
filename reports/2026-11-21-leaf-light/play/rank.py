"""Rank scan.json trees: isolation (foreign leaves/logs within 8 m), biome, distance to water. Read-only.
Usage: python3 -I rank.py scan.json x0 z0 x1 z1
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "reports/2026-11-20-local-light/forest-tools"))
from worldread import World, audit

scan = json.load(open(sys.argv[1]))
x0, z0, x1, z1 = map(int, sys.argv[2:6])
w = World()
LEAVES = {f"minecraft:{s}_leaves" for s in ("oak", "birch", "dark_oak", "spruce")}
leaf = set()
for cx in range(x0 // 16, x1 // 16 + 1):
    for cz in range(z0 // 16, z1 // 16 + 1):
        for x, y, z, n in w.height_log_scan(cx, cz, LEAVES):
            leaf.add((x, y, z))


def biome(x, y, z):
    nbt, _ = audit.decode_chunk(w.region_bytes(x // 512, z // 512), None, x // 16, z // 16)
    sec = {s["Y"]: s for s in nbt["sections"]}[y // 16]["biomes"]
    pal = sec["palette"]
    if len(pal) == 1:
        return pal[0][10:]
    bits = max(1, (len(pal) - 1).bit_length()); per = 64 // bits
    i = ((y % 16) // 4) * 16 + ((z % 16) // 4) * 4 + (x % 16) // 4
    return pal[((sec["data"][i // per] & (2**64 - 1)) >> ((i % per) * bits)) & ((1 << bits) - 1)][10:]


rows = []
for t in scan["trees"]:
    if t["species"] == "dark_oak" or t["logs"] > 12:
        continue
    x, y, z = t["base"]
    lo, hi = t["leaf_bbox"]
    foreign = sum(1 for dx in range(-9, 10) for dz in range(-9, 10) for dy in range(0, 10)
                  if (x + dx, y + dy, z + dz) in leaf and not (lo[0] <= x + dx <= hi[0] and lo[2] <= z + dz <= hi[2]))
    water = None
    for r in range(1, 61):
        if any(w.name(x + dx, 62, z + dz) == "minecraft:water" for dx in range(-r, r + 1) for dz in (-r, r)) or \
           any(w.name(x + dx, 62, z + dz) == "minecraft:water" for dz in range(-r, r + 1) for dx in (-r, r)):
            water = r; break
    rows.append({**t, "foreign_leaves_9m": foreign, "biome": biome(x, y, z), "water_m": water})
rows.sort(key=lambda r: (r["foreign_leaves_9m"], r["water_m"] or 99))
json.dump({"world_unchanged": w.unchanged(), "rows": rows}, open(sys.argv[1].replace(".json", "-ranked.json"), "w"))
print("unchanged", w.unchanged(), len(rows))
for r in rows[:30]:
    print(r["base"], r["species"], r["logs"], r["leaves"], r["lowest_leaf_above_ground"], r["foreign_leaves_9m"], r["biome"], r["water_m"])
