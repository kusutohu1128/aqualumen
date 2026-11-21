"""Public CPU-only source construction. No EGL/GL entry point is executed."""
import json
import os
from pathlib import Path
import subprocess
import struct
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get('WATER_SUN_PREPARED_MAIN_BINARY', str(
    ROOT / 'reports/2026-10-03-water-prepared/cpu-main/water-sun-prepared-main-probe')))
FROZEN = ROOT / 'reports/2026-10-03-water-sun-support/cpu-pack'
PREPARED = ROOT / 'tools/water_sun_prepared.glsl'


def extract_sources(directory):
    roots = []
    for mode, role in [('reject', 'reasons'), ('zero', 'reasons'),
                       ('reject', 'inputs'), ('zero', 'inputs')]:
        target = directory / (mode + '-' + role)
        name = f'Aqualumen-ShoreProbe-world-sun-support-{mode}-{role}-v1.zip'
        with ZipFile(FROZEN / name) as archive:
            archive.extractall(target)
        roots.append(str(target / 'shaders'))
    return roots


class PreparedMainConstruction(unittest.TestCase):
    def test_public_actual_main_construction_is_reversible_without_gl(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            roots = extract_sources(directory)
            output = directory / 'generated'
            result = subprocess.run([str(BINARY), '--cpu-contract', *roots,
                                     str(PREPARED), str(output)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertFalse(data['GLExecuted'])
            self.assertTrue(data['prepared_recovers_old_exact'])
            self.assertTrue(data['all48_observer_recovers_physical_exact'])
            self.assertEqual(data['cap_context_declarations'], 1)
            self.assertEqual(data['node_class_call_sites'], 1)
            self.assertFalse(data['invalid_context_shortcut'])
            for role in ['physical', 'reasons', 'inputs', 'all48']:
                old = (output / f'old-{role}-expanded.fsh').read_text()
                new = (output / f'prepared-{role}-expanded.fsh').read_text()
                self.assertIn('int WSP_supportClass=waterSunSupportClass(viewToEye,target,eta);', old)
                self.assertIn('waterSunSupportClassPrepared(WPM_viewContext,target);', new)
            self.assertNotIn('WPM_requestedNode',
                             (output / 'prepared-physical-expanded.fsh').read_text())
            # Public recoverable host-source call plan, not a simulated GL
            # uniform-value test. Actual typed values are still root-run gates.
            host = (output / 'host-sources/water_sun_prepared_main_probe.cpp').read_text()
            for role in [0, 3]:
                self.assertRegex(host,
                    rf'prior::setGuard\(fixture,programs\.value\[mode\]\[{role}\],scenario\.guard\);\s+'
                    rf'const auto values=sun::snapshotInputs\(fixture,programs\.value\[mode\]\[{role}\],')

    def test_raw_comparison_preserves_signed_zero_and_every_binary32_bit(self):
        with tempfile.TemporaryDirectory() as temporary:
            a, b = Path(temporary) / 'a.f32', Path(temporary) / 'b.f32'
            a.write_bytes(struct.pack('<4f', 0.0, 1.0, 2.0, 3.0))
            for values, accepted in [((0.0, 1.0, 2.0, 3.0), True),
                                     ((-0.0, 1.0, 2.0, 3.0), False),
                                     ((0.0, 1.0000001192092896, 2.0, 3.0), False)]:
                b.write_bytes(struct.pack('<4f', *values))
                result = subprocess.run([str(BINARY), '--cpu-raw-equal', str(a), str(b)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, accepted, result.stderr)
                self.assertFalse(json.loads(result.stdout)['GLExecuted'])

    def test_cpu_synthetic_gate_never_becomes_actual_gpu_proof(self):
        data = {
            'schema': 'aqualumen-prepared-node-native-v1', 'syntheticOnly': True,
            'nativeGLExecuted': True, 'renderer': 'NVIDIA GeForce RTX 3080 Ti',
            'vendor': 'NVIDIA Corporation',
            'status': 'PASS', 'accepted': True, 'count': 376,
            'frozenCount': 344, 'additionalCount': 32,
            'roles': ['old', 'wrapper', 'reused'],
            'sourceSHA256': {
                'old': 'f9aa1c6763065f776d26b46385ecf82c2b16ac171783b19fa2353de1cef4be7a',
                'prepared': 'ab88da48dee42c15a1cfd61514cad75c061a2d1841a15bfbbce21871b9b81441',
                'corpus': '24fdd6ed4ab983a99207883a22ec3b8140fc2aa3fbe364a023308a3b95916e48',
                'utilities': 'f183963ee155c89dcbd8be3e36ccd7d313ccadccde4d1d9bb5b4c2ab16ae16f7',
                'fixtureSource': 'f4abe4cbde553c44258e2c2f2f9e437809f67af9c350823ac4627dcfb1a5bb67'},
            'physicalOracleForAdditional': False,
        }
        checks = ['rawInputEchoExact', 'classesEqual', 'matchesLiteralCPUClass',
                  'allSixIntervalTriplesEqual', 'contextValidEqual',
                  'groupChecksumsEqual', 'repeatByteIdentical',
                  'additionalMatchesLiteralCPUCases']
        data.update({key: True for key in checks})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'synthetic-gate.json'
            for changed in [None, *checks, 'candidate_sha', 'renderer', 'count']:
                mutated = json.loads(json.dumps(data))
                if changed in checks:
                    mutated[changed] = False
                elif changed == 'candidate_sha':
                    mutated['sourceSHA256']['prepared'] = '0' * 64
                elif changed == 'renderer':
                    mutated['renderer'] = 'software renderer'
                elif changed == 'count':
                    mutated['count'] = 375
                path.write_text(json.dumps(mutated))
                result = subprocess.run([str(BINARY), '--cpu-gate-synthetic', str(path)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, changed is None, result.stderr)
                if changed is None:
                    self.assertFalse(json.loads(result.stdout)['native_gate_accepted'])
                actual = subprocess.run([str(BINARY), '--cpu-gate', str(path)],
                                        capture_output=True, text=True)
                self.assertNotEqual(actual.returncode, 0)

    def test_timer_options_are_bounded_without_running_timer(self):
        for warmup, measurement, seconds, accepted in [
                (2, 6, 900, True), (0, 6, 900, False), (2, 0, 900, False),
                (5, 6, 900, False), (2, 13, 900, False), (2, 6, 3601, False)]:
            result = subprocess.run([str(BINARY), '--cpu-timer-options', str(warmup),
                                     str(measurement), str(seconds)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode == 0, accepted, result.stderr)
            if accepted:
                data = json.loads(result.stdout)
                self.assertFalse(data['GLExecuted'])
                self.assertEqual(data['measured_draws_per_variant_per_fixture'], 12)

    def test_changed_helper_is_rejected_before_any_output_or_gl(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            roots = extract_sources(directory)
            changed = directory / 'changed.glsl'
            changed.write_bytes(PREPARED.read_bytes() + b'// not the pinned candidate\n')
            output = directory / 'must-not-exist'
            result = subprocess.run([str(BINARY), '--cpu-contract', *roots,
                                     str(changed), str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('prepared literal helper pin differs', result.stderr)
            self.assertFalse(output.exists())

    def test_native_existing_output_rejects_before_gate_source_or_gl(self):
        with tempfile.TemporaryDirectory() as temporary:
            marker = Path(temporary) / 'preserved.txt'
            marker.write_text('untouched')
            result = subprocess.run([str(BINARY), '--native', *(['absent'] * 4),
                                     'absent', temporary, '--node-gate-result', 'absent'],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('NEW output required', result.stderr)
            self.assertEqual(marker.read_text(), 'untouched')

    def test_malformed_duplicate_or_trailing_gate_json_rejects_without_gl(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'malformed.json'
            for raw in ['{"schema":"a","schema":"b"}', '{} trailing',
                        '{"number":NaN}', '{"number":01}', '{"number":1.}']:
                path.write_text(raw)
                result = subprocess.run([str(BINARY), '--cpu-gate', str(path)],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
