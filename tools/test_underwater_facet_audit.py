#!/usr/bin/env python3
"""Independent CPU audit of saved TEST-only optical-facet A/B evidence.

Self-test fixtures are synthetic metadata/readbacks, never shader experiments.
The CLI reads completed evidence only and prints JSON; it writes no artifacts.
"""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess
import sys
import unittest
from zipfile import ZipFile

sys.dont_write_bytecode = True
import report
from test_thin_runtime_audit import read_intervals

WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d"
SIZE = [1600, 900]
PACKS = {
    "control": ("Aqualumen-ShoreProbe-world-underwater-atlas-086-phase120-v1.zip",
                "8b054a95693a997cde7c3b8f8d4097f593309584067ac1d3c9c77887dba4239d"),
    "facet": ("Aqualumen-ShoreProbe-world-underwater-facet-atlas-086-phase120-v1.zip",
              "8cac459d1ae717bc83719c6a0c76e950b5b05926e4124d5134a004115f97dd9b")}
INTERIOR = {(801, 451), (401, 451), (1201, 451), (801, 251)}
EDGE = {(33, 451), (65, 451), (129, 451), (193, 451), (1409, 451), (1473, 451),
        (1537, 451), (1567, 451), (129, 129), (1473, 129), (129, 771), (1473, 771)}
POINTS = INTERIOR | EDGE
STATE_FIELDS = {"active", "binding", "packBuffer", "alignment", "rowLength", "imageHeight",
                "skipPixels", "skipRows", "skipImages", "swap", "lsb"}


def require(value, message):
    if not value:
        raise ValueError(message)


def finite(values, count):
    return isinstance(values, list) and len(values) == count and all(type(x) in (int, float) and math.isfinite(x) for x in values)


