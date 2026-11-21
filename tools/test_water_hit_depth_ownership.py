import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import water_hit_depth_ownership as owner
import water_optical_probe as probe


ROOT = Path("/home/kusutohu/repos/aqualumen")
STAGING = Path(__file__).parent


class HitDepthOwnershipTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = {mode: owner.pinned_inputs(ROOT, mode) for mode in owner.VERSIONS}

    def test_only_known_nonwater_sources_change(self):
        for mode, (_, _, packs, _) in self.inputs.items():
            with self.subTest(mode=mode):
                result, metadata = owner.mark_nonwater(packs["paired"])
                changed = {name for name in result if result[name] != packs["paired"][name]}
                self.assertEqual(changed, {"shaders/gbuffers_textured.fsh", "shaders/lib/terrain.fsh.glsl", "shaders/shaders.properties"})
                for name in owner.PATCHED_FILES:
                    old = packs["paired"][name].decode()
                    new = result[name].decode()
                    self.assertIn("/* RENDERTARGETS:0,5,12,3 */", new)
                    self.assertIn(owner.MARKER_WRITES, new)
                    marker_at = new.index(owner.MARKER_WRITES)
                    self.assertLess(new.rindex("discard;"), marker_at)
                    self.assertLess(marker_at, new.index("gl_FragData[0]="))
                    restored = new.replace("/* RENDERTARGETS:0,5,12,3 */", "/* DRAWBUFFERS:05 */").replace(owner.MARKER_WRITES, "")
                    self.assertEqual(old, restored)
                    self.assertEqual(re.findall(r"gl_FragData\[[01]\]=[^;]+;", old), re.findall(r"gl_FragData\[[01]\]=[^;]+;", new))
                    self.assertNotIn("gl_FragDepth", new)
                self.assertEqual(metadata["patchedSourcePrograms"], ["gbuffers_textured", "gbuffers_terrain", "gbuffers_textured_lit"])
                self.assertEqual(metadata["patchedSourceProgramBindings"], owner.PATCHED_BINDINGS)
                for name, data in packs["paired"].items():
                    if name not in changed:
                        self.assertEqual(result[name], data, name)

    def test_all_pinned_program_blend_aliases_are_off_once(self):
        expected_ids = {
            "basic", "line", "textured", "textured_lit", "skybasic", "skytextured", "clouds", "terrain", "terrain_solid",
            "terrain_cutout", "damagedblock", "block", "block_translucent", "beaconbeam", "item", "entities", "entities_translucent",
            "lightning", "particles", "particles_translucent", "entities_glowing", "armor_glint", "spidereyes", "hand", "weather", "water", "hand_water",
        }
        self.assertEqual(set(owner.PROGRAM_IDS), {"gbuffers_" + name for name in expected_ids})
        for _, _, packs, _ in self.inputs.values():
            result, metadata = owner.mark_nonwater(packs["paired"])
            before = owner.properties(packs["paired"]["shaders/shaders.properties"].decode())
            text = result["shaders/shaders.properties"].decode()
            after = owner.properties(text)
            self.assertEqual(len(owner.BLEND_KEYS), 54)
            for program in owner.PROGRAM_IDS:
                for target in (12, 3):
                    key = f"blend.{program}.colortex{target}"
                    self.assertEqual(after[key], "off")
                    self.assertEqual(len(re.findall(r"^" + re.escape(key) + "=", text, re.MULTILINE)), 1)
            for key, value in before.items():
                self.assertEqual(after[key], value)
            self.assertFalse(metadata["fallbackProgramResolutionDirectlyObserved"])
            self.assertEqual(metadata["fallbackProgramResolution"], {})
            self.assertEqual(len(metadata["fallbackBlendProgramIds"]), 21)
            self.assertIn("gbuffers_particles", metadata["fallbackBlendProgramIds"])
            self.assertEqual(len(metadata["explicitUnmarkedPaths"]), 4)

    def test_patch_and_blend_ambiguities_fail_closed(self):
        packs = self.inputs["candidate"][2]
        for key, target in (("shaders/gbuffers_textured.fsh", b"/* DRAWBUFFERS:05 */"), ("shaders/lib/terrain.fsh.glsl", b"discard;")):
            broken = dict(packs["paired"])
            broken[key] = broken[key].replace(target, b"removed")
            with self.assertRaises(ValueError):
                owner.mark_nonwater(broken)
        for suffix in (b"\nblend.gbuffers_water.colortex12=off\n", b"\nblend.gbuffers_particles.colortex3=SRC_ALPHA ONE_MINUS_SRC_ALPHA\n"):
            broken = dict(packs["paired"])
            broken["shaders/shaders.properties"] += suffix
            with self.assertRaises(ValueError):
                owner.mark_nonwater(broken)
        broken = dict(packs["paired"])
        broken["shaders/gbuffers_entities.fsh"] = b'#include "/lib/terrain.fsh.glsl"\n'
        with self.assertRaises(ValueError):
            owner.mark_nonwater(broken)

    def test_new_observer_metadata_preserves_all_readback_and_scope_code(self):
        for mode, (_, _, packs, sources) in self.inputs.items():
            _, metadata = owner.mark_nonwater(packs["paired"])
            generated = owner.observer_sources(sources, mode, metadata)
            observer = generated["dev/aqualumen/paired/PairedObserver.java"].decode()
            old = sources["dev/aqualumen/paired/PairedObserver.java"].decode()
            for key, value in metadata.items():
                self.assertIn(f"m.put({json.dumps(key)},{owner.java_value(value)});", observer)
            additions = "".join(f"        m.put({json.dumps(key)},{owner.java_value(value)});\n" for key, value in metadata.items())
            restored = observer.replace(additions, "").replace(owner.VERSIONS[mode], owner.OLD_VERSIONS[mode]).replace(owner.NEW_ATTRIBUTION, owner.OLD_ATTRIBUTION)
            restored = restored.replace('Map.of("ineligibleOrUnsolved",-1,"projectionRejected",-2,"lastKnownNonwater",-3)', 'Map.of("ineligibleOrUnsolved",-1,"projectionRejected",-2)')
            self.assertEqual(restored, old)
            self.assertEqual(generated["dev/aqualumen/paired/GlReadback.java"], sources["dev/aqualumen/paired/GlReadback.java"])
            self.assertIn('"projectedDepthOrNegativeStatus"', observer)
            self.assertIn('"markerProtocol","last-known-nonwater-diagnostic-writer-v1"', observer)
            self.assertIn('"lastKnownNonwaterMarker",-3', observer)
            self.assertEqual(json.loads(generated["fabric.mod.json"])["version"], owner.VERSIONS[mode])
            for name, data in sources.items():
                if name not in ("dev/aqualumen/paired/PairedObserver.java", "fabric.mod.json"):
                    self.assertEqual(generated[name], data, name)

    def test_generation_is_exclusive_deterministic_and_control_archive_exact(self):
        with tempfile.TemporaryDirectory(dir=STAGING) as directory:
            directory = Path(directory)
            for mode, (source_manifest, raw, packs, sources) in self.inputs.items():
                first, second = directory / (mode + "a"), directory / (mode + "b")
                a = owner.generate(ROOT, first, mode)
                b = owner.generate(ROOT, second, mode)
                self.assertEqual(a, b)
                self.assertEqual((first / "control.zip").read_bytes(), raw["control"])
                self.assertEqual((first / "control.zip").read_bytes(), (ROOT / owner.BASE / (mode + "2") / "control.zip").read_bytes())
                self.assertEqual((first / "paired.zip").read_bytes(), (second / "paired.zip").read_bytes())
                self.assertTrue(a["controlArchiveBytesExact"])
                self.assertTrue(a["waterVertexCompositeBytesExact"])
                self.assertEqual(a["inputManifest"]["sha256"], owner.MANIFEST_PINS[mode])
                self.assertEqual(a["inputArchiveSHA256"], source_manifest["archives"])
                self.assertEqual(a["sourcePins"], source_manifest["generatedSourceSha256"])
                self.assertEqual(a["inputPackSourceSha256"], source_manifest["generatedPackSourceSha256"])
                self.assertIsNone(a["observerBuild"])
                self.assertFalse(a["gpuVerified"])
                self.assertFalse(a["physicalAccepted"])
                self.assertFalse(a["visualAccepted"])
                for name, pin in a["generatedSourceSha256"].items():
                    self.assertEqual(probe.sha((first / "observer-sources" / name).read_bytes()), pin)
                for label in ("control", "paired"):
                    self.assertEqual(probe.sha((first / (label + ".zip")).read_bytes()), a["archives"][label])
                    with zipfile.ZipFile(first / (label + ".zip")) as archive:
                        self.assertEqual({name: probe.sha(archive.read(name)) for name in archive.namelist()}, a["generatedPackSourceSha256"][label])
                        for name, data in packs[label].items():
                            if label == "control" or name not in a["changedPairedEntries"]:
                                self.assertEqual(archive.read(name), data, name)
                before = {str(path.relative_to(first)): probe.sha(path.read_bytes()) for path in first.rglob("*") if path.is_file()}
                with self.assertRaises(FileExistsError):
                    owner.generate(ROOT, first, mode)
                self.assertEqual(before, {str(path.relative_to(first)): probe.sha(path.read_bytes()) for path in first.rglob("*") if path.is_file()})
                for name, pin in source_manifest["generatedSourceSha256"].items():
                    probe.read_pinned(ROOT / owner.BASE / (mode + "2") / "observer-sources" / name, pin)
                self.assertEqual(sources["dev/aqualumen/paired/GlReadback.java"], (first / "observer-sources/dev/aqualumen/paired/GlReadback.java").read_bytes())

    def test_tampered_inputs_fail_before_output_creation(self):
        with tempfile.TemporaryDirectory(dir=STAGING) as directory:
            directory = Path(directory)
            root = directory / "repo"
            base = root / owner.BASE / "baseline2"
            base.parent.mkdir(parents=True)
            shutil.copytree(ROOT / owner.BASE / "baseline2" / "observer-sources", base / "observer-sources")
            for name in ("manifest.json", "control.zip", "paired.zip"):
                shutil.copyfile(ROOT / owner.BASE / "baseline2" / name, base / name)
            (root / "tools").mkdir()
            shutil.copyfile(ROOT / "tools/water_optical_probe.py", root / "tools/water_optical_probe.py")
            for relative in ("manifest.json", "control.zip", "paired.zip", "observer-sources/dev/aqualumen/paired/GlReadback.java"):
                path = base / relative
                original = path.read_bytes()
                with path.open("ab") as output:
                    output.write(b"\ncorrupted")
                destination = directory / "should-not-exist"
                with self.assertRaises(ValueError):
                    owner.generate(root, destination, "baseline")
                self.assertFalse(destination.exists())
                with path.open("wb") as output:
                    output.write(original)
            with self.assertRaises(ValueError):
                owner.generate(ROOT, directory / "typo", "typo")

    def test_optional_observer_build_uses_new_artifact_receipt_without_java(self):
        def fake_build(root, out, sources, artifact):
            self.assertEqual(artifact, "aqualumen-paired-water-probe-0.1.0-depth3.jar")
            self.assertEqual(sources, out / "observer-sources")
            return {"exitCode": 0, "artifact": artifact, "observerSha256": "mock-build-not-java"}
        with tempfile.TemporaryDirectory(dir=STAGING) as directory, patch.object(probe, "build_observer", side_effect=fake_build) as build:
            receipt = owner.generate(ROOT, Path(directory) / "out", "candidate", True)
            self.assertEqual(build.call_count, 1)
            self.assertEqual(receipt["observerBuild"]["observerSha256"], "mock-build-not-java")

    def test_cli_generates_no_build_by_default(self):
        with tempfile.TemporaryDirectory(dir=STAGING) as directory:
            out = Path(directory) / "cli"
            run = subprocess.run([sys.executable, str(STAGING / "water_hit_depth_ownership.py"), "--root", str(ROOT), "--out", str(out), "--mode", "baseline"], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            response = json.loads(run.stdout)
            self.assertIsNone(response["observerBuild"])
            self.assertEqual(json.loads((out / "manifest.json").read_text())["observerVersion"], "0.1.0-hit1d3")


if __name__ == "__main__":
    unittest.main()
