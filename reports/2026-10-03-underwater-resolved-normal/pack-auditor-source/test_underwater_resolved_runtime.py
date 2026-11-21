"""Public CLI tests with synthetic CPU ZIP/readback inputs, not GL evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from test_water_tessellation_runtime import fixture as synthetic_readback


SCRIPT = Path(__file__).with_name("underwater_resolved_runtime.py")
PARENT_SHA = "887c3222f8ea48f244d241444cf90966f4a7ecef866047b803d3b38616d4dc3f"


def metadata():
    return dict(schema="aqualumen-underwater-resolved-probe-v1",
        mode="resolved-normal-atlas", level=4, fixed_phase_seconds=120.0,
        test_only=True, not_shipping=True, shipping_fix=False,
        optical_bandwidth_changed=True, FS_optics_changed=True,
        normal_policy=dict(scope="known-underwater-only", detail=0, parent_detail=1),
        normal_policy_guard="upperSurface && localColumnKnown",
        detail_argument="(underwater?0.0:1.0)", parent_pack_sha256=PARENT_SHA,
        parent_metadata_is_current_optical_policy=False,
        runtime_accepted=False, natural_underwater_accepted=False,
        generated_geometry_gpu_qualified=False, GL_neutrality_verified=False,
        pack_enforces_world_guard=False)


class ResolvedCliTests(unittest.TestCase):
    def invoke(self, mutate_metadata=None, mutate_raw=None, raw_override=None,
               metadata_member="UNDERWATER-RESOLVED-PROBE.json", duplicate_metadata=False):
        with tempfile.TemporaryDirectory(prefix="aqualumen-resolved-cpu-test-") as temporary:
            directory = Path(temporary)
            pack = directory / "Aqualumen-ShoreProbe-world-underwater-resolved-086-phase120-test.zip"
            meta = metadata()
            if mutate_metadata:
                mutate_metadata(meta)
            with ZipFile(pack, "w") as archive:
                archive.writestr(metadata_member, json.dumps(meta))
                if duplicate_metadata:
                    archive.writestr(metadata_member, json.dumps(meta))
            raw = synthetic_readback()
            raw.update(packName=pack.name, packSha256=hashlib.sha256(pack.read_bytes()).hexdigest())
            if mutate_raw:
                mutate_raw(raw)
            if raw_override is not None:
                raw = raw_override
            raw_file = directory / "synthetic-raw.json"
            raw_file.write_text(json.dumps(raw))
            before = {p.name: p.read_bytes() for p in directory.iterdir()}
            result = subprocess.run([sys.executable, "-B", str(SCRIPT), str(raw_file), str(pack)],
                                    capture_output=True, text=True)
            self.assertEqual({p.name: p.read_bytes() for p in directory.iterdir()}, before,
                             "The public read-only auditor must not alter inputs or create files")
            return result

    def test_public_cli_qualifies_resolved_policy_without_render_acceptance(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(observed.get("qualifiedUnderwaterKnownStagePoints"), 16)
        self.assertEqual(observed.get("distinctBarycentricTriples"), 16)
        self.assertEqual(observed.get("fixedDensityLevel"), 4)
        self.assertEqual(observed.get("fixedShaderPhaseSeconds"), 120.0)
        self.assertEqual(observed.get("normalPolicy"), metadata()["normal_policy"])
        self.assertIs(observed.get("analyticNormalBandwidthChanged"), True)
        for key in ("geometryNeutralityAccepted", "generatedGeometryAccepted", "drawCountAccepted",
                    "stageAttachmentQueryObserved", "pngSameFrameAccepted", "pngCausalityAccepted",
                    "normalChangeCausalityAccepted",
                    "visualQualityAccepted", "renderingAccepted", "naturalUnderwaterAccepted",
                    "motionAccepted", "performanceAccepted", "fpsFloorAccepted", "shippingAccepted"):
            self.assertIs(observed.get(key), False, key)

    def test_public_cli_rejects_nonobject_raw_without_private_traceback(self):
        result = self.invoke(raw_override=[])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertRegex(result.stderr, r"\ARejected resolved-normal observation: [A-Za-z]+Error\n\Z")

    def test_public_cli_rejects_parent_policy_wrong_density_phase_or_nonboolean_declarations(self):
        mutations = [lambda m: m.update(schema="aqualumen-water-tessellation-probe-v1"),
                     lambda m: m.update(mode="fixed-density-atlas"),
                     lambda m: m.update(level=1), lambda m: m.update(level=2),
                     lambda m: m.update(level=4.0), lambda m: m.update(level="4"),
                     lambda m: m.update(fixed_phase_seconds=119),
                     lambda m: m.update(fixed_phase_seconds="120"),
                     lambda m: m.update(fixed_phase_seconds=float("nan")),
                     lambda m: m.update(parent_pack_sha256="0"*64),
                     lambda m: m.update(normal_policy_guard="localColumnKnown"),
                     lambda m: m.update(detail_argument="0.0"),
                     lambda m: m["normal_policy"].update(scope="all-water"),
                     lambda m: m["normal_policy"].update(detail=1),
                     lambda m: m["normal_policy"].update(detail=False),
                     lambda m: m["normal_policy"].update(parent_detail=0)]
        for key in ("test_only", "not_shipping", "optical_bandwidth_changed", "FS_optics_changed"):
            mutations.extend([lambda m, key=key: m.update({key: False}),
                              lambda m, key=key: m.update({key: 1})])
        for key in ("shipping_fix", "runtime_accepted", "natural_underwater_accepted",
                    "generated_geometry_gpu_qualified", "GL_neutrality_verified",
                    "pack_enforces_world_guard", "parent_metadata_is_current_optical_policy"):
            mutations.extend([lambda m, key=key: m.update({key: True}),
                              lambda m, key=key: m.pop(key)])
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=index):
                result = self.invoke(mutate_metadata=mutation)
                self.assertNotEqual(result.returncode, 0, "Unapproved normal experiment must not qualify")

    def test_public_cli_keeps_existing_scope_binding_and_state_guards(self):
        mutations = [lambda r: r.update(packName="wrong.zip"),
                     lambda r: r.update(packSha256="0"*64),
                     lambda r: r.update(worldId="00000000-0000-0000-0000-000000000000"),
                     lambda r: r.update(seed=0), lambda r: r.update(scopeAuthorized=False),
                     lambda r: r.update(expectedProgram=999),
                     lambda r: r["samplers"][3].update(unit=3),
                     lambda r: r["samplers"][3].update(textureId=71),
                     lambda r: r["samplers"][3].update(active=False),
                     lambda r: r["samplers"][3].update(type=35664),
                     lambda r: r["samplers"][3].update(actualFormat=34842),
                     lambda r: r["samplers"][3].update(width=2560),
                     lambda r: r["stateAfter"].update(binding=999)]
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=index):
                self.assertNotEqual(self.invoke(mutate_raw=mutation).returncode, 0)

    def test_public_cli_rejects_vacuous_invalid_simplex_nonfinite_or_repeated_selected_points(self):
        def clear_known(raw):
            for p in raw["samplers"][0]["samples"]:
                p["rgba"][3] = 0

        def repeat_coordinates(raw):
            for sampler in raw["samplers"]:
                sampler["samples"][1]["x"] = sampler["samples"][0]["x"]
                sampler["samples"][1]["y"] = sampler["samples"][0]["y"]

        mutations = [clear_known, repeat_coordinates,
                     lambda r: r["samplers"][3]["samples"][0].update(rgba=[.2,.2,.2,1]),
                     lambda r: r["samplers"][3]["samples"][0].update(rgba=[.1,.2,.7,0]),
                     lambda r: r["samplers"][0]["samples"][0].update(rgba=[float("nan"),-1,0,1])]
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=index):
                self.assertNotEqual(self.invoke(mutate_raw=mutation).returncode, 0)

    def test_public_cli_rejects_missing_duplicate_or_oversized_authoritative_inputs(self):
        self.assertNotEqual(self.invoke(metadata_member="WATER-TESSELLATION-PROBE.json").returncode, 0,
                            "Inherited geometry manifest is not the current optical policy")
        self.assertNotEqual(self.invoke(duplicate_metadata=True).returncode, 0)
        self.assertNotEqual(self.invoke(mutate_metadata=lambda m: m.update(padding="x"*32769)).returncode, 0)
        self.assertNotEqual(self.invoke(mutate_raw=lambda r: r.update(padding="x"*1048576)).returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