def snapshot(document, role, scene):
    """Typed saved observer boundary, not a GL call or geometric reconstruction."""
    name, sha = PACKS[role]
    require(all(document.get(key) is True for key in ("available", "stateRestored", "scopeAuthorized", "timingAcceptanceExcluded", "selectedTexelsFiniteOnly")), "Failed raw observation guard")
    require(document.get("packName") == name and document.get("packSha256") == sha, "Wrong diagnostic pack")
    require(document.get("worldId") == WORLD_ID and document.get("world") == "AqualumenNaturalV2" and
            type(document.get("seed")) is int and document["seed"] == 308060 and document.get("dimension") == "minecraft:overworld", "Wrong disposable world")
    require(document.get("observerVersion") == "0.3.9" and document.get("tag") == "DEBUG-shore-sampler" and
            document.get("seam") == "FinalPassRenderer.renderFinalPass before FullScreenQuadRenderer.renderQuad; after Program.use and CustomUniforms.push", "Wrong observer seam")
    require(type(document.get("program")) is int and document["program"] > 0 and document["program"] == document.get("expectedProgram"), "Unknown current program")
    require([document.get("width"), document.get("height")] == SIZE and document.get("renderer") == "NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2", "Wrong raw target/renderer")
    expected_camera = [448.5, 59.63899988555908 if scene == "deep" else 62.38899988555908, -383.5]
    camera = document.get("unshiftedCameraPosition")
    require(finite(camera, 3) and math.dist(camera, expected_camera) <= .05, "Wrong held-view camera")
    require(type(document.get("snapshotFrame")) is int and document["snapshotFrame"] > 0 and
            type(document.get("frameTimeCounter")) in (int, float) and math.isfinite(document["frameTimeCounter"]), "Missing actual observer clock")
    require(all(document.get(key) is False for key in ("geometryAttributionAccepted", "runtimeIntegrationAccepted", "visualQualityAccepted")), "Overclaimed acceptance")
    require(document.get("errorFlagPolicy") == "untouched; adapter must not consume or clear GL error flags", "Unknown error-flag policy")
    before, after = document.get("stateBefore"), document.get("stateAfter")
    require(isinstance(before, dict) and isinstance(after, dict) and set(before) == set(after) == STATE_FIELDS and
            all(type(v) is int for v in before.values()) and all(type(v) is int for v in after.values()) and before == after, "Eleven GL states not restored")
    require(document.get("maximumSelectedTexels") == 16 and document.get("texelCoordinateConvention") == "integer level-zero texture coordinates; bottom-left origin" and
            document.get("samplingInterpretation") == "unfiltered level-zero texels, not tone-mapped or reconstructed FINAL texture() values", "Unknown raw readback contract")
    entries = document.get("samplers")
    require(isinstance(entries, list) and all(isinstance(s, dict) for s in entries), "Missing raw samplers")
    names = [s.get("name") for s in entries]
    require(len(set(names)) == len(names) and sum(s.get("active") is True for s in entries) == 3, "Duplicate or extra active sampler")
    samplers = {s["name"]: s for s in entries}
    maps, units, textures, locations = {}, [], [], []
    for index in (9, 10, 11):
        key = f"colortex{index}"
        s = samplers.get(key, {})
        require(s.get("active") is True and type(s.get("location")) is int and s["location"] >= 0 and
                type(s.get("type")) is int and s["type"] == 35678 and type(s.get("size")) is int and s["size"] == 1, "Inactive/non-scalar sampler")
        require(type(s.get("unit")) is int and s["unit"] >= 0 and type(s.get("textureId")) is int and s["textureId"] > 0 and
                s.get("textureExists") is True and s.get("actualFormat") == 34836 and [s.get("width"), s.get("height")] == SIZE, "Wrong actual RGBA32F binding")
        units.append(s["unit"]); textures.append(s["textureId"]); locations.append(s["location"])
        samples = s.get("samples")
        require(isinstance(samples, list) and len(samples) == 16, "Missing selected texels")
        rows = {}
        for sample in samples:
            require(isinstance(sample, dict) and type(sample.get("x")) is int and type(sample.get("y")) is int, "Noninteger texel coordinate")
            coordinate = sample["x"], sample["y"]
            require(coordinate in POINTS and coordinate not in rows, "Unexpected/repeated selected coordinate")
            rgba = sample.get("rgba")
            require(finite(rgba, 4), "Nonfinite readback")
            try:
                exact = all(struct.unpack("<f", struct.pack("<f", value))[0] == value for value in rgba)
            except (OverflowError, struct.error):
                exact = False
            require(exact, "Lossy source float32 JSON")
            rows[coordinate] = rgba
        require(set(rows) == POINTS, "Selected coordinate coverage changed")
        maps[key] = rows
    require(len(set(units)) == len(set(textures)) == len(set(locations)) == 3, "Aliased units/textures/locations")
    metadata = document.get("samplerMetadata")
    require(isinstance(metadata, list) and len(metadata) == 3 and all(isinstance(s, dict) for s in metadata) and
            len({s.get("unit") for s in metadata}) == 3, "Incomplete sampler metadata")
    by_unit = {s["unit"]: s for s in metadata}
    for index in (9, 10, 11):
        s = samplers[f"colortex{index}"]; m = by_unit.get(s["unit"], {})
        require(m.get("textureId") == s["textureId"] and m.get("textureBaseLevel") == 0 and
                m.get("samplerObjectObserved") is True and m.get("effectiveFilteringObserved") is True and
                m.get("wholeTargetReadbackBytes") == 1600 * 900 * 16 and m.get("exportedTexelCount") == 16, "Sampler metadata mismatch")
    for coordinate in POINTS:
        normal, state, reflection = [maps[f"colortex{i}"][coordinate] for i in (9, 10, 11)]
        require(normal[3] in (0, 1) and 0 <= state[0] <= 1 and all(v in (0, 1) for v in state[1:]) and reflection[3] in (0, 1), "Invalid known/water/Fresnel flags")
        require(reflection[1] == float(reflection[0] > 0) and reflection[2] == float(reflection[0] < 0), "Invalid SSR sign flags")
        if state[2] == 1:
            require(abs(sum(v * v for v in normal[:3]) - 1) <= 1e-4, "Water optical normal not unit length")
    return maps


