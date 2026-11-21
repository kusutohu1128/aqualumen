"""CPU ZIP contracts only; no GL, Iris execution or optical-neutrality proof."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from underwater_probe_pack import build_pack as build_atlas


FIELDS = {
    "uv": "vec2", "lightmap": "vec2", "vertexColor": "vec4",
    "worldNormal": "vec3", "worldPosition": "vec3",
    "waterMeanSurfaceY": "float", "waterUnknownWeight": "float",
    "materialId": "float",
}


def strip_tess_blocks(source):
    return re.sub(r"/\* WATER_TESSELLATION_PROBE_BEGIN \*/.*?"
                  r"/\* WATER_TESSELLATION_PROBE_END \*/\n", "", source, flags=re.S)


class WaterTessellationPackTest(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]

    def test_public_cli_builds_level_one_stage_probe_without_changing_original_optics(self):
        source_files = sorted(p for p in (self.root / "shaders").rglob("*") if p.is_file())
        before = {p: p.read_bytes() for p in source_files}
        script = self.root / "tools/water_tessellation_pack.py"
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            parent = build_atlas(self.root, directory / "atlas.zip", "atlas", fixed_phase=120.0)
            target = directory / "stage.zip"
            result = subprocess.run([sys.executable, "-B", str(script), str(target),
                                     "--level", "1", "--fixed-phase", "120.0"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with ZipFile(parent) as atlas, ZipFile(target) as stage:
                vertex = stage.read("shaders/gbuffers_water.vsh").decode()
                for field in FIELDS:
                    vertex = re.sub(rf"\btessVertex_{field}\b", field, vertex)
                self.assertEqual(vertex, atlas.read("shaders/gbuffers_water.vsh").decode())
                tcs = stage.read("shaders/gbuffers_water.tcs").decode()
                tes = stage.read("shaders/gbuffers_water.tes").decode()
                self.assertTrue(tcs.startswith("#version 400 compatibility\n"))
                self.assertTrue(tes.startswith("#version 400 compatibility\n"))
                self.assertIn("layout(vertices=3) out;", tcs)
                self.assertIn("layout(triangles, equal_spacing, ccw) in;", tes)
                self.assertIn("gl_out[gl_InvocationID].gl_Position=gl_in[gl_InvocationID].gl_Position;", tcs)
                for index in range(3):
                    self.assertIn(f"gl_TessLevelOuter[{index}]=1.0;", tcs)
                self.assertIn("gl_TessLevelInner[0]=1.0;", tcs)
                self.assertIn("gl_Position=gl_TessCoord.x*gl_in[0].gl_Position"
                              "+gl_TessCoord.y*gl_in[1].gl_Position"
                              "+gl_TessCoord.z*gl_in[2].gl_Position;", tes)
                for field, kind in FIELDS.items():
                    self.assertIn(f"in {kind} tessVertex_{field}[];", tcs)
                    self.assertIn(f"out {kind} tessControl_{field}[];", tcs)
                    self.assertIn(f"tessControl_{field}[gl_InvocationID]=tessVertex_{field}[gl_InvocationID];", tcs)
                    self.assertIn(f"in {kind} tessControl_{field}[];", tes)
                    self.assertIn(f"{'flat ' if field == 'materialId' else ''}out {kind} {field};", tes)
                    if field != "materialId":
                        self.assertIn(f"{field}=gl_TessCoord.x*tessControl_{field}[0]"
                                      f"+gl_TessCoord.y*tessControl_{field}[1]"
                                      f"+gl_TessCoord.z*tessControl_{field}[2];", tes)
                self.assertIn("materialId=tessControl_materialId[2];", tes)
                self.assertIn("gl_TessCoord", tes)
                for source in (tcs, tes):
                    self.assertNotIn("localWaveState(", source)
                    self.assertNotIn("localWaterColumn(", source)
                water = stage.read("shaders/gbuffers_water.fsh").decode()
                self.assertIn("/* RENDERTARGETS:0,9,10,11,12 */", water)
                self.assertIn("tessStageCoord", water)
                self.assertIn("gl_FragData[4]=vec4(0.0);", water.split("        return;", 1)[0])
                restored_water = strip_tess_blocks(water).replace(
                    "/* RENDERTARGETS:0,9,10,11,12 */", "/* RENDERTARGETS:0,9,10,11 */")
                self.assertEqual(restored_water, atlas.read("shaders/gbuffers_water.fsh").decode())
                final = stage.read("shaders/final.fsh").decode()
                for index in (9, 10, 11, 12):
                    self.assertIn(f"uniform sampler2D colortex{index};", final)
                    self.assertIn(f"texelFetch(colortex{index},p,0)", final)
                stage_panel = "    else if (y==1) panel=probeStage.a>=0.5?(probeNormal.a>=0.5?probeNormal.xyz*0.5+0.5:vec3(1.0,0.0,1.0)):vec3(1.0,1.0,0.0);\n"
                atlas_panel = "    else if (y==1) panel=probeNormal.a>=0.5?probeNormal.xyz*0.5+0.5:vec3(1.0,0.0,1.0);\n"
                self.assertIn(stage_panel, final)
                self.assertEqual(strip_tess_blocks(final).replace(stage_panel, atlas_panel),
                                 atlas.read("shaders/final.fsh").decode())
                prepare = stage.read("shaders/prepare.fsh").decode()
                self.assertIn("const int colortex12Format = RGBA32F;", prepare)
                self.assertIn("const bool colortex12Clear = true;", prepare)
                self.assertIn("const vec4 colortex12ClearColor = vec4(0.0,0.0,0.0,0.0);", prepare)
                self.assertIn("const int colortex12Format = RGBA32F;",
                              "\n".join(re.findall(r"/\*.*?\*/", prepare, flags=re.S)))
                properties = stage.read("shaders/shaders.properties").decode()
                self.assertIn("iris.features.required=CUSTOM_IMAGES COMPUTE_SHADERS TESSELLATION_SHADERS\n", properties)
                self.assertIn("blend.gbuffers_water.colortex12=off", properties)
                for name in atlas.namelist():
                    if name.startswith("original/"):
                        self.assertEqual(stage.read(name), atlas.read(name), name)
                changed_names = {"shaders/gbuffers_water.vsh", "shaders/gbuffers_water.fsh",
                                 "shaders/final.fsh", "shaders/prepare.fsh", "shaders/shaders.properties"}
                for name in atlas.namelist():
                    if name.startswith("shaders/") and name not in changed_names:
                        self.assertEqual(stage.read(name), atlas.read(name), name)
                metadata = json.loads(stage.read("WATER-TESSELLATION-PROBE.json"))
                self.assertEqual(metadata["level"], 1)
                self.assertEqual(metadata["fixed_phase_seconds"], 120.0)
                for key in ("shipping_fix", "GL_neutrality_verified", "runtime_accepted",
                            "natural_underwater_accepted", "pack_enforces_world_guard"):
                    self.assertFalse(metadata[key])
                self.assertEqual(metadata["targets"]["12"], "gl_TessCoord.xyz / TES stage-present=1; nonwater zero")
                for path in source_files:
                    name = path.relative_to(self.root).as_posix()
                    self.assertEqual(stage.read("original/" + name), before[path])
                    self.assertEqual(metadata["original_sha256"][name], hashlib.sha256(before[path]).hexdigest())
                self.assertIn("TEST ONLY", stage.read("WATER-TESSELLATION-PROBE.txt").decode())
                self.assertIn("missing TES", stage.read("WATER-TESSELLATION-PROBE.txt").decode())
            self.assertEqual(before, {p: p.read_bytes() for p in source_files})

    def test_stage_present_flag_is_produced_by_tes_not_fabricated_in_the_fragment(self):
        from water_tessellation_pack import build_pack
        with tempfile.TemporaryDirectory() as temporary:
            target = build_pack(self.root, Path(temporary) / "stage-origin.zip")
            with ZipFile(target) as stage:
                tes = stage.read("shaders/gbuffers_water.tes").decode()
                water = stage.read("shaders/gbuffers_water.fsh").decode()
                self.assertIn("out vec4 tessStageCoord;", tes)
                self.assertIn("tessStageCoord=vec4(gl_TessCoord,1.0);", tes)
                self.assertIn("in vec4 tessStageCoord;", water)
                self.assertIn("gl_FragData[4]=tessStageCoord;", water)
                self.assertNotIn("gl_FragData[4]=vec4(tessStageCoord,1.0);", water)

    def test_flat_material_qualification_matches_through_all_linked_stage_interfaces(self):
        from water_tessellation_pack import build_pack
        with tempfile.TemporaryDirectory() as temporary:
            target = build_pack(self.root, Path(temporary) / "flat-interface.zip")
            with ZipFile(target) as stage:
                interfaces = {
                    "shaders/gbuffers_water.vsh": ("flat out float tessVertex_materialId;",),
                    "shaders/gbuffers_water.tcs": (
                        "flat in float tessVertex_materialId[];",
                        "flat out float tessControl_materialId[];"),
                    "shaders/gbuffers_water.tes": (
                        "flat in float tessControl_materialId[];",
                        "flat out float materialId;"),
                    "shaders/gbuffers_water.fsh": ("flat in float materialId;",),
                }
                for name, declarations in interfaces.items():
                    lines = stage.read(name).decode().splitlines()
                    for declaration in declarations:
                        with self.subTest(stage=name, declaration=declaration):
                            self.assertIn(declaration, lines)

    def test_api_and_cli_reject_unapproved_levels_and_invalid_phases_without_destination_writes(self):
        from water_tessellation_pack import build_pack
        script = self.root / "tools/water_tessellation_pack.py"
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for index, level in enumerate((0, 3, 8, -1, True, 1.0, "1", None)):
                target = directory / f"level-{index}" / "never.zip"
                with self.subTest(level=repr(level)), self.assertRaises(ValueError):
                    build_pack(self.root, target, level=level)
                self.assertFalse(target.parent.exists())
            for index, phase in enumerate((float("nan"), float("inf"), -float("inf"),
                                            -1.0, 12000.1, True, "120.0", None, 10**1000)):
                target = directory / f"phase-{index}" / "never.zip"
                with self.subTest(phase_index=index), self.assertRaises(ValueError):
                    build_pack(self.root, target, fixed_phase=phase)
                self.assertFalse(target.parent.exists())
            for index, arguments in enumerate((
                    ("--level", "3"), ("--level", "8"), ("--level", "1.0"),
                    ("--fixed-phase", "nan"), ("--fixed-phase", "inf"),
                    ("--fixed-phase", "-1"), ("--fixed-phase", "12000.1"))):
                target = directory / f"cli-{index}" / "never.zip"
                result = subprocess.run([sys.executable, "-B", str(script), str(target), *arguments],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(target.parent.exists())

    def test_never_overwrites_an_archive_or_symlink_and_rejects_resolved_shipping_trees(self):
        from water_tessellation_pack import build_pack
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            target = build_pack(self.root, directory / "reserved.zip")
            original = target.read_bytes()
            with self.assertRaises(FileExistsError):
                build_pack(self.root, target)
            self.assertEqual(target.read_bytes(), original)
            link = directory / "reserved-link.zip"
            missing = directory / "missing.zip"
            link.symlink_to(missing)
            with self.assertRaises(FileExistsError):
                build_pack(self.root, link)
            self.assertFalse(missing.exists())
            source = directory / "source"
            source.mkdir()
            (source / "shaders").mkdir()
            dist = directory / "shipping-dist"
            dist.mkdir()
            (source / "dist").symlink_to(dist, target_is_directory=True)
            alias = directory / "alias"
            alias.symlink_to(source / "shaders", target_is_directory=True)
            for folder in (source / "shaders", source / "dist", alias):
                target = folder / "never.zip"
                with self.assertRaises(ValueError):
                    build_pack(source, target)
                self.assertFalse(target.exists())

    def test_same_inputs_produce_identical_archives_and_only_phase_include_changes_at_bounds(self):
        from water_tessellation_pack import build_pack
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            first = build_pack(self.root, directory / "first.zip")
            second = build_pack(self.root, directory / "second.zip")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with ZipFile(first) as archive:
                self.assertEqual(archive.namelist(), sorted(archive.namelist()))
                self.assertTrue(all(entry.date_time == (2026, 10, 3, 0, 0, 0) for entry in archive.infolist()))
            for phase in (0.0, 12000.0):
                target = build_pack(self.root, directory / f"phase-{phase}.zip", fixed_phase=phase)
                with ZipFile(first) as control, ZipFile(target) as changed:
                    self.assertEqual(json.loads(changed.read("WATER-TESSELLATION-PROBE.json"))["fixed_phase_seconds"], phase)
                    for name in control.namelist():
                        if name.startswith(("shaders/", "original/")) and name != "shaders/lib/uniforms.glsl":
                            self.assertEqual(control.read(name), changed.read(name), name)
                    uniforms = changed.read("shaders/lib/uniforms.glsl").decode()
                    self.assertIn(f"#define frameTimeCounter {phase!r}\n", uniforms)
                    restored = re.sub(r"/\* UNDERWATER_PROBE_BEGIN \*/.*?/\* UNDERWATER_PROBE_END \*/\n", "", uniforms, flags=re.S)
                    self.assertEqual(restored, (self.root / "shaders/lib/uniforms.glsl").read_text())

    def test_public_fixed_two_and_four_geometry_packs_preserve_level_one_and_original_optics(self):
        from water_tessellation_pack import build_pack
        script = self.root / "tools/water_tessellation_pack.py"
        source_files = sorted(p for p in (self.root / "shaders").rglob("*") if p.is_file())
        before = {p: p.read_bytes() for p in source_files}
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            level_one = build_pack(self.root, directory / "one.zip")
            self.assertEqual(hashlib.sha256(level_one.read_bytes()).hexdigest(),
                             "6bb9480cc3b5130558dffc8baccf184c5bb6e99949faf3a60057001d58237746")
            for level in (2, 4):
                target = build_pack(self.root, directory / f"density-{level}.zip", level=level)
                cli_target = directory / f"density-cli-{level}.zip"
                result = subprocess.run([sys.executable, "-B", str(script), str(cli_target),
                                         "--level", str(level), "--fixed-phase", "120.0"],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(target.read_bytes(), cli_target.read_bytes())
                with ZipFile(level_one) as one, ZipFile(target) as density:
                    vertex = density.read("shaders/gbuffers_water.vsh").decode()
                    self.assertIn("out float tessVertex_waterVertexAdmitted;", vertex)
                    self.assertIn("tessVertex_waterVertexAdmitted=0.0;", vertex)
                    admission = "        if (tessVertex_worldNormal.y>0.5 || (known && fract(absolutePosition.y)>0.01)) {\n"
                    self.assertIn(admission + "/* WATER_TESSELLATION_PROBE_BEGIN */\n"
                                  "            tessVertex_waterVertexAdmitted=1.0;\n", vertex)
                    self.assertEqual(strip_tess_blocks(vertex), one.read("shaders/gbuffers_water.vsh").decode())
                    tcs = density.read("shaders/gbuffers_water.tcs").decode()
                    self.assertIn("in float tessVertex_waterVertexAdmitted[];", tcs)
                    self.assertIn("out float tessControl_waterVertexAdmitted[];", tcs)
                    self.assertIn("tessControl_waterVertexAdmitted[gl_InvocationID]=tessVertex_waterVertexAdmitted[gl_InvocationID];", tcs)
                    self.assertIn("float tessDensity=(tessVertex_materialId[0]==10000.0"
                                  " && tessVertex_materialId[1]==10000.0"
                                  f" && tessVertex_materialId[2]==10000.0)?{level}.0:1.0;", tcs)
                    level_branch = tcs.split("    if (gl_InvocationID==0) {", 1)[1]
                    self.assertNotIn("waterVertexAdmitted", level_branch)
                    self.assertNotIn("waterUnknownWeight", level_branch)
                    for index in range(3):
                        self.assertIn(f"gl_TessLevelOuter[{index}]=tessDensity;", level_branch)
                    self.assertIn("gl_TessLevelInner[0]=tessDensity;", level_branch)
                    tes = density.read("shaders/gbuffers_water.tes").decode()
                    for library in ("settings", "uniforms", "bathymetry", "waves", "ripples"):
                        self.assertIn(f'#include "/lib/{library}.glsl"', tes)
                    self.assertIn("in float tessControl_waterVertexAdmitted[];", tes)
                    self.assertNotIn("fract(", tes, "Generated mean height must not reclassify original bottom admission")
                    self.assertIn("if (gl_TessCoord[i]>0.0)", tes)
                    self.assertIn("admitted=admitted && tessControl_waterVertexAdmitted[i]==1.0;", tes)
                    self.assertIn("cornerKnown=cornerKnown && tessControl_waterUnknownWeight[i]==0.0;", tes)
                    self.assertIn("bool generatedKnown=localWaterColumn(meanPosition.xz,meanPosition.y,column);", tes)
                    self.assertIn("bool known=cornerKnown && generatedKnown;", tes)
                    self.assertIn("waterUnknownWeight=known?0.0:1.0;", tes)
                    self.assertIn("if (!admitted) {waterUnknownWeight=1.0;return;}", tes)
                    self.assertIn("abs(meanPosition.y-aqualumenGrid.w)<0.30", tes)
                    self.assertIn("clamp(rippleState(absolutePosition.xz).x,-0.07,0.07)", tes)
                    self.assertIn("localWaveState(absolutePosition.xz,frameTimeCounter,0.0,column,0.0,variance).x", tes)
                    self.assertIn("waveState(absolutePosition.xz,frameTimeCounter,0.0).x", tes)
                    self.assertIn("gl_Position=gbufferProjection*gbufferModelView*vec4(worldPosition,1.0);", tes)
                    self.assertIn("gl_Position=gl_in[corner].gl_Position;", tes)
                    for field in FIELDS:
                        if field != "materialId":
                            self.assertIn(f"{field}=tessControl_{field}[corner];", tes)
                    self.assertIn("if (gl_TessCoord.x==0.0) {a=1;b=2;}", tes)
                    self.assertIn("else if (gl_TessCoord.y==0.0) {a=0;b=2;}", tes)
                    self.assertIn("else if (gl_TessCoord.z==0.0) {a=0;b=1;}", tes)
                    self.assertIn("if (densityEndpointBefore(densityMeanVertex(b),densityMeanVertex(a)))", tes)
                    self.assertIn("float t=gl_TessCoord[b];", tes)
                    self.assertIn("meanPosition=meanA+t*(meanB-meanA);", tes)
                    self.assertIn("gl_Position=gl_in[a].gl_Position+t*(gl_in[b].gl_Position-gl_in[a].gl_Position);", tes)
                    self.assertIn("worldPosition=tessControl_worldPosition[a]+t*(tessControl_worldPosition[b]-tessControl_worldPosition[a]);", tes)
                    self.assertIn("tessStageCoord=vec4(gl_TessCoord,1.0);", tes)
                    for name in one.namelist():
                        if name.startswith("original/"):
                            self.assertEqual(density.read(name), one.read(name), name)
                        if name.startswith("shaders/") and name not in {
                                "shaders/gbuffers_water.vsh", "shaders/gbuffers_water.tcs", "shaders/gbuffers_water.tes"}:
                            self.assertEqual(density.read(name), one.read(name), name)
                    metadata = json.loads(density.read("WATER-TESSELLATION-PROBE.json"))
                    self.assertEqual(metadata["mode"], "fixed-density-atlas")
                    self.assertEqual(metadata["level"], level)
                    self.assertEqual(metadata["density_policy"], "fixed factor for three constant water material IDs; nonwater factor one; independent of admission and knowledge")
                    for key in ("shipping_fix", "GL_neutrality_verified", "runtime_accepted",
                                "natural_underwater_accepted", "generated_geometry_gpu_qualified"):
                        self.assertFalse(metadata[key])
                    legend = density.read("WATER-TESSELLATION-PROBE.txt").decode()
                    self.assertIn("TEST ONLY", legend)
                    self.assertIn("side/top", legend)
                    self.assertIn("FS optics", legend)
            self.assertEqual(before, {p: p.read_bytes() for p in source_files})


if __name__ == "__main__":
    unittest.main()
