"""Public CLI tests using synthetic CPU ZIP/raw data; no GL evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from test_water_tessellation_runtime import fixture as synthetic_readback


SCRIPT = Path(__file__).with_name("water_density_runtime.py")


def metadata(level):
    return {"schema": "aqualumen-water-tessellation-probe-v1",
            "mode": "fixed-density-atlas", "level": level,
            "fixed_phase_seconds": 120.0, "shipping_fix": False,
            "FS_optics_changed": False, "generated_geometry_gpu_qualified": False}


class DensityCliTests(unittest.TestCase):
    def invoke(self, level=2, mutate_metadata=None, mutate_raw=None):
        with tempfile.TemporaryDirectory(prefix="aqualumen-density-cpu-test-") as temporary:
            directory = Path(temporary)
            pack = directory / f"Aqualumen-ShoreProbe-world-water-density{level}-086-phase120-test.zip"
            meta = metadata(level)
            if mutate_metadata:
                mutate_metadata(meta)
            with ZipFile(pack, "w") as archive:
                archive.writestr("WATER-TESSELLATION-PROBE.json", json.dumps(meta))
            raw = synthetic_readback()
            raw.update(packName=pack.name, packSha256=hashlib.sha256(pack.read_bytes()).hexdigest())
            if mutate_raw:
                mutate_raw(raw)
            raw_file = directory / "synthetic-raw.json"
            raw_file.write_text(json.dumps(raw))
            before = {p.name: p.read_bytes() for p in directory.iterdir()}
            result = subprocess.run([sys.executable, "-B", str(SCRIPT), str(raw_file), str(pack)],
                                    capture_output=True, text=True)
            self.assertEqual({p.name: p.read_bytes() for p in directory.iterdir()}, before,
                             "The public auditor must never modify inputs or create output files")
            return result

    def test_synthetic_density_two_public_cli_qualifies_selected_texels_only(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(observed.get("qualifiedUnderwaterKnownStagePoints"), 16)
        self.assertEqual(observed.get("fixedDensityLevel"), 2)
        self.assertEqual(observed.get("fixedShaderPhaseSeconds"), 120.0)
        for key in ("geometryNeutralityAccepted", "generatedGeometryAccepted", "drawCountAccepted",
                    "motionAccepted", "naturalUnderwaterAccepted", "performanceAccepted", "shippingAccepted"):
            self.assertIs(observed.get(key), False, key)

    def test_public_cli_rejects_level_one_and_unapproved_or_noninteger_density(self):
        for level in (1, 3, 8, 2.0, "2", True):
            with self.subTest(level=level):
                result = self.invoke(mutate_metadata=lambda meta: meta.update(level=level))
                self.assertNotEqual(result.returncode, 0, "Only exact integer density 2/4 belongs to this CLI")

    def test_public_cli_requires_fixed_phase_density_mode_and_unaccepted_optics_geometry_flags(self):
        mutations = [lambda meta: meta.update(schema="unapproved-schema"),
                     lambda meta: meta.update(mode="passthrough-atlas"),
                     lambda meta: meta.update(fixed_phase_seconds=119.0),
                     lambda meta: meta.update(fixed_phase_seconds="120"),
                     lambda meta: meta.update(fixed_phase_seconds=float("nan"))]
        for key in ("shipping_fix", "FS_optics_changed", "generated_geometry_gpu_qualified"):
            mutations.extend([lambda meta, key=key: meta.update({key: True}),
                              lambda meta, key=key: meta.update({key: 0}),
                              lambda meta, key=key: meta.pop(key)])
        for i, mutation in enumerate(mutations):
            with self.subTest(mutation=i):
                result = self.invoke(mutate_metadata=mutation)
                self.assertNotEqual(result.returncode, 0, "Unapproved source mode/phase/acceptance flags must not pass")

    def test_synthetic_density_four_public_cli_uses_same_bounded_unaccepted_scope(self):
        result = self.invoke(level=4)
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(observed["fixedDensityLevel"], 4)
        self.assertEqual(observed["qualifiedUnderwaterKnownStagePoints"], 16)
        self.assertEqual(observed["distinctBarycentricTriples"], 16)
        self.assertIs(observed["pngSameFrameAccepted"], False)
        self.assertIs(observed["stageAttachmentQueryObserved"], False)
        self.assertIs(observed["visualQualityAccepted"], False)

    def test_public_cli_rejects_wrong_scope_identity_and_aliased_or_inactive_bindings(self):
        mutations = [lambda raw: raw.update(packName="wrong.zip"),
                     lambda raw: raw.update(packSha256="0" * 64),
                     lambda raw: raw.update(worldId="00000000-0000-0000-0000-000000000000"),
                     lambda raw: raw.update(seed=0),
                     lambda raw: raw.update(expectedProgram=999),
                     lambda raw: raw["samplers"][3].update(textureId=71),
                     lambda raw: raw["samplers"][3].update(unit=3),
                     lambda raw: raw["samplers"][3].update(active=False),
                     lambda raw: raw["samplers"][3].update(actualFormat=34842),
                     lambda raw: raw["stateAfter"].update(binding=999)]
        for i, mutation in enumerate(mutations):
            with self.subTest(mutation=i):
                result = self.invoke(mutate_raw=mutation)
                self.assertNotEqual(result.returncode, 0, "Existing scope/storage/state qualification must remain strict")

    def test_public_cli_rejects_oversized_metadata_and_raw_json_without_writes(self):
        result = self.invoke(mutate_metadata=lambda meta: meta.update(padding="x" * 32769))
        self.assertNotEqual(result.returncode, 0, "Diagnostic metadata decompression must be bounded")
        result = self.invoke(mutate_raw=lambda raw: raw.update(padding="x" * 1048576))
        self.assertNotEqual(result.returncode, 0, "Raw observation JSON reads must be bounded")


if __name__ == "__main__":
    unittest.main(verbosity=2)
