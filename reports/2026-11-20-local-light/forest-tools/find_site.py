"""Analytic search for a natural oak/birch composition with a reserved torch slot (read-only; no render).

Usage: python3 -I find_site.py [scan_x0 scan_z0 scan_x1 scan_z1] [top_n]
"""
import json
import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan_trees import GROUND, LOGS  # noqa: E402
from voxels import *  # noqa: E402,F401,F403
from worldread import World  # noqa: E402

TIME = 9800
EYE = 1.62
SUN = sun_direction(TIME)
GOOD = (GRASS, DIRT)


def trees(world, grid, box):
    x0, z0, x1, z1 = box
    out = []
    for x in range(x0 + 4, x1 - 3):
        for z in range(z0 + 4, z1 - 3):
            for y in range(grid.y0 + 1, grid.y0 + grid.H - 12):
                if grid.cat(x, y, z) == LOG and grid.cat(x, y - 1, z) == DIRT:
                    h = 0
                    while grid.cat(x, y + h, z) == LOG:
                        h += 1
                    s = world.state(x, y, z)
                    if s["Name"] not in LOGS or s.get("Properties", {}).get("axis") != "y" or not 4 <= h <= 8:
                        continue
                    leaf = s["Name"].replace("_log", "_leaves")
                    crown = sum(1 for dx in range(-3, 4) for dz in range(-3, 4) for dy in range(2, h + 3)
                                if (st := world.state(x + dx, y + dy, z + dz)) and st["Name"] == leaf
                                and st.get("Properties", {}).get("persistent") == "false")
                    if crown >= 35:
                        out.append((x, y, z, h, s["Name"], crown))
    return out


def ground_y(grid, x, z, near):
    for y in range(near + 4, near - 5, -1):
        if grid.cat(x, y, z) in GOOD and all(grid.cat(x, y + k, z) == AIR for k in (1, 2, 3)):
            return y
    return None


def yaw_to(dx, dz):
    return math.degrees(math.atan2(-dx, dz))


def evaluate(grid, tree, cam, yaw, pitch, rng):
    bx, by, bz, h = tree[:4]
    eye = (cam[0], cam[1] + EYE, cam[2])
    trunk = {(bx, by + k, bz) for k in range(h)}
    n_x, n_y, total = 40, 22, 0
    cnt = {k: 0 for k in ("trunk", "leaf_near", "leaf_mid", "leaf_far", "ground", "sky", "other", "unknown", "water")}
    other_trunks, plants_ground = set(), 0
    for i in range(n_x):
        for j in range(n_y):
            nx = -1 + (i + .5) * 2 / n_x
            ny = -1 + (j + .5) * 2 / n_y
            d = ray_dir(nx, ny, yaw, pitch)
            c, t, cell, plants = grid.cast(eye, d, 90)
            total += 1
            if c == AIR:
                cnt["sky"] += 1
            elif c == UNKNOWN:
                cnt["unknown"] += 1
            elif c == LOG:
                if cell in trunk:
                    cnt["trunk"] += 1
                else:
                    cnt["other"] += 1
                    if t > 8:
                        other_trunks.add((cell[0], cell[2]))
            elif c == LEAVES:
                cnt["leaf_near" if t < 6 else "leaf_mid" if t < 16 else "leaf_far"] += 1
            elif c in (GRASS, DIRT):
                cnt["ground"] += 1
                plants_ground += plants > 0
            elif c == WATER:
                cnt["water"] += 1
            else:
                cnt["other"] += 1
    fr = {k: v / total for k, v in cnt.items()}
    clip = lambda v: max(0.0, min(1.0, v))
    peak = lambda v, c, w: clip(1 - abs(v - c) / w)
    foliage_far = fr["leaf_mid"] + fr["leaf_far"]
    score = (2.0 * peak(fr["trunk"], .09, .08) + 2.0 * peak(foliage_far, .28, .24) + 1.8 * peak(fr["ground"], .30, .15)
             + 1.0 * peak(fr["sky"], .17, .17) + 0.8 * min(1, len(other_trunks) / 3) + 0.8 * clip(plants_ground / 60)
             - 6.0 * max(0, fr["leaf_near"] - .03) - 8.0 * (fr["unknown"] + fr["water"] + max(0, fr["other"] - .06))
             + 0.6 * clip(math.sin(math.radians(yaw))))
    return score, fr, len(other_trunks), plants_ground


