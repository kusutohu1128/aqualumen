"""CPU contract tests for the isolated land-shadow preview pack."""

from dataclasses import FrozenInstanceError, replace
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import warnings
from zipfile import ZipFile

import land_shadow_pack as pack


BASE = Path("/home/kusutohu/repos/aqualumen/reports/2026-10-23-land-shadows/ordinary-0.6.zip")
LIBRARIES = Path(__file__).resolve().parents[1] / "shaders" / "lib"
TOOL = Path(__file__).with_name("land_shadow_pack.py")


def archive_bytes(entries):
    buffer = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with ZipFile(buffer, "w") as archive:
            for entry in entries:
                archive.writestr(entry.name, entry.payload)
    return buffer.getvalue()


def changed(entries, name, payload):
    return tuple(replace(entry, payload=payload) if entry.name == name else entry for entry in entries)


class LandShadowPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = pack.load_base(BASE)
        cls.sources = pack.load_libraries(LIBRARIES)
        cls.preview = pack.preview_entries(cls.base, cls.sources)

    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, str(TOOL), *map(str, arguments)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    def test_pinned_base_has_exactly_46_immutable_entries(self):
        self.assertEqual(hashlib.sha256(BASE.read_bytes()).hexdigest(), pack.BASE_SHA256)
        self.assertEqual(len(self.base.entries), 46)
        self.assertEqual({entry.name for entry in self.base.entries}, pack.BASE_NAMES)
        with self.assertRaises(FrozenInstanceError):
            self.base.entries[0].name = "other"
        with self.assertRaises(TypeError):
            self.sources[pack.LIBRARY_NAMES[0]] = b"other"

    def test_only_two_wrapper_lines_and_two_added_payloads_change(self):
        original = {entry.name: entry.payload for entry in self.base.entries}
        output = {entry.name: entry.payload for entry in self.preview}
        self.assertEqual(set(output), set(original) | set(pack.LIBRARY_NAMES))
        altered = {name for name in original if original[name] != output[name]}
        self.assertEqual(altered, pack.WRAPPERS)
        for name in original:
            with self.subTest(name=name):
                if name in pack.WRAPPERS:
                    old = original[name].splitlines(keepends=True)
                    new = output[name].splitlines(keepends=True)
                    self.assertEqual(len(old), len(new))
                    differences = [(a, b) for a, b in zip(old, new) if a != b]
                    self.assertEqual(
                        differences,
                        [(b'#include "/lib/lighting.glsl"\n', b'#include "/lib/land_lighting.glsl"\n')],
                    )
                else:
                    self.assertEqual(output[name], original[name])
        for name in pack.LIBRARY_NAMES:
            self.assertEqual(output[name], self.sources[name])

    def test_all_nonopaque_expansions_including_water_are_exact(self):
        original = {entry.name: entry.payload for entry in self.base.entries}
        output = {entry.name: entry.payload for entry in self.preview}
        roots = {
            name
            for name in original
            if Path(name).parent == Path("shaders")
            and Path(name).suffix in (".fsh", ".vsh", ".csh")
            and name not in pack.WRAPPERS
        }
        self.assertIn("shaders/gbuffers_water.fsh", roots)
        self.assertIn("shaders/gbuffers_water.vsh", roots)
        for name in roots:
            with self.subTest(name=name):
                self.assertEqual(pack.expanded_shader(output, name), pack.expanded_shader(original, name))
        audit = pack.audit_preservation(self.base, self.preview, self.sources)
        self.assertEqual(set(audit["preserved_nonopaque_expansions"]), roots)
        self.assertEqual(audit["preserved_original_entries"], 44)

    def test_adapter_scopes_alias_and_refuses_prior_instantiation_or_alias(self):
        text = self.sources["shaders/lib/land_lighting.glsl"].decode()
        self.assertIn('#include "/lib/lighting.glsl"\n#undef shadowVisibility\n', text)
        positions = [
            text.index('#include "/lib/shadows.glsl"'),
            text.index('#include "/lib/land_shadows.glsl"'),
            text.index("#ifdef AQUALUMEN_LIGHTING\n#error"),
            text.index("#ifdef shadowVisibility\n#error"),
            text.index("#define shadowVisibility landShadowVisibility"),
            text.index('#include "/lib/lighting.glsl"'),
            text.index("#undef shadowVisibility"),
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(text.count("#define shadowVisibility "), 1)
        self.assertEqual(text.count("#undef shadowVisibility"), 1)

    def test_identity_routes_unchanged_arguments_to_legacy(self):
        text = self.sources["shaders/lib/land_shadows.glsl"].decode()
        body = re.search(r"float\s+landShadowVisibility\s*\(([^)]*)\)\s*\{([^}]*)\}", text)
        self.assertIsNotNone(body)
        self.assertEqual(re.sub(r"\s+", "", body.group(1)), "vec3relativePosition,vec3normal")
        self.assertEqual(re.sub(r"\s+", "", body.group(2)), "returnshadowVisibility(relativePosition,normal);")

    def test_cpu_preprocessor_routes_land_calls_without_leaking_alias(self):
        output = {entry.name: entry.payload for entry in self.preview}
        probe = "\nfloat aliasScopeProbe(vec3 p, vec3 n) { return shadowVisibility(p, n); }\n"
        for name in pack.WRAPPERS:
            with self.subTest(name=name):
                source = pack.expanded_shader(output, name).decode()
                source = source.replace("#version 330 compatibility\n", "") + probe
                result = subprocess.run(
                    ["cpp", "-P", "-x", "c", "-"],
                    input=source,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                code = re.sub(r"\s+", "", result.stdout)
                self.assertIn("returnshadowVisibility(relativePosition,normal);", code)
                self.assertEqual(code.count("landShadowVisibility(position,normal)"), 2)
                self.assertIn("floataliasScopeProbe(vec3p,vec3n){returnshadowVisibility(p,n);}", code)

    def test_cpu_preprocessor_rejects_prior_lighting_or_shadow_alias(self):
        output = {entry.name: entry.payload for entry in self.preview}
        source = pack.expanded_shader(output, "shaders/gbuffers_terrain.fsh").decode()
        source = source.replace("#version 330 compatibility\n", "")
        cases = (
            ("#define AQUALUMEN_LIGHTING\n", "must instantiate the lighting body first"),
            ("#define shadowVisibility anotherFunction\n", "requires an unaliased shadowVisibility"),
        )
        for prefix, message in cases:
            with self.subTest(prefix=prefix):
                result = subprocess.run(
                    ["cpp", "-P", "-x", "c", "-"],
                    input=prefix + source,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)

    def test_added_libraries_have_no_sampler_or_global_shadow_directives(self):
        for name, payload in self.sources.items():
            with self.subTest(name=name):
                self.assertIsNone(pack.RESERVED_LIBRARY.search(payload.decode()))

    def test_library_boundary_rejects_reserved_resources_and_directives(self):
        mutations = (
            "uniform sampler2DShadow anotherShadow;\n",
            "const int shadowMapResolution = 4096;\n",
            "#version 330 compatibility\n",
            "#extension GL_ARB_gpu_shader5 : enable\n",
            "layout(rgba32f) uniform image2D field;\n",
        )
        with tempfile.TemporaryDirectory(prefix="aqualumen-land-pack-library-") as temp:
            directory = Path(temp)
            for name, payload in self.sources.items():
                (directory / Path(name).name).write_bytes(payload)
            target = directory / "land_shadows.glsl"
            for mutation in mutations:
                with self.subTest(mutation=mutation):
                    target.write_bytes(self.sources["shaders/lib/land_shadows.glsl"] + mutation.encode())
                    with self.assertRaisesRegex(ValueError, "reserved resource or global directive"):
                        pack.load_libraries(directory)

    def test_parser_rejects_missing_archive_entry(self):
        entries = tuple(entry for entry in self.base.entries if entry.name != "shaders/shadow.vsh")
        with self.assertRaisesRegex(ValueError, "missing=.*shaders/shadow.vsh"):
            pack.parse_archive(archive_bytes(entries))

    def test_parser_rejects_duplicate_archive_entry(self):
        entries = (*self.base.entries, self.base.entries[0])
        with self.assertRaisesRegex(ValueError, "duplicate archive entry"):
            pack.parse_archive(archive_bytes(entries))

    def test_parser_rejects_unsafe_archive_paths(self):
        for name in ("../escape", "/absolute", "shaders/../escape", "shaders//shadow.fsh", "shaders\\shadow.fsh", "./LICENSE"):
            with self.subTest(name=name):
                entries = (*self.base.entries, pack.ArchiveEntry(name, b"bad"))
                with self.assertRaisesRegex(ValueError, "unsafe archive entry"):
                    pack.parse_archive(archive_bytes(entries))

    def test_parser_rejects_unknown_archive_entry(self):
        entries = (*self.base.entries, pack.ArchiveEntry("shaders/extra.fsh", b"bad"))
        with self.assertRaisesRegex(ValueError, "extra=.*shaders/extra.fsh"):
            pack.parse_archive(archive_bytes(entries))

    def test_parser_rejects_missing_or_duplicate_wrapper_marker(self):
        name = "shaders/gbuffers_terrain.fsh"
        original = next(entry.payload for entry in self.base.entries if entry.name == name)
        for payload in (
            original.replace(pack.LIGHTING_INCLUDE, b""),
            original + pack.LIGHTING_INCLUDE,
        ):
            with self.subTest(payload=payload):
                entries = changed(self.base.entries, name, payload)
                with self.assertRaisesRegex(ValueError, "exactly one lighting include"):
                    pack.parse_archive(archive_bytes(entries))

    def test_preservation_audit_rejects_injected_entry(self):
        bad = (*self.preview, pack.ArchiveEntry("shaders/extra.fsh", b"bad"))
        with self.assertRaisesRegex(ValueError, "archive names differ"):
            pack.audit_preservation(self.base, bad, self.sources)

    def test_preservation_audit_rejects_changed_water(self):
        name = "shaders/gbuffers_water.fsh"
        old = next(entry.payload for entry in self.preview if entry.name == name)
        bad = changed(self.preview, name, old + b"\n#define BAD_WATER_CHANGE\n")
        with self.assertRaisesRegex(ValueError, "preservation failed for shaders/gbuffers_water.fsh"):
            pack.audit_preservation(self.base, bad, self.sources)

    def test_preservation_audit_rejects_wrong_wrapper(self):
        name = "shaders/gbuffers_textured_lit.fsh"
        original = next(entry.payload for entry in self.base.entries if entry.name == name)
        bad = changed(self.preview, name, original)
        with self.assertRaisesRegex(ValueError, "preservation failed for shaders/gbuffers_textured_lit.fsh"):
            pack.audit_preservation(self.base, bad, self.sources)

    def test_preservation_audit_rejects_modified_original_library(self):
        name = "shaders/lib/lighting.glsl"
        old = next(entry.payload for entry in self.preview if entry.name == name)
        bad = changed(self.preview, name, old + b"\n#define BAD_LIGHTING_CHANGE\n")
        with self.assertRaisesRegex(ValueError, "preservation failed for shaders/lib/lighting.glsl"):
            pack.audit_preservation(self.base, bad, self.sources)

    def test_cli_builds_real_reproducible_zip_and_hash_manifest(self):
        with tempfile.TemporaryDirectory(prefix="aqualumen-land-pack-cli-") as temp:
            outputs = [Path(temp) / "first.zip", Path(temp) / "second.zip"]
            for output in outputs:
                result = self.run_cli("--base", BASE, "--output", output)
                self.assertEqual(result.returncode, 0, result.stderr)
                receipt = json.loads(result.stdout)
                self.assertEqual(receipt["output"], str(output))
                self.assertEqual(receipt["manifest"], str(pack.sidecar_path(output)))
                self.assertEqual(receipt["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
            self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())
            self.assertEqual(pack.sidecar_path(outputs[0]).read_bytes(), pack.sidecar_path(outputs[1]).read_bytes())
            manifest = json.loads(pack.sidecar_path(outputs[0]).read_text())
            self.assertEqual(manifest["base_sha256"], pack.BASE_SHA256)
            self.assertEqual(manifest["changed"], sorted(pack.WRAPPERS))
            self.assertEqual(manifest["added"], sorted(pack.LIBRARY_NAMES))
            for name in pack.LIBRARY_NAMES:
                self.assertEqual(manifest["source_sha256"][name], hashlib.sha256(self.sources[name]).hexdigest())
            with ZipFile(outputs[0]) as archive:
                entries = tuple(pack.ArchiveEntry(info.filename, archive.read(info)) for info in archive.infolist())
                self.assertEqual(len(entries), 48)
                self.assertEqual(set(archive.namelist()), pack.BASE_NAMES | set(pack.LIBRARY_NAMES))
                self.assertEqual(len(set(info.date_time for info in archive.infolist())), 1)
                for entry in entries:
                    self.assertEqual(manifest["output_entry_sha256"][entry.name], hashlib.sha256(entry.payload).hexdigest())
            pack.audit_preservation(self.base, entries, self.sources)

    def test_cli_reads_only_two_new_library_files(self):
        with tempfile.TemporaryDirectory(prefix="aqualumen-land-pack-input-") as temp:
            directory = Path(temp) / "libraries"
            directory.mkdir()
            for name, payload in self.sources.items():
                (directory / Path(name).name).write_bytes(payload)
            (directory / "lighting.glsl").write_bytes(b"DO NOT IMPORT DIRTY LIGHTING")
            (directory / "water.glsl").write_bytes(b"DO NOT IMPORT DIRTY WATER")
            output = Path(temp) / "preview.zip"
            result = self.run_cli("--base", BASE, "--output", output, "--library-dir", directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), pack.zip_bytes(self.preview))

    def test_cli_rejects_tampered_base_without_outputs(self):
        with tempfile.TemporaryDirectory(prefix="aqualumen-land-pack-tamper-") as temp:
            base = Path(temp) / "tampered.zip"
            base.write_bytes(BASE.read_bytes() + b"tampered")
            output = Path(temp) / "preview.zip"
            result = self.run_cli("--base", base, "--output", output)
            self.assertEqual(result.returncode, 2)
            self.assertIn("base SHA-256 differs", result.stderr)
            self.assertFalse(output.exists())
            self.assertFalse(pack.sidecar_path(output).exists())
            self.assertEqual(hashlib.sha256(BASE.read_bytes()).hexdigest(), pack.BASE_SHA256)

    def test_cli_existing_zip_is_untouched(self):
        with tempfile.TemporaryDirectory(prefix="aqualumen-land-pack-collision-") as temp:
            output = Path(temp) / "preview.zip"
            output.write_bytes(b"EXISTING ZIP")
            result = self.run_cli("--base", BASE, "--output", output)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(output.read_bytes(), b"EXISTING ZIP")
            self.assertFalse(pack.sidecar_path(output).exists())

    def test_cli_existing_manifest_refuses_before_zip_creation(self):
        with tempfile.TemporaryDirectory(prefix="aqualumen-land-pack-sidecar-") as temp:
            output = Path(temp) / "preview.zip"
            sidecar = pack.sidecar_path(output)
            sidecar.write_bytes(b"EXISTING MANIFEST")
            result = self.run_cli("--base", BASE, "--output", output)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())
            self.assertEqual(sidecar.read_bytes(), b"EXISTING MANIFEST")

    def test_cli_existing_zip_and_manifest_are_untouched(self):
        with tempfile.TemporaryDirectory(prefix="aqualumen-land-pack-both-") as temp:
            output = Path(temp) / "preview.zip"
            output.write_bytes(b"EXISTING ZIP")
            sidecar = pack.sidecar_path(output)
            sidecar.write_bytes(b"EXISTING MANIFEST")
            result = self.run_cli("--base", BASE, "--output", output)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(output.read_bytes(), b"EXISTING ZIP")
            self.assertEqual(sidecar.read_bytes(), b"EXISTING MANIFEST")

    def test_cli_rejects_dangling_symlink_outputs_without_touching_them(self):
        for sidecar_collision in (False, True):
            with self.subTest(sidecar_collision=sidecar_collision):
                with tempfile.TemporaryDirectory(prefix="aqualumen-land-pack-symlink-") as temp:
                    output = Path(temp) / "preview.zip"
                    collision = pack.sidecar_path(output) if sidecar_collision else output
                    collision.symlink_to("missing-target")
                    result = self.run_cli("--base", BASE, "--output", output)
                    self.assertEqual(result.returncode, 2)
                    self.assertTrue(collision.is_symlink())
                    self.assertEqual(collision.readlink(), Path("missing-target"))
                    other = output if sidecar_collision else pack.sidecar_path(output)
                    self.assertFalse(other.exists())

    def test_cli_requires_explicit_base_and_output(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("--base", result.stderr)
        self.assertIn("--output", result.stderr)


if __name__ == "__main__":
    unittest.main()
