"""Analytic, read-only validation of the chosen natural forest torch site. Writes forest-site.json next to this file.

No render is produced: everything below is voxel geometry derived from the saved Anvil chunks of the exact TEST save.
Usage: python3 -I site_report.py
"""
import json
import math
import sys
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from voxels import *  # noqa: E402,F401,F403
from worldread import UUID, SEED, WORLD, World, audit  # noqa: E402

CAMERA_FEET = (208.5, 64.0, 355.5)
YAW, PITCH = 12.7, -2.0
TREE = (209, 64, 360)
TORCH = (207, 64, 359)
DAY_TIME, NIGHT_TIME = 9800, 15500
EYE = 1.62
RENDER_CHUNKS = 12
INSTANCE = WORLD.parent.parent  # .../Aqualumen Lab/minecraft


def eye_pos():
    return (CAMERA_FEET[0], CAMERA_FEET[1] + EYE, CAMERA_FEET[2])


def flood_light(grid, source, level):
    """Vanilla-style block-light model: each step costs 1; opaque full blocks stop it. NOT a measurement."""
    seen = {source: level}
    q = deque([source])
    while q:
        c = q.popleft()
        v = seen[c]
        if v <= 1:
            continue
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (c[0] + d[0], c[1] + d[1], c[2] + d[2])
            if grid.cat(*n) in (LOG, GRASS, DIRT, SOLID, UNKNOWN) or seen.get(n, 0) >= v - 1:
                continue
            seen[n] = v - 1
            q.append(n)
    return seen


