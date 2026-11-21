"""Packaging safeguards, not a shoreline-quality acceptance test."""
import hashlib
from pathlib import Path
import tempfile
import re
import unittest
from zipfile import ZipFile

from shore_probe_pack import build_pack


class ShoreProbePackTest(unittest.TestCase):
    def assert_colour_preserved(self, original, instrumented):
        recovered = re.sub(r"/\* SHORE_PROBE_BEGIN \*/.*?/\* SHORE_PROBE_END \*/\n", "", instrumented, flags=re.S)
        recovered = re.sub(r"/\* RENDERTARGETS:0,9,10,11,12,13,14(?:,15)? \*/", "/* DRAWBUFFERS:0 */", recovered)
        self.assertEqual(original, recovered)
        self.assertEqual(instrumented.count("gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);"), 1)

    def test_diagnostic_keeps_production_colour_and_shipping_sources(self):
        root = Path(__file__).resolve().parents[1]
        sources = sorted(p for p in (root / "shaders").rglob("*") if p.is_file())
        before = {p: hashlib.sha256(p.read_bytes()).digest() for p in sources}
        original = (root / "shaders/gbuffers_water.fsh").read_text()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "ShoreProbe.zip"
            build_pack(root, target)
            with ZipFile(target) as archive:
                instrumented = archive.read("shaders/gbuffers_water.fsh").decode()
                # The original invocation and colour tail remain verbatim;
                # additional stores cannot replace its transport calculation.
                self.assert_colour_preserved(original, instrumented)
            self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).digest() for p in sources})
            with self.assertRaises(FileExistsError):
                build_pack(root, target)

    def test_transport_archive_keeps_real_trace_and_colour_invocation(self):
        root = Path(__file__).resolve().parents[1]
        original = (root / "shaders/gbuffers_water.fsh").read_text()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "Transport.zip"
            build_pack(root, target, "transport")
            with ZipFile(target) as archive:
                self.assert_colour_preserved(original, archive.read("shaders/gbuffers_water.fsh").decode())

    def test_world_probe_exports_positions_from_same_original_water_invocation(self):
        root = Path(__file__).resolve().parents[1]
        original = (root / "shaders/gbuffers_water.fsh").read_text()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "World.zip"
            build_pack(root, target, "world")
            with ZipFile(target) as archive:
                water = archive.read("shaders/gbuffers_water.fsh").decode()
                self.assert_colour_preserved(original, water)
                self.assertIn("absolutePosition,localColumnKnown?1.0:0.0", water)
                self.assertIn("transmitted,receiverConfidence", water)
                self.assertIn("probeReceiver,float(receiverKind)", water)
                self.assertIn("thickness,initialPath,verticalDepth,straightPath", water)
                self.assertIn("opaqueWorld+cameraPosition,localColumn.x", water)
                self.assertIn("n,fresnel", water)
                self.assertIn("same-invocation absolute world", archive.read("SHORE-PROBE.txt").decode())

    def test_refuses_new_files_inside_shipping_trees(self):
        root = Path(__file__).resolve().parents[1]
        for folder in ("dist/nested", "shaders/lib"):
            with self.assertRaises(ValueError):
                build_pack(root, root / folder / "NeverCreated-ShoreProbe.zip")


if __name__ == "__main__":
    unittest.main()