def audit_pair(control, facet, scene):
    """Return qualified selected-point optical changes; not visual acceptance."""
    if scene not in {"near", "deep", "tilt"}:
        raise ValueError("Unknown held-view scene")
    maps = [snapshot(control, "control", scene), snapshot(facet, "facet", scene)]
    rows, qualified, responsive = [], [], []
    for coordinate in sorted(POINTS):
        values = [[m[f"colortex{index}"][coordinate] for index in (9, 10, 11)] for m in maps]
        (normal_a, state_a, reflection_a), (normal_b, state_b, reflection_b) = values
        flags_a = [normal_a[3], *state_a[1:], reflection_a[3]]
        flags_b = [normal_b[3], *state_b[1:], reflection_b[3]]
        if flags_a != flags_b:
            raise ValueError("Selected known/water/underwater flags changed between packs")
        included = flags_a == [1, 1, 1, 1, 1]
        change = max(abs(normal_a[i] - normal_b[i]) for i in range(3))
        if included:
            qualified.append(coordinate)
            if change > .001:
                responsive.append(coordinate)
        rows.append({"x": coordinate[0], "y": coordinate[1], "region": "interior" if coordinate in INTERIOR else "edge",
                     "qualified": included, "exclusion": None if included else "not jointly known underwater water",
                     "normal_control": normal_a[:3], "normal_facet": normal_b[:3], "normal_max_abs_delta": change,
                     "fresnel_control": state_a[0], "fresnel_facet": state_b[0], "fresnel_delta": state_b[0] - state_a[0],
                     "reflection_only_toggle_F_ge_0_9999": (state_a[0] >= .9999) != (state_b[0] >= .9999),
                     "SSR_control": {"path": reflection_a[0], "hit": reflection_a[1], "miss": reflection_a[2]},
                     "SSR_facet": {"path": reflection_b[0], "hit": reflection_b[1], "miss": reflection_b[2]}})
    if (len(qualified) < 4 or (scene == "near" and
            (len(set(qualified) & INTERIOR) != 4 or len(set(qualified) & EDGE) < 4))):
        raise ValueError("Vacuous known-column coverage")
    if len(responsive) < 4 or len(set(responsive) & EDGE) < 1:
        raise ValueError("Insufficient nonvacuous optical-normal response")
    return {"accepted": True, "scope": "selected known-column optical-facet A/B response only", "scene": scene,
            "qualified_points": len(qualified), "qualified_interior": len(set(qualified) & INTERIOR),
            "qualified_edge": len(set(qualified) & EDGE), "responsive_points_above_0_001": len(responsive),
            "responsive_edge": len(set(responsive) & EDGE), "all_sixteen_flags_match": True,
            "reflection_only_counts_F_ge_0_9999": {"control": sum(row["qualified"] and row["fresnel_control"] >= .9999 for row in rows),
                                                   "facet": sum(row["qualified"] and row["fresnel_facet"] >= .9999 for row in rows)},
            "observer_clocks": {role: {"snapshot_frame": document["snapshotFrame"], "actual_frame_time_counter": document["frameTimeCounter"]}
                                for role, document in (("control", control), ("facet", facet))},
            "claims": {"natural_visual_acceptance": False, "true_TIR_measured": False,
                       "same_frame_PNG_proven": False, "native_C0_neutrality_proven": False,
                       "geometry_attribution_accepted": False, "FPS_floor_guaranteed": False, "shipping_fix_accepted": False},
            "points": rows}


def document(path):
    require(path.stat().st_size <= 1024 * 1024, "Oversized JSON evidence")
    value = json.loads(path.read_text())
    require(isinstance(value, dict), "Evidence is not a JSON object")
    return value


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def zip_contents(path, expected_sha):
    require(path.stat().st_size <= 64 * 1024 * 1024 and sha256(path) == expected_sha, "Wrong immutable ZIP SHA")
    with ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        require(len(names) <= 1024 and len(set(names)) == len(names) and
                sum(entry.file_size for entry in entries) <= 64 * 1024 * 1024, "Duplicate/oversized ZIP contents")
        return {name: archive.read(name) for name in names}  # ZipFile verifies each entry CRC.


