import json
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

import water_optical_probe as probe


ROOT = Path("/home/kusutohu/repos/aqualumen")


class OpticalProbeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        probe.read_pinned(ROOT / probe.BASE, probe.BASE_SHA)
        with zipfile.ZipFile(ROOT / probe.BASE) as archive:
            cls.base = {name: archive.read(name) for name in archive.namelist()}
        cls.sources = {name: probe.read_pinned(ROOT / "tools/paired-water-probe" / name, pin) for name, pin in probe.SOURCE_PINS.items()}

    def test_exact_output_order_and_schema(self):
        pack = probe.optical_pack(self.base)
        f = pack["shaders/gbuffers_water.fsh"].decode()
        self.assertIn("/* RENDERTARGETS:0,12,1,2,3,13,14,15 */", f)
        self.assertEqual(list(probe.CHANNELS), [1, 2, 3, 13, 14, 15])
        self.assertTrue(all(len(channels) == 4 for channels in probe.CHANNELS.values()))
        for slot in range(2, 8):
            self.assertLess(f.index(f"gl_FragData[{slot}]=vec4(0.0);"), f.index("materialId!=10000.0"))
        for target in probe.CHANNELS:
            self.assertIn(f"colortex{target}Format = RGBA32F", pack["shaders/prepare.fsh"].decode())
            self.assertRegex(pack["shaders/prepare.fsh"].decode(), rf"(?m)^const int colortex{target}Format = RGBA32F;$")
            self.assertIn(f"blend.gbuffers_water.colortex{target}=off", pack["shaders/shaders.properties"].decode())

    def test_c0_and_preview_zero_text_invariant(self):
        pack = probe.optical_pack(self.base)
        pattern = r"gl_FragData\[0\]=[^;]+;"
        self.assertEqual(re.findall(pattern, self.base["shaders/gbuffers_water.fsh"].decode()), re.findall(pattern, pack["shaders/gbuffers_water.fsh"].decode()))
        old = self.base["shaders/final.fsh"].decode()
        new = pack["shaders/final.fsh"].decode()
        self.assertEqual(old[old.index("void main()"):old.index("    // TEST paired-water")], new[new.index("void main()"):new.index("    // TEST paired-water")])
        self.assertNotIn("aqualumenPairedView!=0", new)
        for view in range(1, 8):
            self.assertIn(f"aqualumenPairedView=={view}", new)
        self.assertIn(b"uniform.int.aqualumenPairedView=0", pack["shaders/shaders.properties"])

    def test_no_recomputed_rays_or_changed_shared_physics(self):
        pack = probe.optical_pack(self.base)
        old = self.base["shaders/gbuffers_water.fsh"].decode()
        new = pack["shaders/gbuffers_water.fsh"].decode()
        for function in ("refract(", "reflectionTrace(", "refractionTrace(", "localWaveState("):
            self.assertEqual(old.count(function), new.count(function))
        for name in self.base:
            if name not in {"shaders/gbuffers_water.fsh", "shaders/final.fsh", "shaders/prepare.fsh", "shaders/shaders.properties"}:
                self.assertEqual(self.base[name], pack[name], name)

    def test_strict_mutation_rejected(self):
        broken = dict(self.base)
        broken["shaders/gbuffers_water.fsh"] = broken["shaders/gbuffers_water.fsh"].replace(b"/* RENDERTARGETS: 0,12 */", b"/* RENDERTARGETS:0,12,9 */")
        with self.assertRaises(ValueError):
            probe.optical_pack(broken)
        with self.assertRaises(ValueError):
            probe.replace_one("a a", "a", "b")
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "input"
            p.write_bytes(b"wrong")
            with self.assertRaises(ValueError):
                probe.read_pinned(p, "0" * 64)

    def test_generated_observer_retains_scope_and_finite_guard(self):
        sources = probe.observer_sources(self.sources)
        s = sources["dev/aqualumen/paired/PairedObserver.java"].decode()
        old = self.sources["dev/aqualumen/paired/PairedObserver.java"].decode()
        for anchor in ("private static boolean scope(", "private static Map<String,Object> mods(", "private static boolean recorderReady(", "private static CaptureRules.Identity identity("):
            start = old.index(anchor)
            end = old.index("\n    private static", start + 1)
            self.assertIn(old[start:end], s)
        self.assertIn('manifest.put("opticalSamplers",opticalSamplers)', s)
        self.assertEqual(s.count('"optical samplers changed after FINAL"'), 2)
        self.assertIn('"optics-"+entry.getKey()+".rgba32f"', s)
        self.assertIn('files.put("sourceC0",write(p.out(),"source-C0.rgba32f"', s)
        self.assertIn("Float.isFinite", sources["dev/aqualumen/paired/GlReadback.java"].decode())
        self.assertNotIn("glGetError", sources["dev/aqualumen/paired/GlReadback.java"].decode())
        self.assertEqual(json.loads(sources["fabric.mod.json"])["version"], probe.VERSION)

    def test_deterministic_exclusive_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "first", Path(directory) / "second"
            a = probe.generate(ROOT, first)
            b = probe.generate(ROOT, second)
            self.assertEqual(a, b)
            self.assertEqual((first / "optical.zip").read_bytes(), (second / "optical.zip").read_bytes())
            with self.assertRaises(FileExistsError):
                probe.generate(ROOT, first)
            self.assertEqual(a["outputOrder"], [0, 12, 1, 2, 3, 13, 14, 15])


if __name__ == "__main__":
    unittest.main()
