"""CPU packaging contracts, not GL neutrality or natural-water acceptance."""
import hashlib
import json
from pathlib import Path
import re
import tempfile
import subprocess
import sys
import unittest
from zipfile import ZipFile

from underwater_probe_pack import build_pack


class UnderwaterProbePackTest(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]

    def test_baseline_observes_the_original_invocation_without_source_mutation(self):
        paths = sorted(p for p in (self.root / "shaders").rglob("*") if p.is_file())
        before = {p: hashlib.sha256(p.read_bytes()).digest() for p in paths}
        original = (self.root / "shaders/gbuffers_water.fsh").read_text()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "baseline.zip"
            self.assertEqual(build_pack(self.root, target, "baseline"), target)
            with ZipFile(target) as archive:
                observed = archive.read("shaders/gbuffers_water.fsh").decode()
                self.assertTrue("/* RENDERTARGETS:0,9,10,11 */" in observed,
                                "baseline ZIP lacks same-invocation diagnostic MRT outputs")
                self.assertIn("vec4(n,localColumnKnown?1.0:0.0)", observed)
                self.assertIn("vec4(fresnel,underwater?1.0:0.0,1.0,1.0)", observed)
                self.assertIn("vec4(reflectedHit.a,", observed)
                recovered = re.sub(r"/\* UNDERWATER_PROBE_BEGIN \*/.*?/\* UNDERWATER_PROBE_END \*/\n", "", observed, flags=re.S)
                recovered = recovered.replace("/* RENDERTARGETS:0,9,10,11 */", "/* DRAWBUFFERS:0 */")
                self.assertEqual(recovered, original)
                self.assertEqual(archive.read("shaders/final.fsh"), (self.root / "shaders/final.fsh").read_bytes())
            self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).digest() for p in paths})

    def test_observation_targets_preserve_signed_normals_and_zero_known_flags(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = build_pack(self.root, Path(temporary) / "baseline.zip", "baseline")
            with ZipFile(target) as archive:
                prepare = archive.read("shaders/prepare.fsh").decode()
                properties = archive.read("shaders/shaders.properties").decode()
                water = archive.read("shaders/gbuffers_water.fsh").decode()
                for index in (9, 10, 11):
                    self.assertTrue(f"const int colortex{index}Format = RGBA32F;" in prepare,
                                    "diagnostic target must use signed 32F storage")
                    self.assertIn(f"const bool colortex{index}Clear = true;", prepare)
                    self.assertIn(f"blend.gbuffers_water.colortex{index}=off", properties)
                    comment_text = "\n".join(re.findall(r"/\*.*?\*/", prepare, flags=re.S))
                    self.assertTrue(f"const int colortex{index}Format = RGBA32F;" in comment_text,
                                    "Iris format annotations must not become executable GLSL")
                before_return = water.split("        return;", 1)[0]
                for index in (1, 2, 3):
                    self.assertIn(f"gl_FragData[{index}]=vec4(0.0);", before_return)
                self.assertFalse(re.search(r"gl_FragData\[(?![0-3]\])", water))

    def test_clear_colour_annotations_use_four_explicit_scalars_for_iris(self):
        # Actual Iris 1.8.8 runtime RED at 21:49:06: "expected 4 arguments
        # to a vec4 constructor, got 1", followed by ArrayIndexOutOfBounds.
        # This is a public ZIP compatibility contract, not a parser replay or
        # proof of successful Iris execution. Native GLSL accepts vec4(0.0).
        with tempfile.TemporaryDirectory() as temporary:
            for mode in ("baseline", "atlas", "facet", "reasons"):
                target = build_pack(self.root, Path(temporary) / (mode + ".zip"), mode)
                with ZipFile(target) as archive:
                    prepare = archive.read("shaders/prepare.fsh").decode()
                    for index in (9, 10, 11):
                        match = re.search(
                            rf"const vec4 colortex{index}ClearColor\s*=\s*vec4\(([^()]*)\);",
                            prepare)
                        self.assertIsNotNone(match, "clear colour annotation must be present")
                        arguments = [part.strip() for part in match.group(1).split(",")]
                        self.assertEqual(len(arguments), 4,
                                         "Iris's annotation parser requires four scalar arguments")
                        self.assertEqual(arguments, ["0.0"] * 4)

    def test_atlas_displays_same_invocation_values_without_changing_water_main(self):
        with tempfile.TemporaryDirectory() as temporary:
            baseline = build_pack(self.root, Path(temporary) / "baseline.zip", "baseline")
            atlas = build_pack(self.root, Path(temporary) / "atlas.zip", "atlas")
            with ZipFile(baseline) as base, ZipFile(atlas) as diagnostic:
                self.assertEqual(base.read("shaders/gbuffers_water.fsh"), diagnostic.read("shaders/gbuffers_water.fsh"))
                final = diagnostic.read("shaders/final.fsh").decode()
                self.assertIn("fract(texcoord*vec2(2.0))", final)
                for index in (9, 10, 11):
                    self.assertIn(f"texelFetch(colortex{index},p,0)", final)
                recovered = re.sub(r"/\* UNDERWATER_PROBE_BEGIN \*/.*?/\* UNDERWATER_PROBE_END \*/\n", "", final, flags=re.S)
                self.assertEqual(recovered, (self.root / "shaders/final.fsh").read_text())

    def test_reasons_exports_original_query_before_the_guard_without_source_mutation(self):
        paths = sorted(p for p in (self.root / "shaders").rglob("*") if p.is_file())
        before = {p: hashlib.sha256(p.read_bytes()).digest() for p in paths}
        original = (self.root / "shaders/gbuffers_water.fsh").read_text()
        with tempfile.TemporaryDirectory() as temporary:
            target = build_pack(self.root, Path(temporary) / "reasons.zip", "reasons")
            with ZipFile(target) as archive:
                observed = archive.read("shaders/gbuffers_water.fsh").decode()
                self.assertIn("bool probeRawColumnKnown=localColumnKnown;", observed)
                self.assertIn("vec4(worldNormal.y,waterUnknownWeight,probeRawColumnKnown?1.0:0.0,localColumnKnown?1.0:0.0)", observed)
                self.assertLess(observed.index("bool probeRawColumnKnown=localColumnKnown;"),
                                observed.index("localColumnKnown=localColumnKnown && waterUnknownWeight==0.0;"))
                recovered = re.sub(r"/\* UNDERWATER_PROBE_BEGIN \*/.*?/\* UNDERWATER_PROBE_END \*/\n", "", observed, flags=re.S)
                recovered = recovered.replace("/* RENDERTARGETS:0,9,10,11 */", "/* DRAWBUFFERS:0 */")
                self.assertEqual(recovered, original)
                self.assertEqual(archive.read("shaders/gbuffers_water.vsh"), (self.root / "shaders/gbuffers_water.vsh").read_bytes())
                for function in ("localWaterColumn(", "reflectionTrace(", "refractionTrace("):
                    self.assertEqual(observed.count(function), original.count(function))
                self.assertIn("vec4(fresnel,underwater?1.0:0.0,1.0,1.0)", observed)
                self.assertIn("vec4(reflectedHit.a,", observed)
                final = archive.read("shaders/final.fsh").decode()
                self.assertIn("vec3(probeNormal.x*0.5+0.5,probeNormal.y,probeNormal.z)", final)
                for index in (9, 10, 11):
                    self.assertIn(f"texelFetch(colortex{index},p,0)", final)
                restored_final = re.sub(r"/\* UNDERWATER_PROBE_BEGIN \*/.*?/\* UNDERWATER_PROBE_END \*/\n", "", final, flags=re.S)
                self.assertEqual(restored_final, (self.root / "shaders/final.fsh").read_text())
                metadata = json.loads(archive.read("UNDERWATER-PROBE.json"))
                self.assertEqual(metadata["targets"]["9"], "worldNormal.y / waterUnknownWeight / rawColumnKnown / finalColumnKnown")
                self.assertFalse(metadata["shipping_fix"])
                self.assertFalse(metadata["GL_neutrality_verified"])
                self.assertEqual(archive.read("original/shaders/gbuffers_water.fsh").decode(), original)
                self.assertEqual(metadata["original_sha256"]["shaders/gbuffers_water.fsh"], hashlib.sha256(original.encode()).hexdigest())
                legend = archive.read("UNDERWATER-PROBE.txt").decode()
                self.assertIn("mode=reasons", legend)
                self.assertIn("alpha=final localColumnKnown", legend)
                self.assertIn("raw column query", legend)
                self.assertNotIn("C9: actual final optical n.xyz", legend)
            self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).digest() for p in paths})

    def test_facet_is_one_known_column_normal_difference_not_a_geometry_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            baseline = build_pack(self.root, Path(temporary) / "baseline.zip", "baseline")
            facet = build_pack(self.root, Path(temporary) / "facet.zip", "facet")
            with ZipFile(baseline) as base, ZipFile(facet) as diagnostic:
                original = base.read("shaders/gbuffers_water.fsh").decode()
                changed = diagnostic.read("shaders/gbuffers_water.fsh").decode()
                assignment = "            n=normalize(vec3(-wave.y,1.0,-wave.z));\n"
                self.assertEqual(original.count(assignment), 1)
                self.assertEqual(changed, original.replace(assignment, "            n=rasterFacet;\n", 1))
                self.assertEqual(diagnostic.read("shaders/gbuffers_water.vsh"), (self.root / "shaders/gbuffers_water.vsh").read_bytes())
                self.assertEqual(base.read("shaders/final.fsh"), diagnostic.read("shaders/final.fsh"))
                for function in ("reflectionTrace(", "refractionTrace("):
                    self.assertEqual(changed.count(function), original.count(function))

    def test_public_facet_atlas_is_one_assignment_ablation_with_identical_atlas_display(self):
        script = self.root / "tools/underwater_probe_pack.py"
        with tempfile.TemporaryDirectory() as temporary:
            atlas = build_pack(self.root, Path(temporary) / "atlas.zip", "atlas")
            target = Path(temporary) / "facet-atlas.zip"
            result = subprocess.run([sys.executable, "-B", str(script), str(target), "--mode", "facet-atlas"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with ZipFile(atlas) as control, ZipFile(target) as facet:
                assignment = "            n=normalize(vec3(-wave.y,1.0,-wave.z));\n"
                original = control.read("shaders/gbuffers_water.fsh").decode()
                self.assertEqual(original.count(assignment), 1)
                self.assertEqual(facet.read("shaders/gbuffers_water.fsh").decode(),
                                 original.replace(assignment, "            n=rasterFacet;\n", 1))
                shader_names = [name for name in control.namelist() if name.startswith("shaders/")]
                for name in shader_names:
                    if name != "shaders/gbuffers_water.fsh":
                        self.assertEqual(control.read(name), facet.read(name), name)
                for name in control.namelist():
                    if name.startswith("original/"):
                        self.assertEqual(control.read(name), facet.read(name), name)
                final = facet.read("shaders/final.fsh").decode()
                for index in (9, 10, 11):
                    self.assertIn(f"texelFetch(colortex{index},p,0)", final)
                metadata = json.loads(facet.read("UNDERWATER-PROBE.json"))
                self.assertEqual(metadata["mode"], "facet-atlas")
                self.assertFalse(metadata["shipping_fix"])
                self.assertIn("same final atlas display", facet.read("UNDERWATER-PROBE.txt").decode())

    def test_public_fixed_phase_pair_keeps_one_optical_assignment_and_original_uniforms(self):
        script = self.root / "tools/underwater_probe_pack.py"
        paths = sorted(p for p in (self.root / "shaders").rglob("*") if p.is_file())
        before = {p: p.read_bytes() for p in paths}
        with tempfile.TemporaryDirectory() as temporary:
            atlas = Path(temporary) / "atlas-fixed.zip"
            result = subprocess.run([sys.executable, "-B", str(script), str(atlas), "--mode", "atlas", "--fixed-phase", "120.0"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            facet = build_pack(self.root, Path(temporary) / "facet-atlas-fixed.zip", "facet-atlas", fixed_phase=120.0)
            with ZipFile(atlas) as control, ZipFile(facet) as changed:
                uniforms = control.read("shaders/lib/uniforms.glsl").decode()
                self.assertIn("uniform float frameTimeCounter;\n/* UNDERWATER_PROBE_BEGIN */\n#define frameTimeCounter 120.0\n", uniforms)
                recovered = re.sub(r"/\* UNDERWATER_PROBE_BEGIN \*/.*?/\* UNDERWATER_PROBE_END \*/\n", "", uniforms, flags=re.S)
                self.assertEqual(recovered, (self.root / "shaders/lib/uniforms.glsl").read_text())
                self.assertEqual(control.read("original/shaders/lib/uniforms.glsl"), (self.root / "shaders/lib/uniforms.glsl").read_bytes())
                assignment = "            n=normalize(vec3(-wave.y,1.0,-wave.z));\n"
                original = control.read("shaders/gbuffers_water.fsh").decode()
                self.assertEqual(original.count(assignment), 1)
                for name in control.namelist():
                    if name.startswith(("shaders/", "original/")):
                        expected = original.replace(assignment, "            n=rasterFacet;\n", 1).encode() if name == "shaders/gbuffers_water.fsh" else control.read(name)
                        self.assertEqual(changed.read(name), expected, name)
                for archive in (control, changed):
                    metadata = json.loads(archive.read("UNDERWATER-PROBE.json"))
                    self.assertEqual(metadata["fixed_phase_seconds"], 120.0)
                    self.assertFalse(metadata["GL_neutrality_verified"])
                    self.assertIn("does not freeze", archive.read("UNDERWATER-PROBE.txt").decode())
            self.assertEqual(before, {p: p.read_bytes() for p in paths})

    def test_fixed_phase_rejects_nonfinite_or_out_of_bounds_values_before_any_write(self):
        script = self.root / "tools/underwater_probe_pack.py"
        with tempfile.TemporaryDirectory() as temporary:
            for index, phase in enumerate((float("nan"), float("inf"), -float("inf"), -1.0, 12000.1, True, "120.0", 10**1000)):
                target = Path(temporary) / f"missing-{index}" / "rejected.zip"
                with self.subTest(phase_index=index), self.assertRaises(ValueError):
                    build_pack(self.root, target, "facet-atlas", fixed_phase=phase)
                self.assertFalse(target.parent.exists(), "Invalid phase must not create directories")
            for index, argument in enumerate(("nan", "inf", "-1", "12000.1")):
                target = Path(temporary) / f"cli-missing-{index}" / "rejected.zip"
                result = subprocess.run([sys.executable, "-B", str(script), str(target), "--mode", "atlas", "--fixed-phase", argument],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(target.parent.exists())
            for phase in (0.0, 12000.0):
                target = build_pack(self.root, Path(temporary) / f"valid-{phase}.zip", "atlas", fixed_phase=phase)
                with ZipFile(target) as archive:
                    self.assertEqual(json.loads(archive.read("UNDERWATER-PROBE.json"))["fixed_phase_seconds"], phase)
                    self.assertIn(f"#define frameTimeCounter {phase!r}\n", archive.read("shaders/lib/uniforms.glsl").decode())

    def test_no_fixed_phase_keeps_default_archives_and_metadata_identical(self):
        with tempfile.TemporaryDirectory() as temporary:
            for mode in ("baseline", "atlas", "facet", "reasons"):
                first = build_pack(self.root, Path(temporary) / (mode + "-default.zip"), mode)
                second = build_pack(self.root, Path(temporary) / (mode + "-none.zip"), mode, fixed_phase=None)
                self.assertEqual(first.read_bytes(), second.read_bytes())
                with ZipFile(second) as archive:
                    self.assertNotIn("fixed_phase_seconds", json.loads(archive.read("UNDERWATER-PROBE.json")))
                    self.assertEqual(archive.read("shaders/lib/uniforms.glsl"), (self.root / "shaders/lib/uniforms.glsl").read_bytes())

    def test_never_overwrites_an_existing_archive_or_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = build_pack(self.root, Path(temporary) / "baseline.zip", "baseline")
            original = target.read_bytes()
            with self.assertRaises(FileExistsError):
                build_pack(self.root, target, "atlas")
            self.assertEqual(target.read_bytes(), original)
            link = Path(temporary) / "reserved.zip"
            missing = Path(temporary) / "absent.zip"
            link.symlink_to(missing)
            with self.assertRaises(FileExistsError):
                build_pack(self.root, link, "baseline")
            self.assertFalse(missing.exists())

    def test_archive_keeps_immutable_originals_license_and_honest_mode_legend(self):
        source_files = sorted(p for p in (self.root / "shaders").rglob("*") if p.is_file())
        with tempfile.TemporaryDirectory() as temporary:
            for mode in ("baseline", "atlas", "facet", "reasons"):
                target = build_pack(self.root, Path(temporary) / (mode + ".zip"), mode)
                with ZipFile(target) as archive:
                    self.assertTrue("UNDERWATER-PROBE.txt" in archive.namelist(),
                                    "diagnostic mode and limits must accompany the ZIP")
                    self.assertEqual(archive.read("LICENSE"), (self.root / "LICENSE").read_bytes())
                    metadata = json.loads(archive.read("UNDERWATER-PROBE.json"))
                    self.assertEqual(metadata["mode"], mode)
                    self.assertFalse(metadata["shipping_fix"])
                    self.assertFalse(metadata["natural_underwater_accepted"])
                    self.assertFalse(metadata["GL_neutrality_verified"])
                    for path in source_files:
                        name = path.relative_to(self.root).as_posix()
                        original = archive.read("original/" + name)
                        self.assertEqual(original, path.read_bytes())
                        self.assertEqual(metadata["original_sha256"][name], hashlib.sha256(original).hexdigest())
                    self.assertIn("TEST ONLY", archive.read("UNDERWATER-PROBE.txt").decode())

    def test_public_cli_routes_only_the_four_approved_modes(self):
        script = self.root / "tools/underwater_probe_pack.py"
        with tempfile.TemporaryDirectory() as temporary:
            for mode in ("baseline", "atlas", "facet", "reasons"):
                target = Path(temporary) / (mode + ".zip")
                result = subprocess.run([sys.executable, "-B", str(script), str(target), "--mode", mode],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(target.exists(), "CLI must actually create the requested diagnostic ZIP")
                with ZipFile(target) as archive:
                    self.assertEqual(json.loads(archive.read("UNDERWATER-PROBE.json"))["mode"], mode)
            rejected = Path(temporary) / "rejected.zip"
            result = subprocess.run([sys.executable, "-B", str(script), str(rejected), "--mode", "shipping"],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(rejected.exists())

    def test_rejects_unknown_modes_and_resolved_shipping_destinations(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            (source / "shaders").mkdir()
            dist = Path(temporary) / "shipping-dist"
            dist.mkdir()
            (source / "dist").symlink_to(dist, target_is_directory=True)
            alias = Path(temporary) / "alias"
            alias.symlink_to(source / "shaders", target_is_directory=True)
            rejected = Path(temporary) / "unknown.zip"
            with self.assertRaises(ValueError):
                build_pack(source, rejected, "shipping")
            self.assertFalse(rejected.exists())
            for directory in (source / "shaders", source / "dist", alias):
                destination = directory / "never-created.zip"
                with self.assertRaises(ValueError):
                    build_pack(source, destination, "baseline")
                self.assertFalse(destination.exists())

    def test_identical_inputs_produce_byte_identical_archives_in_every_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            for mode in ("baseline", "atlas", "facet", "reasons"):
                first = build_pack(self.root, Path(temporary) / (mode + "-first.zip"), mode)
                second = build_pack(self.root, Path(temporary) / (mode + "-second.zip"), mode)
                self.assertEqual(first.read_bytes(), second.read_bytes())
                with ZipFile(first) as archive:
                    self.assertEqual(archive.namelist(), sorted(archive.namelist()))
                    self.assertTrue(all(entry.date_time == (2026, 10, 2, 0, 0, 0) for entry in archive.infolist()))


if __name__ == "__main__":
    unittest.main()