def audit_archives(directory):
    shipping_sha = "16a7da88b7a5ba11d6aadfd56c717875fc61153b81cc859b4503da620c56c9d0"
    shipping = zip_contents(Path(__file__).resolve().parents[1] / "dist/Aqualumen-0.8.6.zip", shipping_sha)
    pair = {role: zip_contents(directory / name, sha) for role, (name, sha) in PACKS.items()}
    assignment = "            n=normalize(vec3(-wave.y,1.0,-wave.z));\n"
    replacement = "            n=rasterFacet;\n"
    strip = lambda data: re.sub(rb"/\* UNDERWATER_PROBE_BEGIN \*/\n.*?/\* UNDERWATER_PROBE_END \*/\n", b"", data, flags=re.S)
    for role, files in pair.items():
        metadata = json.loads(files["UNDERWATER-PROBE.json"])
        require(metadata.get("schema") == "aqualumen-underwater-probe-v1" and
                metadata.get("mode") == ("atlas" if role == "control" else "facet-atlas") and
                metadata.get("fixed_phase_seconds") == 120.0 and metadata.get("fixed_phase_scope") ==
                "common analytic frameTimeCounter only; not contact solver, bathymetry, weather or observer clock" and
                all(metadata.get(k) is False for k in ("shipping_fix", "natural_underwater_accepted", "GL_neutrality_verified", "pack_enforces_world_guard")), "Wrong diagnostic scope/phase")
        require(set(files) == set(shipping) | {"original/" + name for name in shipping} |
                {"UNDERWATER-PROBE.json", "UNDERWATER-PROBE.txt"}, "Changed original/source inventory")
        require(metadata.get("original_sha256") == {name: hashlib.sha256(data).hexdigest() for name, data in shipping.items()} and
                all(files["original/" + name] == data for name, data in shipping.items()), "Original shipping bytes/hash changed")
        changed = {name for name in shipping if files[name] != shipping[name]}
        require(changed == {"shaders/gbuffers_water.fsh", "shaders/final.fsh", "shaders/prepare.fsh",
                            "shaders/shaders.properties", "shaders/lib/uniforms.glsl"}, "Unexpected diagnostic source edit")
        water = strip(files["shaders/gbuffers_water.fsh"]).decode().replace("/* RENDERTARGETS:0,9,10,11 */", "/* DRAWBUFFERS:0 */")
        if role == "facet":
            require(water.count(replacement) == 1, "Facet assignment is not singular")
            water = water.replace(replacement, assignment)
        require(water.encode() == shipping["shaders/gbuffers_water.fsh"] and
                strip(files["shaders/final.fsh"]) == shipping["shaders/final.fsh"], "STORE/atlas stripping does not recover original main")
        uniforms = files["shaders/lib/uniforms.glsl"]
        phase = b"uniform float frameTimeCounter;\n/* UNDERWATER_PROBE_BEGIN */\n#define frameTimeCounter 120.0\n/* UNDERWATER_PROBE_END */\n"
        require(uniforms.count(phase) == 1 and uniforms.count(b"#define frameTimeCounter") == 1 and
                strip(uniforms) == shipping["shaders/lib/uniforms.glsl"], "Fixed phase changed uniform declaration or other source")
        for i in (9, 10, 11):
            require(f"const int colortex{i}Format = RGBA32F;".encode() in files["shaders/prepare.fsh"] and
                    f"const vec4 colortex{i}ClearColor = vec4(0.0,0.0,0.0,0.0);".encode() in files["shaders/prepare.fsh"] and
                    f"blend.gbuffers_water.colortex{i}=off".encode() in files["shaders/shaders.properties"], "Diagnostic target storage/blending mismatch")
    changed = [name for name in sorted(pair["control"]) if pair["control"][name] != pair["facet"][name]]
    require(changed == ["UNDERWATER-PROBE.json", "UNDERWATER-PROBE.txt", "shaders/gbuffers_water.fsh"] and
            pair["control"]["shaders/gbuffers_water.fsh"].count(assignment.encode()) == 1 and
            pair["control"]["shaders/gbuffers_water.fsh"].replace(assignment.encode(), replacement.encode()) == pair["facet"]["shaders/gbuffers_water.fsh"], "Pair has more than one shader assignment difference")
    return {"shipping_sha256": shipping_sha, "original_entries": len(shipping), "diagnostic_entries": len(pair["control"]),
            "paired_changed_entries": changed, "sole_shader_change": "known-column optical n = rasterFacet",
            "fixed_analytic_phase_seconds": 120.0, "VS_unchanged": True,
            "source_sha256": {role: {name: hashlib.sha256(files[name]).hexdigest() for name in
                                     ("shaders/gbuffers_water.vsh", "shaders/gbuffers_water.fsh", "shaders/final.fsh", "shaders/lib/uniforms.glsl")}
                              for role, files in pair.items()}}