def main():
    args = sys.argv[1:]
    box = tuple(int(v) for v in args[:4]) if len(args) >= 4 else (96, 264, 255, 423)
    top_n = int(args[4]) if len(args) >= 5 else 12
    only = tuple(int(v) for v in args[5].split(',')) if len(args) >= 6 else None
    fine = only is not None
    w = World()
    t0 = time.time()
    grid = Grid(w, box[0] - 16, box[1] - 16, box[2] + 16, box[3] + 16, 52, 110)
    ts = trees(w, grid, box)
    print(f"# grid built {time.time() - t0:.1f}s, trees={len(ts)}", file=sys.stderr)
    rng = random.Random(5)
    results = []
    for tree in ts:
        if only and tuple(tree[:3]) != only:
            continue
        bx, by, bz, h = tree[:4]
        tc = (bx + .5, bz + .5)
        for cxi in range(bx - 9, bx + 10):
            for czi in range(bz - 9, bz + 10):
                dist = math.hypot(cxi + .5 - tc[0], czi + .5 - tc[1])
                if not 5.0 <= dist <= 7.5:
                    continue
                gy = ground_y(grid, cxi, czi, by - 1)
                if gy is None or abs(gy + 1 - by) > 3:
                    continue
                fy = gy + 1
                ok = all(grid.cat(cxi + a, fy + b, czi + c) in (AIR, PLANT) and
                         (grid.cat(cxi + a, fy + b, czi + c) == AIR or b == 0)
                         for a in (-1, 0, 1) for c in (-1, 0, 1) for b in (0, 1, 2))
                if not ok or grid.cat(cxi, fy, czi) != AIR:
                    continue
                cam = (cxi + .5, fy, czi + .5)
                eye = (cam[0], cam[1] + EYE, cam[2])
                # trunk faces must be reachable by three rays at 0.4, 1.4 and 2.6 m above the base
                vis = 0
                for dy in (.4, 1.4, 2.6):
                    p = (tc[0], by + dy, tc[1])
                    d = (p[0] - eye[0], p[1] - eye[1], p[2] - eye[2])
                    n = math.sqrt(sum(v * v for v in d))
                    c, t, cell, _ = grid.cast(eye, tuple(v / n for v in d), n + 1)
                    vis += c == LOG and cell == (bx, by + int(dy), bz)
                if vis < 3:
                    continue
                base_yaw = yaw_to(tc[0] - eye[0], tc[1] - eye[2])
                for delta in (range(-28, 29, 2) if fine else (-22, -17, -12, 12, 17, 22)):
                    yaw = base_yaw + delta
                    for pitch in (range(-14, 3, 2) if fine else (-10, -6, -2, 2, 6)):
                        pb = project((tc[0], by + .3, tc[1]), eye, yaw, pitch)
                        pm = project((tc[0], by + 3.0, tc[1]), eye, yaw, pitch)
                        if not pb or not pm or not (.15 <= abs(pb[0]) <= .5) or not (-.75 <= pb[1] <= -.1) or pm[1] > .9:
                            continue
                        # torch slot: air, supported by grass/dirt, 1.0-2.4 m from the trunk, in front of it, left/right opposite
                        best = None
                        for tx in range(bx - 3, bx + 4):
                            for tz in range(bz - 3, bz + 4):
                                td = math.hypot(tx + .5 - tc[0], tz + .5 - tc[1])
                                if not 1.0 <= td <= 2.4:
                                    continue
                                ty = None
                                for y in range(by + 3, by - 4, -1):
                                    if grid.cat(tx, y - 1, tz) in GOOD and grid.cat(tx, y, tz) == AIR and grid.cat(tx, y + 1, tz) == AIR:
                                        ty = y
                                        break
                                if ty is None or (tx, ty, tz) in ((cxi, fy, czi),):
                                    continue
                                flame = (tx + .5, ty + .65, tz + .5)
                                pt = project(flame, eye, yaw, pitch)
                                if not pt or abs(pt[0]) > .8 or not (-.65 <= pt[1] <= -.15) or pt[2] > project((tc[0], by, tc[1]), eye, yaw, pitch)[2] - .5:
                                    continue
                                if pt[0] * pb[0] > 0 or abs(pt[0] - pb[0]) < .35:
                                    continue
                                d = (flame[0] - eye[0], flame[1] - eye[1], flame[2] - eye[2])
                                n = math.sqrt(sum(v * v for v in d))
                                c, t, cell, _ = grid.cast(eye, tuple(v / n for v in d), n - .3)
                                if c != AIR:
                                    continue
                                fit = abs(pt[0] - (-math.copysign(.4, pb[0]))) + abs(pt[1] + .3)
                                if best is None or fit < best[0]:
                                    best = (fit, (tx, ty, tz), pt)
                        if best is None:
                            continue
                        score, fr, nt, pg = evaluate(grid, tree, cam, yaw, pitch, rng)
                        results.append({"score": round(score, 3), "tree": list(tree[:3]), "species": tree[4], "height": h,
                                        "camera_feet": list(cam), "yaw": round(yaw, 2), "pitch": pitch,
                                        "torch_cell": list(best[1]), "torch_ndc": [round(v, 3) for v in best[2][:2]],
                                        "trunk_base_ndc": [round(pb[0], 3), round(pb[1], 3)], "distance_to_trunk": round(math.hypot(cam[0] - tc[0], cam[2] - tc[1]), 2),
                                        "fractions": {k: round(v, 3) for k, v in fr.items()}, "other_trunks": nt, "plant_rays": pg})
        print(f"# tree {tree[:3]} done, results {len(results)}, {time.time() - t0:.0f}s", file=sys.stderr)
    results.sort(key=lambda r: -r["score"])
    best_per_tree, seen = [], set()
    for r in results:
        if tuple(r["tree"]) not in seen:
            seen.add(tuple(r["tree"]))
            best_per_tree.append(r)
    print(json.dumps({"time_of_day": TIME, "sun": SUN, "world_unchanged": w.unchanged(), "evaluated": len(results),
                      "best_per_tree": results[:top_n] if fine else best_per_tree[:top_n]}))


if __name__ == "__main__":
    main()
