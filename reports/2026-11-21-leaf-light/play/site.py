"""Read-only ASCII survey of one site in AqualumenNaturalV2: surface map, leaves/logs, biome.
Usage: python3 -I site.py cx cz radius
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "reports/2026-11-20-local-light/forest-tools"))
from worldread import World, audit

cx, cz, r = map(int, sys.argv[1:4])
w = World()


def top(x, z):
    for y in range(120, 40, -1):
        s = w.state(x, y, z)
        if s and s["Name"] not in ("minecraft:air", "minecraft:cave_air"):
            n = s["Name"][10:]
            if n.endswith("_leaves"):
                continue
            return y, n
    return None, None


def biome(x, y, z):
    data = w.region_bytes(x // 16 // 32, z // 16 // 32)
    nbt, _ = audit.decode_chunk(data, None, x // 16, z // 16)
    sec = {s["Y"]: s for s in nbt["sections"]}[y // 16]["biomes"]
    pal = sec["palette"]
    if len(pal) == 1:
        return pal[0]
    bits = max(1, (len(pal) - 1).bit_length())
    per = 64 // bits
    i = ((y % 16) // 4) * 16 + ((z % 16) // 4) * 4 + (x % 16) // 4
    word = sec["data"][i // per] & (2**64 - 1)
    return pal[(word >> ((i % per) * bits)) & ((1 << bits) - 1)]


print("biome at site", biome(cx, 64, cz))
print("legend: digits=surface y-64 (+ = higher, clipped ±9), L=leaf above surface, T=log, ~=water, *=center")
for dz in range(-r, r + 1):
    row = ""
    for dx in range(-r, r + 1):
        x, z = cx + dx, cz + dz
        y, n = top(x, z)
        ch = "?"
        if n is None:
            ch = " "
        elif n == "water":
            ch = "~"
        elif n.endswith("_log"):
            ch = "T"
        else:
            ch = str(max(-9, min(9, y - 64))) if y - 64 >= 0 else chr(ord("a") - (y - 64) - 1)
            leaf_above = any((w.name(x, yy, z) or "").endswith("_leaves") for yy in range(y + 1, y + 12))
            if leaf_above:
                ch = "L"
        if dx == 0 and dz == 0:
            ch = "*"
        row += ch
    print(f"{cz+dz:4d} {row}")
print("x from", cx - r, "to", cx + r)
print("world_unchanged", w.unchanged())