def audit_capture(directory, role, scene, raw=None):
    """Existing PNG/head/metric public helpers, with this explicit 900p scope."""
    require(not (directory / "aborted.json").exists(), "Aborted capture")
    run, complete = document(directory / "run.json"), document(directory / "complete.json")
    scenario = "underwater-up-" + scene
    row = document(directory / (scenario + ".json"))
    name, sha = PACKS[role]
    common = {"world_id": WORLD_ID, "pack_name": name, "pack_sha256": sha, "shader_active": True,
              "shader_fallback": False, "resolution": SIZE, "framebuffer_resolution": SIZE,
              "player_dimension": "minecraft:overworld"}
    require(all(type(d.get(k)) is type(v) and d[k] == v for d in (run, row) for k, v in common.items()), "Wrong measured pack/world/target")
    config = {"schema": 2, "expected_pack_sha256": sha, "expected_resolution": SIZE, "world_generator": "minecraft:noise/overworld",
              "seed": 308060, "render_chunks": 12, "simulation_chunks": 6, "frame_limit": 120, "vsync": False,
              "warmup_seconds": 10.0, "sample_seconds": 5.0, "scenarios": [scenario], "terrain_fixture": "No terrain placement"}
    require(all(type(run.get(k)) is type(v) and run[k] == v for k, v in config.items()) and
            Path(run.get("world_directory", "")).name == "AqualumenNaturalV2", "Wrong approved TEST configuration")
    require(complete.get("status") == "complete" and complete.get("run_id") == run.get("run_id") == row.get("run_id") and
            isinstance(run.get("run_id"), str) and run["run_id"] and complete.get("scenarios") == [scenario] and
            complete.get("fixture_cleanup_complete") is True, "Incomplete or mismatched run")
    mods = {"aqualumen_benchmark": "0.3.9", "aqualumen_physics": "0.3.0", "iris": "1.8.8+mc1.21.1",
            "sodium": "0.6.9+mc1.21.1", "minecraft": "1.21.1", "java": "21"}
    require(all(run.get("mods", {}).get(k) == v for k, v in mods.items()) and
            run.get("gl_renderer") == "NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2", "Wrong runtime version/renderer")
    entries = [line.split("=", 1) for line in run.get("iris_configuration", "").splitlines() if line and not line.startswith("#") and "=" in line]
    require(len({entry[0] for entry in entries}) == len(entries), "Ambiguous recorded Iris selection")
    properties = dict(entries)
    require(properties.get("enableShaders") == "true" and properties.get("shaderPack") == name, "Wrong recorded Iris selection")
    storage = run.get("iris_render_target_storage", {})
    queries = storage.get("queries", [])
    require(storage.get("available") is True and storage.get("bindingRestored") is True and len(queries) == 6 and
            {q.get("index") for q in queries} == {0, 4, 5, 6, 7, 8}, "Missing actual Iris storage")
    ids = []
    for q in queries:
        index = q["index"]; dimensions = [1024, 512] if index in (6, 7) else SIZE
        fmt, declared = (34836, "RGBA32F") if index in (0, 4) else (34842, "RGBA16F")
        require([q.get("declaredWidth"), q.get("declaredHeight"), q.get("declaredFormat")] == [*dimensions, declared], "Wrong declared storage")
        for side in ("main", "alt"):
            s = q.get(side, {})
            require(type(s.get("textureId")) is int and s["textureId"] > 0 and
                    [s.get("width"), s.get("height"), s.get("actualFormat")] == [*dimensions, fmt], "Wrong actual storage")
            ids.append(s["textureId"])
    require(len(set(ids)) == 12, "Aliased main/alt storage")
    require(row.get("scenario") == scenario and row.get("workload") == "warmed-view" and row.get("warmup_seconds") == 10.0 and
            row.get("sample_seconds_requested") == 5.0 and row.get("contact_driver") == "none" and row.get("camera_lock") and
            all(row.get(k) is True for k in ("window_focused", "physics_active_seen", "camera_follows_local_player")), "Failed scene/camera/focus guard")
    report.validate_underwater_up(row, scenario)
    ns, ms = read_intervals(directory / (scenario + ".csv"))
    computed = report.metrics(ms)
    total = sum(ns)
    require(all(type(row.get(k)) in (int, float) and math.isfinite(row[k]) and
                math.isclose(row[k], v, rel_tol=1e-5, abs_tol=.001) for k, v in computed.items()) and
            type(row.get("frames")) is int and row["frames"] == len(ns) and
            type(row.get("frames_over_16_667_ms")) is int and row["frames_over_16_667_ms"] == sum(n * 60 > 1000000000 for n in ns) and
            math.isclose(computed["mean_fps"], 1e9 * len(ns) / total, rel_tol=1e-12) and
            math.isclose(row.get("recorded_seconds", -1), total / 1e9, abs_tol=1e-8) and
            row.get("sample_seconds_actual", 0) >= total / 1e9 >= 4.9, "Raw integer timing/metric mismatch")
    physics = json.loads(row.get("physics_status_json", "{}")); bathymetry = physics.get("bathymetry", {})
    require(physics.get("version") == "0.3.0-candidate" and physics.get("active") == 1 and physics.get("dimension") == 0 and
            bathymetry.get("ready") == 1 and bathymetry.get("known_columns") == 4096 and bathymetry.get("failed") is False, "Physics/map not ready")
    png = directory / (scenario + ".png")
    report.check_png(png, SIZE)
    try:
        from PIL import Image
    except ImportError:
        # No dependency installation: the existing CPU decoder is an alternate
        # full-image check after the bounded CRC/zlib/dimension public helper.
        decoded = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-hwaccel", "none", "-threads", "1",
                                  "-i", str(png), "-f", "null", "-"], capture_output=True, timeout=30)
        require(decoded.returncode == 0 and not decoded.stderr, "CPU full-image PNG decode failed")
        decoder = "ffmpeg CPU, hardware acceleration disabled"
    else:
        with Image.open(png) as image:
            image.load()
            require(list(image.size) == SIZE and image.mode in ("RGB", "RGBA"), "Wrong decoded PNG")
        decoder = "Pillow image.load"
    result = {"run_id": run["run_id"], "directory": directory.name, "completed_utc": complete["utc"],
              "raw_ns_count": len(ns), "raw_ns_sum": total, "metrics": computed,
              "PNG_full_CRC_and_full_image_decode": True, "PNG_decoder": decoder,
              "focused": True, "head_depth_m": row["underwater_up"]["actual_eye_depth"],
              "camera_position": row["actual_camera_position"], "camera_rotation": row["actual_camera_rotation"],
              "iris_storage_and_binding_restoration": True,
              "artifacts_sha256": {p.name: sha256(p) for p in (directory / "run.json", directory / "complete.json",
                                                             directory / (scenario + ".json"), directory / (scenario + ".csv"), png)}}
    if raw is not None:
        snapshot(raw, role, scene)
        require(math.dist(raw["unshiftedCameraPosition"], row["actual_camera_position"]) <= .05 and
                datetime.fromisoformat(raw["utc"].replace("Z", "+00:00")) > datetime.fromisoformat(complete["utc"].replace("Z", "+00:00")), "Raw observation is not the completed held view")
        result["raw_captured_after_measurement_complete"] = True
    return result


