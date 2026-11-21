"""Public CPU ZIP/CLI contracts only; no GL, game or physical acceptance."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from water_tessellation_pack import build_pack as build_density


PARENT_SHA256 = "887c3222f8ea48f244d241444cf90966f4a7ecef866047b803d3b38616d4dc3f"
PARENT_CALL = "wave=localWaveState(absolutePosition.xz,frameTimeCounter,max(footprint*1.25,0.035),localColumn,1.0,slopeVariance);"
RESOLVED_CALL = "wave=localWaveState(absolutePosition.xz,frameTimeCounter,max(footprint*1.25,0.035),localColumn,(underwater?0.0:1.0),slopeVariance);"


class UnderwaterResolvedPackTest(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]

    def test_public_cli_changes_only_known_underwater_optical_bandwidth_at_fixed_density_four(self):
        sources = sorted(p for p in (self.root / "shaders").rglob("*") if p.is_file())
        before = {p: p.read_bytes() for p in sources}
        script = self.root / "tools/underwater_resolved_pack.py"
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            parent = build_density(self.root, folder / "parent.zip", level=4, fixed_phase=120.0)
            self.assertEqual(hashlib.sha256(parent.read_bytes()).hexdigest(), PARENT_SHA256)
            target = folder / "resolved.zip"
            result = subprocess.run([sys.executable, "-B", str(script), str(target)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with ZipFile(parent) as control, ZipFile(target) as resolved:
                original = control.read("shaders/gbuffers_water.fsh").decode()
                changed = resolved.read("shaders/gbuffers_water.fsh").decode()
                self.assertEqual(original.count(PARENT_CALL), 1)
                self.assertEqual(changed, original.replace(PARENT_CALL, RESOLVED_CALL))
                self.assertEqual(changed.replace(RESOLVED_CALL, PARENT_CALL), original)
                for name in control.namelist():
                    if name.startswith(("shaders/", "original/")) and name != "shaders/gbuffers_water.fsh":
                        self.assertEqual(resolved.read(name), control.read(name), name)
                metadata = json.loads(resolved.read("UNDERWATER-RESOLVED-PROBE.json"))
                self.assertEqual(metadata["schema"], "aqualumen-underwater-resolved-probe-v1")
                self.assertEqual(metadata["mode"], "resolved-normal-atlas")
                self.assertEqual(metadata["level"], 4)
                self.assertEqual(metadata["fixed_phase_seconds"], 120.0)
                self.assertEqual(metadata["parent_pack_sha256"], PARENT_SHA256)
                self.assertEqual(metadata["normal_policy"],
                                 {"scope": "known-underwater-only", "detail": 0, "parent_detail": 1})
                self.assertEqual(metadata["normal_policy_guard"], "upperSurface && localColumnKnown")
                self.assertEqual(metadata["detail_argument"], "(underwater?0.0:1.0)")
                for key in ("test_only", "not_shipping", "optical_bandwidth_changed", "FS_optics_changed"):
                    self.assertIs(metadata[key], True, key)
                for key in ("shipping_fix", "runtime_accepted", "GL_neutrality_verified",
                            "generated_geometry_gpu_qualified", "natural_underwater_accepted",
                            "pack_enforces_world_guard", "parent_metadata_is_current_optical_policy"):
                    self.assertIs(metadata[key], False, key)
                parent_metadata = json.loads(control.read("WATER-TESSELLATION-PROBE.json"))
                self.assertEqual(metadata["original_sha256"], parent_metadata["original_sha256"])
                self.assertEqual(metadata["targets"], parent_metadata["targets"])
                self.assertEqual(resolved.read("WATER-TESSELLATION-PROBE.json"),
                                 control.read("WATER-TESSELLATION-PROBE.json"))
                for path in sources:
                    name = path.relative_to(self.root).as_posix()
                    self.assertEqual(resolved.read("original/" + name), before[path])
            self.assertEqual(before, {p: p.read_bytes() for p in sources})

    def test_public_api_and_cli_never_overwrite_or_enter_resolved_shipping_trees(self):
        from underwater_resolved_pack import build_pack
        script = self.root / "tools/underwater_resolved_pack.py"
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            reserved = folder / "reserved.zip"
            reserved.write_bytes(b"existing user artifact")
            with self.assertRaises(FileExistsError):
                build_pack(self.root, reserved)
            result = subprocess.run([sys.executable, "-B", str(script), str(reserved)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(reserved.read_bytes(), b"existing user artifact")
            link = folder / "dangling.zip"
            missing = folder / "missing.zip"
            link.symlink_to(missing)
            with self.assertRaises(FileExistsError):
                build_pack(self.root, link)
            self.assertTrue(link.is_symlink())
            self.assertFalse(missing.exists())
            source = folder / "source"
            (source / "shaders").mkdir(parents=True)
            shipping = folder / "shipping"
            shipping.mkdir()
            (source / "dist").symlink_to(shipping, target_is_directory=True)
            alias = folder / "shader-alias"
            alias.symlink_to(source / "shaders", target_is_directory=True)
            for tree in (source / "shaders", source / "dist", alias):
                destination = tree / "never.zip"
                with self.subTest(tree=tree), self.assertRaises(ValueError):
                    build_pack(source, destination)
                self.assertFalse(destination.exists())
            for option in ("--level", "--fixed-phase"):
                destination = folder / option[2:] / "never.zip"
                result = subprocess.run([sys.executable, "-B", str(script), str(destination),
                                         option, "4" if option == "--level" else "120.0"],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(destination.parent.exists(), "Fixed constants must not become tuning knobs")

    def test_public_api_rejects_missing_duplicate_or_drifted_parent_seams_before_destination_writes(self):
        from underwater_resolved_pack import build_pack
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for mode in ("missing", "duplicate", "other-source-drift"):
                source = folder / mode / "source"
                shutil.copytree(self.root / "shaders", source / "shaders")
                shutil.copyfile(self.root / "LICENSE", source / "LICENSE")
                shader = source / "shaders/gbuffers_water.fsh"
                if mode == "missing":
                    shader.write_text(shader.read_text().replace(PARENT_CALL, RESOLVED_CALL))
                elif mode == "duplicate":
                    shader.write_text(shader.read_text().replace(PARENT_CALL, PARENT_CALL + "\n" + PARENT_CALL))
                else:
                    shader.write_text(shader.read_text() + "\n// Changed unapproved parent source\n")
                before = {p: p.read_bytes() for p in (source / "shaders").rglob("*") if p.is_file()}
                destination = folder / mode / "output-not-created" / "never.zip"
                message = "seam must occur exactly once" if mode != "other-source-drift" else "pinned diagnostic digest"
                with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, message):
                    build_pack(source, destination)
                self.assertFalse(destination.parent.exists())
                self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_public_api_and_cli_are_deterministic_and_explain_parent_only_metadata_provenance(self):
        from underwater_resolved_pack import build_pack
        script = self.root / "tools/underwater_resolved_pack.py"
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            first = build_pack(self.root, folder / "first.zip")
            second = build_pack(self.root, folder / "second.zip")
            cli = folder / "cli.zip"
            result = subprocess.run([sys.executable, "-B", str(script), str(cli)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes(), cli.read_bytes())
            parent = build_density(self.root, folder / "parent.zip", level=4, fixed_phase=120.0)
            with ZipFile(first) as resolved, ZipFile(parent) as control:
                self.assertEqual(resolved.namelist(), sorted(resolved.namelist()))
                self.assertTrue(all(p.date_time == (2026, 10, 3, 0, 0, 0) for p in resolved.infolist()))
                metadata = json.loads(resolved.read("UNDERWATER-RESOLVED-PROBE.json"))
                self.assertEqual(metadata["parent_pack_metadata_member"], "WATER-TESSELLATION-PROBE.json")
                self.assertEqual(metadata["parent_pack_metadata_sha256"],
                                 hashlib.sha256(control.read("WATER-TESSELLATION-PROBE.json")).hexdigest())
                self.assertIn("parent geometry provenance only", metadata["parent_metadata_scope"])
                for key in ("geometry_source_changed", "variance_policy_changed", "transport_policy_changed",
                            "fluid_conservation_simulated", "residual_energy_integrated", "reciprocal_interface_accepted"):
                    self.assertIs(metadata[key], False, key)
                legend = resolved.read("UNDERWATER-RESOLVED-PROBE.txt").decode()
                for phrase in ("TEST ONLY", "not a shipping fix", "FS_optics_changed=false does NOT",
                               "derived values/rays/receivers may change", "does not transfer lost detail variance",
                               "no world guard"):
                    self.assertIn(phrase, legend)
                for name in ("UNDERWATER-PROBE.txt", "WATER-TESSELLATION-PROBE.txt"):
                    self.assertIn("UNDERWATER-RESOLVED-PROBE.json/.txt", resolved.read(name).decode())
                    self.assertEqual(resolved.read("PARENT-RESOLVED-" + name), control.read(name))


if __name__ == "__main__":
    unittest.main()
