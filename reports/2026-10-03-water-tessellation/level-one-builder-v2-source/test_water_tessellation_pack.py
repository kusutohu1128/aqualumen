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
            for index, level in enumerate((0, 2, 4, -1, True, 1.0, "1", None)):
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
                    ("--level", "2"), ("--level", "4"), ("--level", "1.0"),
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


if __name__ == "__main__":
    unittest.main()
