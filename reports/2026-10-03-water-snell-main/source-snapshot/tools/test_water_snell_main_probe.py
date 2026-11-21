"""Public CPU contracts only; this test never invokes the GL execution mode."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import struct
import unittest
from zipfile import ZipFile

from water_snell_main_pack import build_pack

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get('SNELL_MAIN_PROBE_BINARY', str(
    ROOT/'reports/2026-10-03-water-snell-main/cpu-native/water-snell-main-probe')))


class PublicMainConstruction(unittest.TestCase):
    def test_four_actual_pack_roles_recover_same_variant_physical_main(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = []
            for mode,observe in [('old','reasons'),('stable','reasons'),('old','inputs'),('stable','inputs')]:
                directory = Path(temporary)/(mode+'-'+observe)
                archive = build_pack(ROOT,directory.with_suffix('.zip'),mode,observe)
                with ZipFile(archive) as packed:
                    packed.extractall(directory)
                paths.append(str(directory/'shaders'))
            result = subprocess.run([str(BINARY),'--cpu-contract',*paths],text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['schema'],'aqualumen-snell-main-construction-v1')
            self.assertFalse(report['GLExecuted'])
            self.assertTrue(report['observer_recovers_variant_physical_exact'])
            self.assertTrue(report['stable_restores_old_math_exact'])
            self.assertEqual(report['roles'],['physical','reasons','inputs'])

    def test_public_readback_distinguishes_no_target_from_same_draw_first_failure(self):
        # Synthetic binary32 payloads test the observation contract, not a shader.
        accepted = [0,-1,0,1, 0,-1,0,1, .007,.002,.003,15, 0,0,0,0,
                    0,0,0,0, 1,1,0,0]
        rejected = accepted[:]
        rejected[12:16] = [0,1,0,64*3+1]
        rejected[16:20] = [3,48,0,0]
        rejected[20:24] = [1,0,0,48]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'payload.f32'
            for values,label in [(accepted,'NO_FAILED_TARGET_OBSERVED'),(rejected,'FIRST_FAILED_TARGET_OBSERVED')]:
                path.write_bytes(struct.pack('<24f',*values))
                result = subprocess.run([str(BINARY),'--cpu-readback',str(path),'1','1'],
                                        text=True,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout)['observation'],label)

    def test_public_readback_rejects_mismatched_first_reason_and_nonfinite_inputs(self):
        payload = [0,-1,0,1, 0,-1,0,1, .007,.002,.003,15, 0,1,0,64*3+1,
                   3,48,0,0, 1,0,0,48]
        cases = []
        mismatch = payload[:]
        mismatch[15] = 64*4+1
        cases.append(mismatch)
        not_finite = payload[:]
        not_finite[4] = float('nan')
        cases.append(not_finite)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'payload.f32'
            for values in cases:
                path.write_bytes(struct.pack('<24f',*values))
                result = subprocess.run([str(BINARY),'--cpu-readback',str(path),'1','1'],
                                        text=True,capture_output=True)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('contract rejected',result.stderr)

    def test_full_mode_rejects_existing_output_before_any_gl_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            sentinel = directory/'preserved.txt'
            sentinel.write_text('untouched')
            result = subprocess.run([str(BINARY),*(['missing']*4),str(directory)],
                                    text=True,capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('NEW output required',result.stderr)
            self.assertEqual(sentinel.read_text(),'untouched')

    def test_changed_included_node_rejects_even_when_original_archive_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = []
            for mode,observe in [('old','reasons'),('stable','reasons'),('old','inputs'),('stable','inputs')]:
                directory = Path(temporary)/(mode+'-'+observe)
                archive = build_pack(ROOT,directory.with_suffix('.zip'),mode,observe)
                with ZipFile(archive) as packed:
                    packed.extractall(directory)
                paths.append(str(directory/'shaders'))
                if mode=='stable':
                    node = directory/'shaders/lib/water_snell_inverse.glsl'
                    node.write_bytes(node.read_bytes()+b'// altered included module\n')
            result = subprocess.run([str(BINARY),'--cpu-contract',*paths],text=True,capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('adapted stable module',result.stderr)


if __name__=='__main__':
    unittest.main()