def chunk_status(world, radius):
    cx0, cz0 = math.floor(CAMERA_FEET[0]) // 16, math.floor(CAMERA_FEET[2]) // 16
    missing, notfull, ok = [], [], 0
    for cx in range(cx0 - radius - 1, cx0 + radius + 2):
        for cz in range(cz0 - radius - 1, cz0 + radius + 2):
            data = world.region_bytes(cx // 32, cz // 32)
            if data is None:
                missing.append([cx, cz])
                continue
            try:
                nbt, rec = audit.decode_chunk(data, None, cx, cz)
            except ValueError:
                missing.append([cx, cz])
                continue
            if nbt.get("Status") != "minecraft:full":
                notfull.append([cx, cz, nbt.get("Status")])
            else:
                ok += 1
    return {"center_chunk": [cx0, cz0], "radius_checked": radius + 1, "chunks_full": ok,
            "missing_or_absent": missing, "not_full": notfull}


def main():
    world = World()
    marker = world.marker
    grid = Grid(world, 120, 270, 300, 450, 50, 112)
    eye = eye_pos()
    sun = sun_direction(DAY_TIME)
    out = {"schema": 1, "utc": datetime.now(timezone.utc).isoformat(), "world": str(WORLD), "world_id": UUID, "seed": SEED,
           "marker": marker, "time_day": DAY_TIME, "time_night_optional": NIGHT_TIME}

    # ---- camera ----
    bx, by, bz = TREE
    cam_cells = {f"feet+{k}": grid.cat(int(CAMERA_FEET[0]), int(CAMERA_FEET[1]) + k, int(CAMERA_FEET[2])) for k in range(3)}
    support = world.name(int(CAMERA_FEET[0]), int(CAMERA_FEET[1]) - 1, int(CAMERA_FEET[2]))
    body = [(int(CAMERA_FEET[0]) + a, int(CAMERA_FEET[1]) + b, int(CAMERA_FEET[2]) + c) for a in (-1, 0, 1) for c in (-1, 0, 1) for b in (0, 1)]
    body_names = Counter(world.name(*p) for p in body)
    out["camera"] = {"feet": CAMERA_FEET, "eye": eye, "yaw": YAW, "pitch": PITCH, "eye_height": EYE,
                     "support_block_below_feet": support, "feet_eye_head_cells_exact": [world.name(int(CAMERA_FEET[0]), int(CAMERA_FEET[1]) + k, int(CAMERA_FEET[2])) for k in range(3)],
                     "body_3x3x2_block_names": dict(body_names),
                     "distance_to_trunk_base_m": round(math.hypot(CAMERA_FEET[0] - (bx + .5), CAMERA_FEET[2] - (bz + .5)), 3),
                     "platform": False, "note": "spectator camera hovers at the natural ground cell; no block is placed for it"}

    # ---- torch slot ----
    tx, ty, tz = TORCH
    flame = (tx + .5, ty + .65, tz + .5)
    d = [flame[i] - eye[i] for i in range(3)]
    dist = math.sqrt(sum(v * v for v in d))
    hit = grid.cast(eye, tuple(v / dist for v in d), dist - .3)
    pt = project(flame, eye, YAW, PITCH)
    out["torch_slot"] = {"cell": TORCH, "state_now": world.state(*TORCH), "support_cell": [tx, ty - 1, tz],
                         "support_state": world.state(tx, ty - 1, tz), "cell_above_state": world.state(tx, ty + 1, tz),
                         "four_horizontal_neighbours": {n: world.name(tx + dx, ty, tz + dz) for n, (dx, dz) in
                                                         {"+x": (1, 0), "-x": (-1, 0), "+z": (0, 1), "-z": (0, -1)}.items()},
                         "flame_centre": flame, "camera_to_flame_m": round(dist, 3),
                         "camera_to_flame_first_blocker_before_flame": None if hit[0] == AIR else [NAMES[hit[0]], hit[2]],
                         "ndc": [round(pt[0], 4), round(pt[1], 4)],
                         "pixel_2560x1440_fov70": [round((pt[0] + 1) / 2 * 2560, 1), round((1 - pt[1]) / 2 * 1440, 1)],
                         "distance_to_trunk_axis_m": round(math.hypot(tx + .5 - (bx + .5), tz + .5 - (bz + .5)), 3),
                         "variants": {"off": None, "warm": "minecraft:torch", "soul": "minecraft:soul_torch"},
                         "block_light_emission": {"minecraft:torch": 14, "minecraft:soul_torch": 10}}

    # ---- tree and distant foliage ----
    logs = [(bx, by + k, bz) for k in range(12) if world.name(bx, by + k, bz) and world.name(bx, by + k, bz).endswith("_log")]
    log_states = [(p, world.state(*p)) for p in logs]
    base = world.state(bx, by - 1, bz)
    crown = []
    for dx in range(-3, 4):
        for dz in range(-3, 4):
            for dy in range(2, len(logs) + 3):
                s = world.state(bx + dx, by + dy, bz + dz)
                if s and s["Name"].endswith("_leaves"):
                    crown.append(((bx + dx, by + dy, bz + dz), s))
    out["tree"] = {"base": TREE, "species": log_states[0][1]["Name"], "trunk_height": len(logs), "ground_state_below": base,
                   "log_states": [{"cell": p, "state": s} for p, s in log_states],
                   "crown_leaves_within_3_blocks": len(crown),
                   "crown_leaves_persistent_false": sum(s.get("Properties", {}).get("persistent") == "false" for _, s in crown),
                   "genuine_natural_evidence": "leaves are persistent=false (player-placed leaves would be persistent=true); trunk base is the generator's dirt (tree placement converts grass to dirt); "
                                               "regions are the vanilla noise-generated overworld of seed 308060; no log/leaf/dirt cell here is in any benchmark fixture plot"}

    # ---- composition rays, 96x54 ----
    n_x, n_y = 96, 54
    fr = Counter()
    existing_cells = {}
    near_leaves, far_leaves, far_logs, trunk_hits = {}, {}, {}, 0
    ndc_hits = {}
    plants_seen = 0
    for i in range(n_x):
        for j in range(n_y):
            nx, ny = -1 + (i + .5) * 2 / n_x, -1 + (j + .5) * 2 / n_y
            dd = ray_dir(nx, ny, YAW, PITCH)
            c, t, cell, pl = grid.cast(eye, dd, 96)
            plants_seen += pl > 0
            if c == AIR:
                fr["sky"] += 1
            elif c == LEAVES:
                fr["leaves<6m" if t < 6 else "leaves6-16m" if t < 16 else "leaves>16m"] += 1
                (near_leaves if t < 8 else far_leaves).setdefault(cell, (t, nx, ny))
            elif c == LOG:
                if cell[0] == bx and cell[2] == bz:
                    fr["target_trunk"] += 1
                    trunk_hits += 1
                else:
                    fr["other_trunks"] += 1
                    if t >= 8:
                        far_logs.setdefault(cell, (t, nx, ny))
            elif c in (GRASS, DIRT):
                fr["ground"] += 1
            elif c == WATER:
                fr["water"] += 1
            elif c == UNKNOWN:
                fr["outside_grid_unknown"] += 1
            else:
                fr["other_solid"] += 1
    total = n_x * n_y
    out["composition_rays_96x54"] = {"fractions": {k: round(v / total, 4) for k, v in sorted(fr.items())},
                                     "rays_through_plants_before_first_solid": plants_seen,
                                     "method": "voxel DDA from the exact eye; sky = no block within 96 m; first-hit categories; analytic, not a render",
                                     "fov_vertical_deg": FOV_V, "aspect": 16 / 9}
    # pick deterministic evidence cells: leaves/logs spread over the screen, nearest first
    def spread(d, limit):
        picked, buckets = [], set()
        for cell, (t, nx, ny) in sorted(d.items(), key=lambda kv: kv[1][0]):
            b = (int((nx + 1) * 3), int((ny + 1) * 3), int(t // 12))
            if b in buckets:
                continue
            buckets.add(b)
            picked.append(cell)
            if len(picked) >= limit:
                break
        return picked
    for label, picks in (("near_foliage", spread(near_leaves, 14)), ("distant_foliage", spread(far_leaves, 26)), ("distant_trunks", spread(far_logs, 6))):
        for cell in picks:
            s = world.state(*cell)
            props = s.get("Properties", {})
            need = []
            if s["Name"].endswith("_leaves"):
                need = ["persistent=" + props.get("persistent", "false")]
            elif s["Name"].endswith("_log"):
                need = ["axis=" + props.get("axis", "y")]
            existing_cells[cell] = {"role": label, "id": s["Name"], "required_state_substrings": need,
                                    "distance_m": round((near_leaves.get(cell) or far_leaves.get(cell) or far_logs.get(cell))[0], 2)}
    for p, s in log_states:
        existing_cells[p] = {"role": "target_trunk_log", "id": s["Name"], "required_state_substrings": ["axis=y"], "distance_m": None}
    existing_cells[(bx, by - 1, bz)] = {"role": "trunk_base_dirt", "id": base["Name"], "required_state_substrings": [], "distance_m": None}
    existing_cells[(tx, ty - 1, tz)] = {"role": "torch_support", "id": world.name(tx, ty - 1, tz), "required_state_substrings": [], "distance_m": None}
    existing_cells[(int(CAMERA_FEET[0]), int(CAMERA_FEET[1]) - 1, int(CAMERA_FEET[2]))] = {"role": "camera_support", "id": support, "required_state_substrings": [], "distance_m": None}
    out["existing_verified_cells"] = [{"cell": list(c), **v} for c, v in sorted(existing_cells.items())]
    out["existing_verified_cells_count"] = len(existing_cells)

    # ---- reserved exact-air cells ----
    reserved = [TORCH, (tx, ty + 1, tz)] + [(int(CAMERA_FEET[0]), int(CAMERA_FEET[1]) + k, int(CAMERA_FEET[2])) for k in range(3)]
    out["reserved_exact_air_cells"] = [{"cell": list(c), "state_now": world.state(*c)} for c in reserved]
    out["reserved_all_exact_air_in_save"] = all(world.state(*c) == {"Name": "minecraft:air"} for c in reserved)

    # ---- solar shade and modelled block light ----
    sample_points = {"trunk_camera_face_mid": (bx + .5 + 0.0, by + 1.5, bz - .001), "trunk_camera_face_low": (bx + .5, by + .5, bz - .001),
                     "ground_in_front_of_torch": (tx + .5, ty + .001, tz + .5 - 1.0), "torch_base": (tx + .5, ty + .001, tz + .5)}
    shade = {}
    for name, p in sample_points.items():
        c, t, cell, _ = grid.cast(p, sun, 80)
        exited_top = c == UNKNOWN and cell is not None and cell[1] >= grid.y0 + grid.H  # ray left through the grid ceiling: nothing blocks it
        blocked = c != AIR and not exited_top
        shade[name] = {"point": p, "sun_ray_first_blocker": [NAMES[c], list(cell) if cell else None, round(t, 2)] if blocked else None,
                       "ray_exited_grid_ceiling_unblocked": exited_top, "lab_geometry_shaded": blocked}
    out["solar"] = {"time_of_day": DAY_TIME, "sun_direction_xyz": sun, "elevation_deg": round(math.degrees(math.asin(sun[1])), 1),
                    "azimuth_note": "vanilla path: sun travels toward -X in the afternoon; this view faces +Z so the sun is on the camera's right",
                    "shade_by_voxel_ray": shade, "method": "leaves treated as blocking; analytical lab geometry, not a measurement"}
    light = {}
    for variant, lvl in (("warm", 14), ("soul", 10)):
        field = flood_light(grid, TORCH, lvl)
        pts = {"trunk_camera_face_air_cell": (bx, by + 1, bz - 1), "ground_in_front_of_torch": (tx, ty, tz - 1), "camera_eye_cell": (int(eye[0]), int(eye[1]), int(eye[2])),
               "torch_cell": TORCH, "two_blocks_toward_camera": (tx, ty, tz - 2), "four_blocks_toward_camera": (tx, ty, tz - 4)}
        light[variant] = {"emission": lvl, "model_levels": {k: field.get(v, 0) for k, v in pts.items()},
                          "cells_lit": len(field), "reach_blocks_horizontal_max": max(abs(c[0] - tx) + abs(c[2] - tz) for c in field)}
    out["modelled_block_light"] = {"method": "flood fill: cost 1 per cell, opaque full blocks stop; NOT a measurement of Minecraft's light engine", "variants": light}

    # ---- safety ----
    journals = {n: (INSTANCE / "aqualumen-benchmark" / n).exists() for n in ("opaque-fixture-journal.json", "local-light-fixture-journal.json")}
    out["safety"] = {"pending_fixture_journals": journals, "any_pending_journal": any(journals.values()),
                     "overlap_with_other_fixtures": {
                         "min_x_gap_to_natural_shore_plot_blocks": min(abs(x - 136) for x in (int(CAMERA_FEET[0]), tx, bx)),
                         "natural_shore_plot_bounds": [130, 63, 341, 136, 66, 343],
                         "note": "x=207..209 z=355..360 is >70 blocks from every audit-fixture-air plot (x 426..452, z -387..-233), the natural-shore plot (x130..136, z341..343) and the LocalLightFixture box (x400..413, z-420..-401)"},
                     "chunks_in_render_radius": chunk_status(world, RENDER_CHUNKS),
                     "save_unchanged_during_analysis": world.unchanged(),
                     "writes": False}
    (HERE / "forest-site.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("camera", "torch_slot", "reserved_all_exact_air_in_save", "composition_rays_96x54", "existing_verified_cells_count", "solar", "modelled_block_light", "safety")}, indent=1))


if __name__ == "__main__":
    main()
