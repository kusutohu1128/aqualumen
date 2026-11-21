"""Read-only scan of the saved AqualumenNaturalV2 chunks (same seed 308060) for tractable natural trees.

Usage: python3 -I scan.py x0 z0 x1 z1  > scan.json   (opens region files read-only, via worldread)
A tree = flood fill of one species' logs + `persistent=false` leaves from a ground-standing trunk column.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "reports/2026-11-20-local-light/forest-tools"))
from worldread import World

SPECIES = ["oak", "birch", "dark_oak", "spruce"]
GROUND = {"minecraft:grass_block", "minecraft:dirt", "minecraft:podzol", "minecraft:coarse_dirt"}


def main():
    x0, z0, x1, z1 = map(int, sys.argv[1:5])
    w = World()
    logs = {}
    for cx in range(x0 // 16, x1 // 16 + 1):
        for cz in range(z0 // 16, z1 // 16 + 1):
            for x, y, z, n in w.height_log_scan(cx, cz, {f"minecraft:{s}_log" for s in SPECIES}):
                logs[(x, y, z)] = n
    seen, out = set(), []
    for (x, y, z), n in sorted(logs.items()):
        if (x, y, z) in seen or w.name(x, y - 1, z) not in GROUND:
            continue
        sp = n[10:-4]
        leaf = f"minecraft:{sp}_leaves"
        # flood fill from this base
        stack, lg, lv = [(x, y, z)], set(), set()
        while stack and len(lg) + len(lv) < 700:
            p = stack.pop()
            if p in lg or p in lv:
                continue
            s = w.state(*p)
            if s is None:
                continue
            if s["Name"] == n:
                lg.add(p)
            elif s["Name"] == leaf and s.get("Properties", {}).get("persistent") == "false":
                lv.add(p)
            else:
                continue
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                stack.append((p[0] + d[0], p[1] + d[1], p[2] + d[2]))
        seen |= lg
        bases = [p for p in lg if w.name(p[0], p[1] - 1, p[2]) in GROUND]
        if len(bases) != 1 and sp != "dark_oak":
            continue
        if not lv:
            continue
        low = min(p[1] for p in lv) - y
        out.append({"base": [x, y, z], "species": sp, "logs": len(lg), "leaves": len(lv), "lowest_leaf_above_ground": low,
                    "leaf_bbox": [[min(p[i] for p in lv) for i in range(3)], [max(p[i] for p in lv) for i in range(3)]],
                    "trunk_bases": len(bases)})
    print(json.dumps({"box": [x0, z0, x1, z1], "world_unchanged": w.unchanged(), "count": len(out), "trees": out}))


main()
