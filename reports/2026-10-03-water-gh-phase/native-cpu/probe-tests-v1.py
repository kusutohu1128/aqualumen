"""Public CPU-only construction; never invoke the EGL/GL entry point."""
import json
import os
from pathlib import Path
import subprocess
import struct
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get('WATER_GH_PHASE_PROBE_BINARY', str(
    ROOT/'reports/2026-10-03-water-gh-phase/native-cpu/water-gh-phase-probe-v1')))
PARENT = ROOT/'reports/2026-10-03-water-prepared-iris/cpu-pack/Aqualumen-ShoreProbe-world-sun-prepared-physical-v1.zip'


class GHPhaseConstruction(unittest.TestCase):
    def test_public_cpu_parent_accepts_exact_frozen_prepared_physical_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            with ZipFile(PARENT) as archive:
                archive.extractall(temporary)
            result = subprocess.run([str(BINARY), '--cpu-parent',
                                     str(Path(temporary)/'shaders')],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            evidence = json.loads(result.stdout)
            self.assertFalse(evidence['GLExecuted'])
            self.assertTrue(evidence['parent_sources_pinned'])
            self.assertEqual(evidence['geometry_stage_count'], 3)

    def test_changed_parent_include_rejects_complete_compiled_source_closure(self):
        with tempfile.TemporaryDirectory() as temporary:
            with ZipFile(PARENT) as archive:
                archive.extractall(temporary)
            root = Path(temporary)/'shaders'
            include = root/'lib/caustics.glsl'
            include.write_bytes(include.read_bytes()+b'// modified actual included source\n')
            result = subprocess.run([str(BINARY), '--cpu-parent', str(root)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('expanded physical parent source pin differs', result.stderr)

    def test_native_entry_rejects_existing_output_before_source_or_GL_actions(self):
        with tempfile.TemporaryDirectory() as temporary:
            sentinel = Path(temporary)/'preserved.txt'
            sentinel.write_bytes(b'untouched')
            result = subprocess.run([str(BINARY), 'absent-parent', 'absent-zero',
                                     'absent-45', temporary],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('NEW output required', result.stderr)
            self.assertEqual(sentinel.read_bytes(), b'untouched')

    def test_public_readback_preserves_same_draw_C0_copy_and_raw_admissions(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'synthetic-eight-slots.f32'
            values = [1, 2, 3, 1, 0, 0, 0, 0, 1, 1, 12585984, 0,
                      15, 1, 2, -1, .2, .3, .5, 1,
                      1, 1, .8, 0, 1, 1, .8, 0, 1, 2, 3, 1]
            path.write_bytes(struct.pack('<32f', *values))
            result = subprocess.run([str(BINARY), '--cpu-readback', str(path), '1', '1'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            evidence = json.loads(result.stdout)
            self.assertTrue(evidence['syntheticOnly'])
            self.assertTrue(evidence['same_draw_copy_exact'])
            self.assertEqual(evidence['full_WR_valid_applied'], [1, 1])
            self.assertEqual(evidence['base_WR_valid_applied'], [1, 1])

    def test_public_physical_phase_contract_changes_only_whitened_node_rotation(self):
        from water_gh_phase_pack import build_pack
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with ZipFile(PARENT) as archive:
                archive.extractall(directory/'parent')
            roots = [str(directory/'parent/shaders')]
            for phase in (0, 45):
                pack = directory/f'Aqualumen-ShoreProbe-world-gh-phase-{phase}-physical-v1.zip'
                build_pack(PARENT, phase, 'physical', pack)
                with ZipFile(pack) as archive:
                    archive.extractall(directory/str(phase))
                roots.append(str(directory/str(phase)/'shaders'))
            result = subprocess.run([str(BINARY), '--cpu-physical-phase', *roots],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            evidence = json.loads(result.stdout)
            self.assertFalse(evidence['GLExecuted'])
            self.assertTrue(evidence['phase0_literal_original_expression'])
            self.assertTrue(evidence['phase45_only_pre_Cholesky_rotation'])

    def test_public_diagnostic_contract_recovers_each_actual_physical_phase(self):
        from water_gh_phase_pack import build_pack
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with ZipFile(PARENT) as archive:
                archive.extractall(directory/'parent')
            roots = [str(directory/'parent/shaders')]
            for phase in (0, 45):
                pack = directory/f'Aqualumen-ShoreProbe-world-gh-phase-{phase}-diagnostic-v1.zip'
                build_pack(PARENT, phase, 'diagnostic', pack)
                with ZipFile(pack) as archive:
                    archive.extractall(directory/str(phase))
                roots.append(str(directory/str(phase)/'shaders'))
            result = subprocess.run([str(BINARY), '--cpu-contract', *roots],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            evidence = json.loads(result.stdout)
            self.assertFalse(evidence['GLExecuted'])
            self.assertTrue(evidence['observer_recovers_each_phase_exact'])
            self.assertEqual(evidence['actual_water_draw_targets'], [0, 9, 10, 11, 12, 13, 14, 15])

    def test_mutated_passive_snapshot_rejects_even_if_tag_erasure_recovers_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with ZipFile(PARENT) as archive:
                archive.extractall(directory/'parent')
            roots = [str(directory/'parent/shaders')]
            for phase in (0, 45):
                pack = ROOT/'reports/2026-10-03-water-gh-phase/cpu-pack'/f'Aqualumen-ShoreProbe-world-gh-phase-{phase}-diagnostic-v1.zip'
                with ZipFile(pack) as archive:
                    archive.extractall(directory/str(phase))
                roots.append(str(directory/str(phase)/'shaders'))
            helper = Path(roots[1])/'lib/water_residual_sun.glsl'
            value = helper.read_bytes()
            self.assertEqual(value.count(b'    WGP_fullWR=WGP_readLegacyStatus();\n'), 1)
            helper.write_bytes(value.replace(b'    WGP_fullWR=WGP_readLegacyStatus();\n',
                                            b'    WGP_fullWR=vec4(0.0);\n'))
            result = subprocess.run([str(BINARY), '--cpu-contract', *roots],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('passive Sun status snapshot source differs', result.stderr)

    def test_signed_zero_difference_rejects_same_draw_copy_not_float_equality(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'synthetic-eight-slots.f32'
            values = [0, 2, 3, 1, 0, 0, 0, 0, 1, 1, 12585984, 0,
                      15, 1, 2, -1, .2, .3, .5, 1,
                      1, 1, .8, 0, 1, 1, .8, 0, -0.0, 2, 3, 1]
            path.write_bytes(struct.pack('<32f', *values))
            result = subprocess.run([str(BINARY), '--cpu-readback', str(path), '1', '1'],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('same-draw observation contract rejected', result.stderr)


if __name__ == '__main__':
    unittest.main()