def audit_report(directory):
    archive = audit_archives(directory)
    scenes = []
    for scene in ("near", "deep", "tilt"):
        raw_paths = {role: directory / (f"{role}-{scene}-raw-first.json" if role == "control" and scene == "near" else f"{role}-{scene}-raw.json") for role in PACKS}
        raw = {role: document(path) for role, path in raw_paths.items()}
        captures = {role: audit_capture(directory / ("control-near-initial" if role == "control" and scene == "near" else f"{role}-{scene}"), role, scene, raw[role]) for role in PACKS}
        pair = audit_pair(raw["control"], raw["facet"], scene)
        require(captures["control"]["camera_position"] == captures["facet"]["camera_position"] and
                captures["control"]["camera_rotation"] == captures["facet"]["camera_rotation"] and
                raw["control"]["unshiftedCameraPosition"] == raw["facet"]["unshiftedCameraPosition"], "Paired camera pose differs")
        pair["captures"] = captures
        pair["raw_sha256"] = {role: sha256(path) for role, path in raw_paths.items()}
        scenes.append(pair)
    repeat = audit_capture(directory / "control-near", "control", "near")
    require(repeat["artifacts_sha256"]["underwater-up-near.png"] == scenes[0]["captures"]["control"]["artifacts_sha256"]["underwater-up-near.png"], "Retained near repeat PNG differs")
    return {"available": True, "audit_scope": "saved TEST-only known-column optical-facet A/B selected-point response",
            "world_id": WORLD_ID, "seed": 308060, "resolution": SIZE, "frame_limit": 120, "vsync": False,
            "warmup_seconds": 10, "sample_seconds": 5, "pack_sha256": {role: sha for role, (_, sha) in PACKS.items()},
            "archive_comparison": archive, "paired_scene_count": len(scenes), "selected_points_per_scene": 16,
            "scenes": scenes, "control_near_repeat": repeat,
            "control_near_raw_pairs_initial_run_not_later_repeat": True,
            "claims": scenes[0]["claims"],
            "limits": ["Analytic phase120 is common; observer clock, contact solver, bathymetry and weather are not frozen by that macro.",
                       "Raw observations follow completed measurements and match held camera; raw/PNG same frame is unproven.",
                       "Raw snapshots do not export yaw/pitch, submersion or world time; those are measured-scene context, not direct raw queries.",
                       "Selected texels and storage are observed, not all-fragment geometry or passive C0 neutrality.",
                       "Reflection-only classification uses F>=0.9999; this threshold alone is not true TIR.",
                       "Seven five-second warmed 900p views at cap120, not 1440p, temporal or floor acceptance.",
                       "This audit does not accept appearance or adopt the facet ablation as a shipping fix."]}


