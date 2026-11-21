"""CPU-only saved-terrain ray join for the one authorized same-frame snapshot."""
import argparse
import collections
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OBSERVATION = "259d112e-d967-4cd3-9aaf-148b28c53a4c"
WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d"
PACK_SHA = "ccd937b89156df9104e6bd1106bae1100f163498242ab1ec8e0ddc89dfe98180"
CAMERA = [-191.5, 65.71999988555908, 320.5]
PASS = {"minecraft:" + name for name in ("air", "cave_air", "void_air", "water", "seagrass", "tall_seagrass", "kelp", "kelp_plant")}
FULL = {"minecraft:" + name for name in ("sand", "gravel", "dirt", "stone", "clay", "sandstone", "granite", "diorite",
          "andesite", "deepslate", "coal_ore", "copper_ore", "moss_block", "grass_block", "bedrock")}


def require(value, message):
    if not value:
        raise ValueError(message)


def norm(vector):
    return math.sqrt(sum(value * value for value in vector))


def point_at(origin, direction, t):
    return [origin[i] + direction[i] * t for i in range(3)]


def shape(state):
    if state["Name"] in PASS:
        return "ignored_air_fluid_or_water_plant"
    if state["Name"] in FULL and state.get("Properties", {}).get("waterlogged") != "true":
        return "known_full_cube"
    return "unknown_shape"


def dda(origin, direction, cell, limit=48.0):
    """First positive-volume voxel entry, using the supplied ray unchanged.

    ``cell`` is the read-only world boundary. Unknown block shapes stop the
    qualification; they are never silently treated as solid cubes or empty.
    Simultaneous boundary crossings step all tied axes, avoiding phantom hits
    in side cells that the ray touches only at an edge/corner.
    """
    require(len(origin) == len(direction) == 3 and all(math.isfinite(x) for x in (*origin, *direction)) and
            norm(direction) > 0 and 0 < limit <= 48, "Invalid bounded DDA ray")
    voxel = [math.floor(value) for value in origin]
    steps = [1 if d > 0 else -1 if d < 0 else 0 for d in direction]
    for axis in range(3):
        if steps[axis] < 0 and origin[axis] == voxel[axis]:
            voxel[axis] -= 1
    next_t, delta = [], []
    for axis, d in enumerate(direction):
        if d == 0:
            next_t.append(math.inf); delta.append(math.inf)
        else:
            boundary = voxel[axis] + (1 if steps[axis] > 0 else 0)
            next_t.append((boundary - origin[axis]) / d)
            delta.append(abs(1 / d))
    t, entered_axes = 0.0, []
    for _ in range(512):
        state = cell(*voxel)
        kind = shape(state)
        if kind != "ignored_air_fluid_or_water_plant":
            return {"status": "hit_known_full_cube" if kind == "known_full_cube" else "unknown_shape_before_qualified_hit",
                    "t": t, "ray_length_m": t * norm(direction), "point": point_at(origin, direction, t),
                    "block": list(voxel), "state": state, "saved_shape": kind,
                    "entered_axes": entered_axes, "entry_normals": [[(-steps[a] if i == a else 0) for i in range(3)] for a in entered_axes],
                    "starts_inside_or_on_forward_solid": t == 0.0}
        t = min(next_t)
        if t > limit:
            return {"status": "no_known_collision_within_48m", "maximum_t": limit}
        entered_axes = [a for a in range(3) if abs(next_t[a] - t) <= 1e-12]
        for axis in entered_axes:
            voxel[axis] += steps[axis]
            next_t[axis] += delta[axis]
    raise ValueError("DDA step bound exceeded")


