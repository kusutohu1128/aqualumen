"""Read-only scan for natural single-trunk oak/birch trees near woodland/shore in the TEST save.

Usage: python3 -I scan_trees.py [x0 z0 x1 z1] > candidates.json
Prints JSON candidates (trunk base, height, species, crown leaves, water distance).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from worldread import World  # noqa: E402

LOGS = {"minecraft:oak_log", "minecraft:birch_log"}
GROUND = {"minecraft:grass_block", "minecraft:dirt", "minecraft:podzol", "minecraft:coarse_dirt"}


def main():
    x0, z0, x1, z1 = (int(v) for v in sys.argv[1:5]) if len(sys.argv) >= 5 else (64, 256, 271, 495)
    w = World()
    logs = {}
    for cx in range(x0 // 16, x1 // 16 + 1):
        for cz in range(z0 // 16, z1 // 16 + 1):
            for x, y, z, n in w.height_log_scan(cx, cz, LOGS):
                logs[(x, y, z)] = n
    cands = []
    for (x, y, z), n in logs.items():
        below = w.name(x, y - 1, z)
        if below not in GROUND:
            continue
        h = 0
        while logs.get((x, y + h, z)) == n:
            h += 1
        if h < 4 or h > 8:
            continue
        leaf = n.replace("_log", "_leaves")
        crown = 0
        for dx in range(-3, 4):
            for dz in range(-3, 4):
                for dy in range(2, h + 3):
                    s = w.state(x + dx, y + dy, z + dz)
                    if s and s["Name"] == leaf and s.get("Properties", {}).get("persistent") == "false":
                        crown += 1
        if crown < 35:
            continue
        water = None
        for r in range(2, 41, 2):
            found = False
            for dx in range(-r, r + 1, 2):
                for dz in (-r, r):
                    if w.name(x + dx, 62, z + dz) == "minecraft:water" or w.name(x + dz, 62, z + dx) == "minecraft:water":
                        found = True
                        break
                if found:
                    break
            if found:
                water = r
                break
        cands.append({"base": [x, y, z], "species": n, "height": h, "crown_leaves": crown,
                      "ground": below, "water_distance_m": water})
    print(json.dumps({"scan_box": [x0, z0, x1, z1], "count": len(cands), "world_unchanged": w.unchanged(),
                      "candidates": sorted(cands, key=lambda c: (c["water_distance_m"] is None, c["water_distance_m"] or 0))}))


if __name__ == "__main__":
    main()
