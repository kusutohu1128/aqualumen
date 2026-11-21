"""Certify what Minecraft itself generated in a private Woodland clone, against the saved V2 chunks (same seed), read-only.

  python3 -I certify.py <private save dir> [out.json]

Compares every block of the tree box between the clone and V2 (differences must be explained by the player's actions), then reports the
tree (logs, `persistent=false` leaves), the biome at the tree/spawn/water/cave cells and the chunk status/ generator facts.
"""
import importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "reports/2026-11-20-local-light/forest-tools"))
from worldread import World, audit, WORLD as V2  # noqa: E402

site = json.loads((HERE / "site.json").read_text())


class Save:
    def __init__(self, root):
        self.root, self.cache = Path(root), {}

    def nbt(self, cx, cz):
        if (cx, cz) not in self.cache:
            p = self.root / f"region/r.{cx // 32}.{cz // 32}.mca"
            res = None
            if p.exists() and not p.is_symlink():
                try:
                    res = audit.decode_chunk(p.read_bytes(), None, cx, cz)[0]
                except ValueError:
                    res = None
            self.cache[(cx, cz)] = res
        return self.cache[(cx, cz)]

    def sections(self, cx, cz):
        n = self.nbt(cx, cz)
        return None if n is None or "sections" not in n else World._sections(n)

    def state(self, x, y, z):
        s = self.sections(x // 16, z // 16)
        if s is None:
            return None
        sec = s.get(y // 16)
        if sec is None:
            return {"Name": "minecraft:air"}
        pal, idx = sec
        return pal[0] if idx is None else pal[idx[(y % 16) * 256 + (z % 16) * 16 + (x % 16)]]

    def biome(self, x, y, z):
        n = self.nbt(x // 16, z // 16)
        sec = {s["Y"]: s for s in n["sections"]}[y // 16]["biomes"]
        pal = sec["palette"]
        if len(pal) == 1:
            return pal[0]
        bits = max(1, (len(pal) - 1).bit_length()); per = 64 // bits
        i = ((y % 16) // 4) * 16 + ((z % 16) // 4) * 4 + (x % 16) // 4
        return pal[((sec["data"][i // per] & (2**64 - 1)) >> ((i % per) * bits)) & ((1 << bits) - 1)]


def key(s):
    return None if s is None else (s["Name"], tuple(sorted(s.get("Properties", {}).items())))


def main():
    clone, v2 = Save(sys.argv[1]), Save(V2)
    tx, ty, tz = site["tree"]["base"]
    box = [(x, y, z) for x in range(tx - 12, tx + 13) for y in range(ty - 3, ty + 12) for z in range(tz - 12, tz + 13)]
    diffs, missing, same = [], 0, 0
    for p in box:
        a, b = clone.state(*p), v2.state(*p)
        if a is None or b is None:
            missing += 1
        elif key(a) == key(b):
            same += 1
        else:
            pa, pb = a.get("Properties", {}), b.get("Properties", {})
            diffs.append({"cell": p, "clone": a["Name"], "v2": b["Name"], "properties_differing": sorted(k for k in set(pa) | set(pb) if pa.get(k) != pb.get(k))})
    logs = [(tx, ty + i, tz) for i in range(4)]
    # flood fill this tree only: its logs plus connected oak leaves
    stack, seen_logs, leaves = [(tx, ty, tz)], set(), set()
    while stack:
        p = stack.pop()
        n = (clone.state(*p) or {}).get("Name")
        if p in seen_logs or p in leaves or n not in ("minecraft:oak_log", "minecraft:oak_leaves") or (p[1] < ty or abs(p[0] - tx) > 3 or abs(p[2] - tz) > 3):
            continue
        (seen_logs if n.endswith("log") else leaves).add(p)
        stack += [(p[0] + d[0], p[1] + d[1], p[2] + d[2]) for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
    persistent_false = [p for p in leaves if clone.state(*p)["Properties"].get("persistent") == "false"]
    cells = {"tree": (tx, ty, tz), "spawn": tuple(int(v // 1) for v in site["spawn"]["feet"]), "water": tuple(site["water_edge_steps"]["cell"]),
             "cave": tuple(site["cave_cell"])}
    biomes = {k: clone.biome(*c).replace("minecraft:", "") for k, c in cells.items()}
    v2biomes = {k: v2.biome(*c).replace("minecraft:", "") for k, c in cells.items()}
    status = {}
    for cx in range((tx - 12) // 16, (tx + 12) // 16 + 1):
        for cz in range((tz - 12) // 16, (tz + 12) // 16 + 1):
            n = clone.nbt(cx, cz)
            status[f"{cx},{cz}"] = None if n is None else {"Status": n.get("Status"), "DataVersion": n.get("DataVersion")}
    out = {"clone": str(clone.root), "v2": str(V2), "box_cells": len(box), "identical": same, "missing": missing, "different": diffs,
           "tree_logs": [clone.state(*p)["Name"] for p in logs], "tree_flood_fill_logs": len(seen_logs), "tree_leaves_in_crown": len(leaves),
           "tree_leaves_persistent_false": len(persistent_false), "biomes_clone": biomes, "biomes_v2": v2biomes, "chunks": status,
           "ground_below_tree": clone.state(tx, ty - 1, tz)["Name"], "level_dat_seed_region_files": sorted(p.name for p in (clone.root / "region").glob("*.mca"))[:6]}
    out["ok"] = (out["tree_logs"] == ["minecraft:oak_log"] * 4 and len(persistent_false) == site["tree"]["crown_leaves_persistent_false"]
                 and biomes == v2biomes and biomes["tree"] == "forest" and not missing
                 and all(d["properties_differing"] in (["distance"], []) or d["clone"].endswith("torch") for d in diffs))
    print(json.dumps(out, indent=1, default=list))
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(out, indent=1, default=list) + "\n")


main()