def synthetic_snapshot(role, scene="near", known=1.0):
    """Explicit MOCK external-boundary fixture; not captured GL data."""
    f32 = lambda x: struct.unpack("<f", struct.pack("<f", x))[0]
    camera = [448.5, 59.63899988555908 if scene == "deep" else 62.38899988555908, -383.5]
    state = {key: 0 for key in STATE_FIELDS}
    state.update(active=33984, binding=49, alignment=4)
    name, sha = PACKS[role]
    doc = {"fixture_kind": "synthetic_CPU_only", "available": True, "stateRestored": True,
           "scopeAuthorized": True, "timingAcceptanceExcluded": True, "selectedTexelsFiniteOnly": True,
           "visualQualityAccepted": False, "geometryAttributionAccepted": False, "runtimeIntegrationAccepted": False,
           "world": "AqualumenNaturalV2", "worldId": WORLD_ID, "seed": 308060, "dimension": "minecraft:overworld",
           "packName": name, "packSha256": sha, "observerVersion": "0.3.9", "tag": "DEBUG-shore-sampler",
           "program": 21, "expectedProgram": 21, "width": 1600, "height": 900,
           "renderer": "NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2", "snapshotFrame": 100,
           "frameTimeCounter": 53.4, "unshiftedCameraPosition": camera,
           "maximumSelectedTexels": 16, "stateBefore": state, "stateAfter": deepcopy(state),
           "seam": "FinalPassRenderer.renderFinalPass before FullScreenQuadRenderer.renderQuad; after Program.use and CustomUniforms.push",
           "texelCoordinateConvention": "integer level-zero texture coordinates; bottom-left origin",
           "samplingInterpretation": "unfiltered level-zero texels, not tone-mapped or reconstructed FINAL texture() values",
           "errorFlagPolicy": "untouched; adapter must not consume or clear GL error flags",
           "samplers": [], "samplerMetadata": []}
    n = [-.1, -math.sqrt(.99), 0] if role == "control" else [0, -1, 0]
    for offset, rgba in enumerate(([f32(x) for x in n] + [known], [.2 if role == "control" else .1, 1, 1, 1], [-1, 0, 1, 1])):
        unit, texture = 3 + offset, 71 + 2 * offset
        doc["samplers"].append({"name": f"colortex{9 + offset}", "active": True, "location": offset + 2,
                                "type": 35678, "size": 1, "unit": unit, "textureId": texture,
                                "textureExists": True, "actualFormat": 34836, "width": 1600, "height": 900,
                                "samples": [{"x": x, "y": y, "rgba": [f32(v) for v in rgba]} for x, y in sorted(POINTS)]})
        doc["samplerMetadata"].append({"unit": unit, "textureId": texture, "textureBaseLevel": 0,
                                       "samplerObjectObserved": True, "effectiveFilteringObserved": True,
                                       "wholeTargetReadbackBytes": 1600 * 900 * 16, "exportedTexelCount": 16})
    return doc