def self_test():
    def known_voxel(x, y, z):
        return {"Name": "minecraft:sand" if (x, y, z) == (0, 0, 0) else "minecraft:air"}
    hit = dda((.5, 2.5, .5), (0., -1., 0.), known_voxel)
    assert hit is not None and hit["t"] == 1.5 and hit["point"] == [.5, 1., .5], "known voxel top boundary must be hit exactly at t=1.5"
    assert hit["block"] == [0, 0, 0] and hit["entry_normals"] == [[0, 1, 0]]

    def voxels(states):
        return lambda x, y, z: {"Name": states.get((x, y, z), "minecraft:air")}

    negative = dda((-.5, 2.5, -.5), (0., -1., 0.), voxels({(-1, 0, -1): "minecraft:sand"}))
    assert negative["block"] == [-1, 0, -1] and negative["point"] == [-.5, 1., -.5] and negative["t"] == 1.5

    away = dda((0., .5, .5), (-1., 0., 0.), known_voxel)
    assert away["status"] == "no_known_collision_within_48m", "ray leaving a boundary must not collide with the cube behind it"
    forward = dda((0., .5, .5), (-1., 0., 0.), voxels({(-1, 0, 0): "minecraft:sand"}))
    assert forward["t"] == 0 and forward["block"] == [-1, 0, 0] and forward["starts_inside_or_on_forward_solid"]

    diagonal = dda((.5, .5, .5), (math.sqrt(.5), math.sqrt(.5), 0.),
                   voxels({(1, 0, 0): "minecraft:sand", (2, 2, 0): "minecraft:sand"}))
    assert diagonal["block"] == [2, 2, 0] and diagonal["entered_axes"] == [0, 1]
    assert math.isclose(diagonal["t"], 1.5 * math.sqrt(2), abs_tol=1e-12)
    assert math.dist(diagonal["point"], [2., 2., .5]) < 1e-12, "corner-only side cells must not become phantom collisions"

    unknown = dda((.5, 2.5, .5), (0., -1., 0.),
                  voxels({(0, 1, 0): "minecraft:stone_slab", (0, 0, 0): "minecraft:sand"}))
    assert unknown["status"] == "unknown_shape_before_qualified_hit" and unknown["t"] == .5
    assert unknown["state"]["Name"] == "minecraft:stone_slab", "unknown shapes must stop qualification rather than become full cubes or empty"
    bounded_hit = dda((.5, .5, .5), (1., 0., 0.), voxels({(49, 0, 0): "minecraft:sand"}))
    assert bounded_hit["status"] == "no_known_collision_within_48m" and bounded_hit["maximum_t"] == 48
    return {"passed": True, "tests": ["known voxel top boundary at t1.5; exact point/block/upward face",
                "negative coordinates use floor and exact voxel boundary", "integer origin selects forward cell; cube behind ray excluded",
                "integer origin inside forward solid classified at t0", "tied corner axes skip touched-only side cell",
                "unknown partial block stops first-hit qualification", "collision beyond 48m is excluded"]}


def bounded(path, limit):
    require(not path.is_symlink(), "Evidence symlink is forbidden")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, "Bounded evidence read exceeded")
    return raw


