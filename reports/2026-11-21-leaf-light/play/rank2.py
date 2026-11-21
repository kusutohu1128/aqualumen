"""Rank trees from scan.py outputs by isolation, orbit walkability, biome and nearby surface water (read-only).
Usage: python3 -I rank2.py out.json scan1.json [scan2.json ...]
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "reports/2026-11-20-local-light/forest-tools"))
from worldread import World, audit

class SafeWorld(World):
    def chunk(self, cx, cz):
        try:
            return super().chunk(cx, cz)
        except KeyError:  # partially generated edge chunk without block_states
            self.chunks[(cx, cz)] = None
            return None


w = SafeWorld()
LEAVES = {f"minecraft:{s}_leaves" for s in ("oak", "birch", "dark_oak", "spruce")}
SOLID_NOT = {"minecraft:air", "minecraft:cave_air", "minecraft:water", "minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern",
             "minecraft:large_fern", "minecraft:poppy", "minecraft:dandelion", "minecraft:cornflower", "minecraft:lily_of_the_valley",
             "minecraft:azure_bluet", "minecraft:oxeye_daisy", "minecraft:allium", "minecraft:rose_bush", "minecraft:lilac",
             "minecraft:peony", "minecraft:red_mushroom", "minecraft:brown_mushroom", "minecraft:sweet_berry_bush", "minecraft:dead_bush",
             "minecraft:lily_pad", "minecraft:snow", "minecraft:vine", "minecraft:bush"}


def biome(x, y, z):
    nbt, _ = audit.decode_chunk(w.region_bytes(x // 512, z // 512), None, x // 16, z // 16)
    sec = {s["Y"]: s for s in nbt["sections"]}[y // 16]["biomes"]
    pal = sec["palette"]
    if len(pal) == 1:
        return pal[0][10:]
    bits = max(1, (len(pal) - 1).bit_length()); per = 64 // bits
    i = ((y % 16) // 4) * 16 + ((z % 16) // 4) * 4 + (x % 16) // 4
    return pal[((sec["data"][i // per] & (2**64 - 1)) >> ((i % per) * bits)) & ((1 << bits) - 1)][10:]


def walk_y(x, z, y0):
    """Feet y of a standable cell near y0 (solid below, 2 air above), else None."""
    for y in (y0, y0 + 1, y0 - 1):
        b, a1, a2 = w.name(x, y - 1, z), w.name(x, y, z), w.name(x, y + 1, z)
        if None in (b, a1, a2):
            return None
        if b not in SOLID_NOT and not b.endswith("_leaves") and a1 in SOLID_NOT - {"minecraft:water"} and a2 in SOLID_NOT - {"minecraft:water"}:
            return y
    return None


out = []
for path in sys.argv[2:]:
    scan = json.load(open(path))
    x0, z0, x1, z1 = scan["box"]
    leaf = set()
    for cx in range(x0 // 16 - 1, x1 // 16 + 2):
        for cz in range(z0 // 16 - 1, z1 // 16 + 2):
            leaf.update((x, y, z) for x, y, z, n in w.height_log_scan(cx, cz, LEAVES))
    for t in scan["trees"]:
        if t["species"] in ("dark_oak", "spruce") or t["logs"] > 8:
            continue
        x, y, z = t["base"]
        lo, hi = t["leaf_bbox"]
        foreign = sum(1 for dx in range(-9, 10) for dz in range(-9, 10) for dy in range(0, 10)
                      if (x + dx, y + dy, z + dz) in leaf and not (lo[0] <= x + dx <= hi[0] and lo[2] <= z + dz <= hi[2]))
        if foreign > 450:
            continue
        ring = {}
        for r in (4, 5):
            ok = 0
            for k in range(24):
                import math
                px, pz = round(x + r * math.cos(k * math.pi / 12)), round(z + r * math.sin(k * math.pi / 12))
                ok += walk_y(px, pz, y) is not None
            ring[r] = ok
        water = None
        for r in range(1, 70):
            cells = [(x + dx, z + dz) for dx in range(-r, r + 1) for dz in (-r, r)] + [(x + dx, z + dz) for dz in range(-r + 1, r) for dx in (-r, r)]
            if any(w.name(px, yy, pz) == "minecraft:water" for px, pz in cells for yy in range(y - 3, y)):
                water = r; break
        out.append({**t, "foreign_leaves_9m": foreign, "ring4_ok_of_24": ring[4], "ring5_ok_of_24": ring[5], "biome": biome(x, y, z), "water_m": water})
out.sort(key=lambda r: (-(r["ring4_ok_of_24"] >= 22 and r["ring5_ok_of_24"] >= 22), r["foreign_leaves_9m"]))
json.dump({"world_unchanged": w.unchanged(), "rows": out}, open(sys.argv[1], "w"), indent=1)
print("unchanged", w.unchanged(), len(out))
for r in out[:40]:
    print(r["base"], r["species"], r["logs"], r["leaves"], "low", r["lowest_leaf_above_ground"], "foreign", r["foreign_leaves_9m"], "ring", r["ring4_ok_of_24"], r["ring5_ok_of_24"], r["biome"], "water", r["water_m"])