class FacetAuditTests(unittest.TestCase):
    def test_synthetic_vacuous_unknown_pair_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_pair(synthetic_snapshot("control", known=0.0), synthetic_snapshot("facet", known=0.0), "near")

    def test_synthetic_unchanged_optical_normals_are_not_a_nonvacuous_ablation(self):
        control, facet = synthetic_snapshot("control"), synthetic_snapshot("facet")
        facet["samplers"][0]["samples"] = deepcopy(control["samplers"][0]["samples"])
        with self.assertRaises(ValueError):
            audit_pair(control, facet, "near")

    def test_synthetic_wrong_identity_storage_or_nonfinite_readback_is_rejected(self):
        changes = [lambda d: d.update(packSha256="0" * 64),
                   lambda d: d.update(unshiftedCameraPosition=[448.5, 50, -383.5]),
                   lambda d: d["samplers"][0].update(actualFormat=34842),
                   lambda d: d["samplers"][0]["samples"][0]["rgba"].__setitem__(0, float("nan")),
                   lambda d: d["stateAfter"].update(binding=999)]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                facet = synthetic_snapshot("facet")
                change(facet)
                with self.assertRaises(ValueError):
                    audit_pair(synthetic_snapshot("control"), facet, "near")

    def test_synthetic_repeated_coordinates_or_aliased_bound_textures_are_rejected(self):
        for operation in ("repeat", "alias"):
            with self.subTest(operation=operation):
                facet = synthetic_snapshot("facet")
                if operation == "repeat":
                    facet["samplers"][0]["samples"][1] = deepcopy(facet["samplers"][0]["samples"][0])
                else:
                    facet["samplers"][1]["textureId"] = facet["samplers"][0]["textureId"]
                with self.assertRaises(ValueError):
                    audit_pair(synthetic_snapshot("control"), facet, "near")

    def test_synthetic_all_ssr_misses_are_an_acceptable_optical_ablation_outcome(self):
        control, facet = synthetic_snapshot("control"), synthetic_snapshot("facet")
        facet["frameTimeCounter"] = 500.0
        result = audit_pair(control, facet, "near")
        self.assertTrue(result["accepted"])
        self.assertEqual(result["qualified_interior"], 4)
        self.assertEqual(result["responsive_points_above_0_001"], 16)
        self.assertTrue(all(row["SSR_control"]["miss"] == row["SSR_facet"]["miss"] == 1 for row in result["points"]))
        self.assertFalse(result["claims"]["shipping_fix_accepted"])
        self.assertEqual(result["observer_clocks"]["facet"]["actual_frame_time_counter"], 500.0)

    def test_synthetic_near_needs_all_four_interior_and_some_edge_response(self):
        for operation in ("unknown_interior", "unresponsive_edges", "flag_mismatch"):
            with self.subTest(operation=operation):
                control, facet = synthetic_snapshot("control"), synthetic_snapshot("facet")
                if operation == "unknown_interior":
                    for doc in (control, facet):
                        for sample in doc["samplers"][0]["samples"]:
                            if (sample["x"], sample["y"]) == (801, 451):
                                sample["rgba"][3] = 0.0
                elif operation == "unresponsive_edges":
                    for a, b in zip(control["samplers"][0]["samples"], facet["samplers"][0]["samples"]):
                        if (a["x"], a["y"]) in EDGE:
                            b["rgba"] = a["rgba"][:]
                else:
                    facet["samplers"][0]["samples"][0]["rgba"][3] = 0.0
                with self.assertRaises(ValueError):
                    audit_pair(control, facet, "near")

    def test_synthetic_reflection_only_threshold_does_not_claim_true_tir(self):
        control, facet = synthetic_snapshot("control"), synthetic_snapshot("facet")
        facet["samplers"][1]["samples"][0]["rgba"][0] = struct.unpack("<f", struct.pack("<f", .99995))[0]
        result = audit_pair(control, facet, "near")
        self.assertEqual(result["reflection_only_counts_F_ge_0_9999"], {"control": 0, "facet": 1})
        self.assertTrue(result["points"][0]["reflection_only_toggle_F_ge_0_9999"])
        self.assertFalse(result["claims"]["true_TIR_measured"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--report-dir", type=Path)
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FacetAuditTests))
        return 0 if result.wasSuccessful() else 1
    if args.report_dir is None:
        parser.error("Choose --self-test or --report-dir")
    try:
        print(json.dumps(audit_report(args.report_dir), indent=2, sort_keys=True, allow_nan=False))
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(json.dumps({"available": False, "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