class SavedWorld:
    def __init__(self):
        spec = importlib.util.spec_from_file_location("shore_ray_anvil", REPO / "tools/audit-fixture-air.py")
        self.decoder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.decoder)
        world = self.decoder.WORLD
        require(world.resolve() == world.absolute(), "World symlink redirection is forbidden")
        marker = dict(line.split("=", 1) for line in (world / "aqualumen-world.properties").read_text().splitlines()
                      if line and not line.startswith("#"))
        self.decoder.validate_marker(world.name, marker)
        self.marker = {key: marker[key] for key in ("world_id", "seed", "schema", "generator")}
        self.path = world / "region/r.-1.0.mca"
        self.before = self.path.stat()
        require(8192 <= self.before.st_size <= self.decoder.LIMIT, "Region size outside bounded plan")
        self.raw = bounded(self.path, self.decoder.LIMIT)
        require(len(self.raw) == self.before.st_size, "Region changed during initial read")
        self.chunks = {}
        self.states = collections.Counter()

    def cell(self, x, y, z):
        require((x // 512, z // 512) == (-1, 0) and 0 <= y <= 80, "Ray left authorized bounded saved region")
        key = (x // 16, z // 16)
        if key not in self.chunks:
            self.chunks[key] = self.decoder.decode_chunk(self.raw, self.path, *key)[0]
        state = self.decoder.block_state(self.chunks[key], x, y, z)
        self.states[state["Name"]] += 1
        return state

    def finish(self):
        after = self.path.stat()
        require((self.before.st_size, self.before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
                "Saved region changed during audit; result rejected")
        return {"name": self.path.name, "sha256": hashlib.sha256(self.raw).hexdigest(), "size_bytes": len(self.raw),
                "mtime_ns_before": self.before.st_mtime_ns, "mtime_ns_after": after.st_mtime_ns,
                "stable_size_and_mtime_during_read": True, "decoded_chunks": len(self.chunks),
                "data_version": 3955, "marker_verified": self.marker,
                "state_query_counts_not_unique_cells": dict(self.states)}


def nearest_exposed_face(q, cell):
    """Nearest full-cube face in a bounded 3³ neighbourhood of Q.

    Only a known pass-through neighbour qualifies a face as exposed. This is
    geometry distance, NOT camera visibility; unknown shapes are not asserted
    to expose or hide anything. Distant or entity-only Q returns no local face.
    """
    centre = [math.floor(value) for value in q]
    best = None
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                block = [centre[0] + dx, centre[1] + dy, centre[2] + dz]
                state = cell(*block)
                if shape(state) != "known_full_cube":
                    continue
                for axis in range(3):
                    for side in (-1, 1):
                        neighbour = block.copy(); neighbour[axis] += side
                        if shape(cell(*neighbour)) != "ignored_air_fluid_or_water_plant":
                            continue
                        candidate = [min(max(q[i], block[i]), block[i] + 1) for i in range(3)]
                        candidate[axis] = block[axis] + (side == 1)
                        distance = math.dist(candidate, q)
                        if best is None or distance < best["distance_m"]:
                            best = {"distance_m": distance, "point": candidate, "block": block,
                                    "state": state, "axis": axis, "side": side, "shape": "known_exposed_full_cube_face"}
    return best


def local_saved_depth(p, cell):
    x, z = math.floor(p[0]), math.floor(p[2])
    for y in range(62, -1, -1):
        state = cell(x, y, z)
        if state["Name"] in PASS and state["Name"] not in {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}:
            continue
        if shape(state) == "known_full_cube":
            return {"column": [x, z], "bed_top_y": y + 1, "state": state,
                    "nominal_mean_surface_depth_m": 62.88888931274414 - (y + 1)}
        return {"column": [x, z], "status": "unknown_or_disconnected_column", "first_state": state}
    return {"status": "no_qualified_support_to_Y0"}


def join():
    path = HERE / "observations" / (OBSERVATION + ".json")
    raw = bounded(path, 2 * 1024 * 1024)
    data = json.loads(raw)
    require(data.get("available") is True and data.get("stateRestored") is True and data.get("scopeAuthorized") is True,
            "Raw snapshot availability/state/scope guard failed")
    require(data.get("requestId") == OBSERVATION and data.get("worldId") == WORLD_ID and data.get("world") == "AqualumenNaturalV2" and
            data.get("seed") == 308060 and data.get("dimension") == "minecraft:overworld" and
            data.get("packSha256") == PACK_SHA and data.get("snapshotFrame") == 11329 and
            [data.get("width"), data.get("height")] == [1600, 900] and
            data.get("unshiftedCameraPosition") == CAMERA and data.get("selectedTexelsFiniteOnly") is True,
            "Raw snapshot identity/pose/frame guard failed")
    pack = bounded(HERE / "tools/Aqualumen-ShoreProbe-world-r3.zip", 64 * 1024 * 1024)
    require(hashlib.sha256(pack).hexdigest() == PACK_SHA, "Saved probe ZIP identity mismatch")
    with zipfile.ZipFile(HERE / "tools/Aqualumen-ShoreProbe-world-r3.zip") as archive:
        source = archive.read("shaders/gbuffers_water.fsh")
    require(len(source) <= 1024 * 1024, "Probe source exceeds bounded plan")
    require(b"/* RENDERTARGETS:0,9,10,11,12,13,14,15 */" in source, "Direct MRT target mapping differs from audited semantics")
    for index, expression in enumerate((b"vec4(absolutePosition,localColumnKnown?1.0:0.0)", b"vec4(transmitted,receiverConfidence)",
                       b"vec4(probeReceiver,float(receiverKind))", b"vec4(thickness,initialPath,verticalDepth,straightPath)",
                       b"vec4(opaqueWorld+cameraPosition,localColumn.x)", b"vec4(n,fresnel)"), start=2):
        require(f"gl_FragData[{index}]=".encode() + expression + b";" in source, "Direct MRT payload definition differs from audited semantics")
    fields = {}
    for sampler in data["samplers"]:
        if sampler["name"] not in {"colortex" + str(index) for index in range(10, 16)}:
            continue
        require(sampler.get("active") is True and sampler.get("textureExists") is True and sampler.get("actualFormat") == 34836 and
                [sampler.get("width"), sampler.get("height")] == [1600, 900], "Raw field storage mismatch")
        samples = {(sample["x"], sample["y"]): sample["rgba"] for sample in sampler["samples"]}
        require(len(samples) == 16 and all(len(v) == 4 and all(math.isfinite(x) for x in v) for v in samples.values()), "Invalid raw field samples")
        fields[int(sampler["name"][8:])] = samples
    require(set(fields) == set(range(10, 16)) and all(set(fields[10]) == set(v) for v in fields.values()), "Field coordinates are not aligned")
    world = SavedWorld()
    results, excluded = [], []
    for coordinate, c10 in fields[10].items():
        p, direction, normal = c10[:3], fields[11][coordinate][:3], fields[15][coordinate][:3]
        if not (62.8 <= p[1] <= 62.92 and c10[3] == 1.0 and abs(norm(direction) - 1) < 1e-5 and
                abs(norm(normal) - 1) < 1e-5 and normal[1] > .5 and direction[1] < -.02):
            excluded.append({"pixel": list(coordinate), "reason": "nonwater/zero or unqualified surface/ray/normal"})
            continue
        require(-216 <= p[0] <= -168 and 320 <= p[2] <= 384, "Water point outside authorized coast bounds")
        c11, c12, c13, c14, c15 = [fields[index][coordinate] for index in range(11, 16)]
        q, kind, thickness = c12[:3], c12[3], c13[0]
        require(kind in (0., 1., 2.) and 0 <= c11[3] <= 1 and 0 <= c15[3] <= 1 and 0 <= thickness <= 48,
                "Invalid exported kind/confidence/Fresnel/path")
        hit = dda(p, direction, world.cell)
        prediction = point_at(p, direction, thickness)
        projected_t = sum((q[i] - p[i]) * direction[i] for i in range(3)) / sum(d * d for d in direction)
        row = {"pixel": list(coordinate), "surface_absolute": p, "transmitted_direction": direction, "direction_norm": norm(direction),
               "optical_normal": normal, "normal_norm": norm(normal), "fresnel": c15[3], "receiver_kind": int(kind),
               "confidence": c11[3], "returned_receiver_absolute": q, "returned_uv_itself_recorded": False,
               "original_screen_opaque_absolute": c14[:3], "local_shader_column_depth_m": c14[3],
               "shader_thickness_m": thickness, "initial_seed_m": c13[1], "shader_vertical_depth_m": c13[2],
               "shader_straight_path_m": c13[3], "saved_local_column": local_saved_depth(p, world.cell),
               "saved_first_collision": hit, "P_plus_D_thickness": prediction,
               "returned_Q_vs_P_plus_D_thickness_distance_m": math.dist(q, prediction),
               "returned_Q_projected_ray_t": projected_t,
               "returned_Q_perpendicular_ray_residual_m": math.dist(q, point_at(p, direction, projected_t)),
               "returned_Q_nearest_saved_exposed_cube_face": nearest_exposed_face(q, world.cell),
               "interpretation": "accepted screen-space receiver; compare Q to saved terrain conditionally" if kind == 1 else
                   "unknown/miss proxy; thickness and returned original-screen Q are NOT an accepted transmitted hit"}
        if hit["status"] == "hit_known_full_cube" and not hit["starts_inside_or_on_forward_solid"]:
            row["shader_thickness_minus_saved_first_t_m"] = thickness - hit["t"]
            row["returned_Q_vs_saved_first_point_distance_m"] = math.dist(q, hit["point"])
        results.append(row)
    require(len(results) == 13 and len(excluded) == 3, "Qualified/excluded sample count changed")
    return {"schema": 1, "audit": "actual same-frame exported rays versus saved terrain, conditional absolute-coordinate join",
            "observed_utc": datetime.now(timezone.utc).isoformat(), "completed": True,
            "observation": {"file": path.name, "sha256": hashlib.sha256(raw).hexdigest(), "frame": 11329,
                            "pack_sha256": PACK_SHA, "probe_water_source_sha256": hashlib.sha256(source).hexdigest(),
                            "camera_absolute": CAMERA, "coordinate_source": "direct absolute positions exported by water MRT; not inverse-projection reconstruction",
                            "geometryUniformsAvailable": data["geometryUniformsAvailable"],
                            "geometryAttributionAccepted": data["geometryAttributionAccepted"],
                            "runtimeIntegrationAccepted": data["runtimeIntegrationAccepted"]},
            "saved_region": world.finish(), "qualified_points": 13, "excluded_points": excluded, "points": results,
            "known_full_cube_names": sorted(FULL), "ignored_names": sorted(PASS),
            "limits": {"screen_visibility_proven": False, "entities_included": False, "partial_block_shapes_assumed_full_cubes": False,
                       "water_membership_proven": False, "wave_start_mean_surface_tolerance_m": .1,
                       "same_frame_saved_terrain_proven": False, "absolute_coordinate_payload_independently_calibrated": False,
                       "shader_geometry_observer_flags_overridden": False, "ray_limit_m": 48,
                       "ordinary_world_read": False, "world_writes": False, "game_or_gpu_calls": False,
                       "note": "First saved full-cube collision is independent of screen depth. A screen receiver can be a plant/entity or terrain not camera-visible; acceptance kind1 is not alone world first-hit proof. Mean-plane±0.1m wave start is not water-membership proof. Unknown shapes stop first-hit qualification; no global water-quality completion is implied."}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write", action="store_true", help="Generate only adjacent ray-join.json")
    args = parser.parse_args()
    try:
        if args.self_test:
            print(json.dumps(self_test(), indent=2))
        else:
            result = join()
            result["cpu_tests"] = self_test()
            result["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            destination = HERE / "ray-join.json"
            if destination.exists():
                prior = json.loads(bounded(destination, 2 * 1024 * 1024))
                if "cpu_test_first_failure" in prior:
                    result["cpu_test_first_failure"] = prior["cpu_test_first_failure"]
            if args.write:
                destination.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            print(json.dumps({"completed": result["completed"], "qualified": result["qualified_points"],
                              "kind_counts": dict(collections.Counter(str(p["receiver_kind"]) for p in result["points"])),
                              "hit_status_counts": dict(collections.Counter(p["saved_first_collision"]["status"] for p in result["points"])),
                              "points": [{"pixel": p["pixel"], "kind": p["receiver_kind"], "shader_t": p["shader_thickness_m"],
                                          "saved_t": p["saved_first_collision"].get("t"), "block": p["saved_first_collision"].get("block"),
                                          "Q_face_distance": (p["returned_Q_nearest_saved_exposed_cube_face"] or {}).get("distance_m")}
                                         for p in result["points"]]}, indent=2))
    except Exception as error:
        print(json.dumps({"completed": False, "error_class": type(error).__name__,
                          "reason": str(error) if isinstance(error, (ValueError, AssertionError)) else "bounded audit boundary failed"}))
        raise SystemExit(1)
