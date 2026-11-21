"""Public saved-output CLI tests; generated fixtures are synthetic, never GL."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'tools/water_sun_prepared_timing.py'
FIXTURES = (
    'central2-cachezero-guard0', 'central2-cachezero-guard1',
    'central2-cachepositive-guard0', 'central2-cachepositive-guard1',
    'wide60-cachepositive-guard1', 'wide90-cachepositive-guard1')
MODES = ('old', 'prepared')
HEADER = ['fixture', 'stage', 'cycle', 'position', 'variant', 'elapsed_ns']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(data, indent=2) + '\n').encode()
    path.write_bytes(raw)
    return sha(raw)


def packet(directory):
    sources = []
    physical = {}
    geometry = []
    for stage in range(3):
        name = f'geometry-stage{stage}.glsl'
        raw = f'// synthetic geometry {stage}\n'.encode()
        (directory / name).write_bytes(raw)
        sources.append({'file': name, 'sha256': sha(raw), 'bytes': len(raw)})
        geometry.append({'type': [35633, 36488, 36487][stage],
                         'bytes': len(raw), 'sha256': sha(raw)})
    for mode in MODES:
        name = f'{mode}-physical-expanded.fsh'
        raw = f'// synthetic {mode} physical source\n'.encode()
        (directory / name).write_bytes(raw)
        physical[mode] = sha(raw)
        sources.append({'file': name, 'sha256': sha(raw), 'bytes': len(raw)})
    manifest = {'schema': 'aqualumen-prepared-main-source-v1', 'sources': sources}
    manifest_sha = write_json(directory / 'source-manifest.json', manifest)
    csv_text = io.StringIO(newline='')
    writer = csv.writer(csv_text, lineterminator='\n')
    writer.writerow(HEADER)
    states, timer_inputs, cases = [], [], []
    for fixture in FIXTURES:
        guard = int(fixture.endswith('guard1'))
        aperture = 90 if fixture.startswith('wide90') else 60 if fixture.startswith('wide60') else 2
        cases.append({'path': fixture, 'guard': guard,
                      'positive_cache': 'cachepositive' in fixture,
                      'aperture_degrees': aperture, 'qualified': True, 'accepted': True})
        entries = []
        queried = []
        for mode in MODES:
            program = 20 if mode == 'old' else 30
            parent = directory / fixture / f'timer-{mode}-actual-inputs'
            parent.mkdir(parents=True)
            samplers, payload = [], b''
            for unit in range(8):
                data = struct.pack('<f', 1.0 + unit)
                filename = f'input-sampler{unit}.f32'
                (parent / filename).write_bytes(data)
                payload += data
                samplers.append({'unit': unit, 'file': filename,
                                 'width': 1, 'height': 1, 'components': 1})
            receipt = {'schema': 'aqualumen-native-residual-sun-inputs-v1',
                       'program': program, 'currentProgramBefore': program,
                       'currentProgramAfter': program, 'stateRestored': True,
                       'activeTextureBefore': 33984, 'activeTextureAfter': 33984,
                       'textureBindingBefore': 1, 'textureBindingAfter': 1,
                       'matrices': {'gbufferProjection': [1.0] * 16},
                       'samplers': samplers}
            receipt_sha = write_json(parent / 'actual-inputs.json', receipt)
            write_json(parent / 'timer-guard.json', {
                'schema': 'aqualumen-native-sun-iris-guard-input-v1',
                'program': program, 'currentProgramBefore': program,
                'currentProgramAfter': program, 'name': 'aqualumenSunTestAuthorized',
                'type': 5124, 'size': 1, 'value': guard})
            entries.append({'variant': mode, 'receipt': str((parent / 'actual-inputs.json').relative_to(directory)),
                            'receipt_sha256': receipt_sha, 'texture_payload_sha256': sha(payload)})
            queried.append({'program': program, 'currentProgramBefore': program,
                            'currentProgramAfter': program,
                            'stages': [*geometry, {'type': 35632, 'sha256': physical[mode],
                                       'bytes': (directory / f'{mode}-physical-expanded.fsh').stat().st_size}]})
        timer_inputs.append({'fixture': fixture, 'actual_inputs': entries,
                             'queried_program_sources': queried})
        for stage, cycles in [('warmup', 1), ('measured', 2)]:
            for cycle in range(cycles):
                for position, mode in enumerate(('old', 'prepared', 'prepared', 'old')):
                    ns = 99000000 if stage == 'warmup' else (1000000 + cycle * 100000)
                    if mode == 'prepared':
                        ns //= 2
                    writer.writerow([fixture, stage, cycle, position, mode, ns])
                    entry = entries[MODES.index(mode)]
                    program = 20 if mode == 'old' else 30
                    states.append({'program': program, 'currentProgramBefore': program,
                                   'currentProgramAfter': program, 'framebuffer': 2,
                                   'viewport': [0, 0, 257, 257], 'VAO': 3,
                                   'patchVertices': 3, 'drawBuffers': [36064, 36065, 36066, 36067, 36068, 0, 0, 0],
                                   'guard': {'name': 'aqualumenSunTestAuthorized', 'type': 5124, 'size': 1,
                                             'location': 7, 'actualBefore': guard, 'actualAfter': guard},
                                   'actual_input_receipt_sha256': entry['receipt_sha256'],
                                   'actual_texture_payload_sha256': entry['texture_payload_sha256'],
                                   'queried_fragment_source_sha256': physical[mode],
                                   'counterBits': 64, 'elapsed_ns': ns, 'stateUnchanged': True})
    raw_csv = csv_text.getvalue().encode()
    (directory / 'draw-timer.csv').write_bytes(raw_csv)
    state_sha = write_json(directory / 'draw-timer-state.json', states)
    write_json(directory / 'draw-timer-inputs.json', timer_inputs)
    result = {'schema': 'aqualumen-prepared-main-native-v1', 'syntheticOnly': True,
              'nativeGLExecuted': True, 'renderer': 'NVIDIA GeForce RTX 3080 Ti',
              'vendor': 'NVIDIA Corporation', 'status': 'PASS', 'accepted': True,
              'main_fixture_qualified': True, 'main_differential_accepted': True,
              'source_manifest_sha256': manifest_sha, 'cases': cases,
              'timer': {'executed': True, 'query': 'GL_TIME_ELAPSED', 'counterBits': 64,
                        'alternation': 'ABBA old/prepared/prepared/old',
                        'warmup_cycles': 1, 'measurement_cycles': 2,
                        'samples_per_variant_per_fixture': 4,
                        'raw_integer_ns_file': 'draw-timer.csv', 'state_file': 'draw-timer-state.json',
                        'raw_csv_sha256': sha(raw_csv), 'state_sha256': state_sha,
                        'Minecraft_FPS': False}}
    write_json(directory / 'result.json', result)
    return result


def run(directory):
    return subprocess.run([sys.executable, '-B', str(CLI), str(directory)],
                          capture_output=True, text=True)


class Timing(unittest.TestCase):
    def test_public_cli_rejects_one_changed_framebuffer_or_vao_despite_updated_state_hash(self):
        for field in ('framebuffer', 'VAO'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                result = packet(directory)
                states = json.loads((directory / 'draw-timer-state.json').read_text())
                states[13][field] += 1
                result['timer']['state_sha256'] = write_json(directory / 'draw-timer-state.json', states)
                write_json(directory / 'result.json', result)
                output = run(directory)
                self.assertNotEqual(output.returncode, 0)
                self.assertFalse(json.loads(output.stderr)['timingEvidenceQualified'])

    def test_public_cli_fails_closed_for_missing_pending_or_noncanonical_timing(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertNotEqual(run(Path(temporary)).returncode, 0)
        for mutation in ('pending', 'sample-count', 'fixture-order', 'ABBA',
                         'warmup-order', 'fractional-ns', 'CSV-hash', 'duplicate-json'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                data = packet(directory)
                csv_path = directory / 'draw-timer.csv'
                if mutation == 'pending':
                    data['timer']['executed'] = False
                elif mutation == 'sample-count':
                    data['timer']['samples_per_variant_per_fixture'] = 3
                elif mutation == 'fixture-order':
                    data['cases'][0], data['cases'][1] = data['cases'][1], data['cases'][0]
                elif mutation in ('ABBA', 'warmup-order', 'fractional-ns'):
                    rows = list(csv.reader(io.StringIO(csv_path.read_text())))
                    if mutation == 'ABBA':
                        rows[2][4] = 'old'
                    elif mutation == 'warmup-order':
                        rows[1][1] = 'measured'
                    else:
                        rows[1][-1] = '99000000.0'
                    text = io.StringIO(newline='')
                    csv.writer(text, lineterminator='\n').writerows(rows)
                    csv_path.write_text(text.getvalue())
                    data['timer']['raw_csv_sha256'] = sha(csv_path.read_bytes())
                elif mutation == 'CSV-hash':
                    data['timer']['raw_csv_sha256'] = '0' * 64
                write_json(directory / 'result.json', data)
                if mutation == 'duplicate-json':
                    raw = (directory / 'result.json').read_text()
                    (directory / 'result.json').write_text(raw.replace('{', '{"status":"RED",', 1))
                output = run(directory)
                self.assertNotEqual(output.returncode, 0)
                self.assertFalse(json.loads(output.stderr)['timingEvidenceQualified'])

    def test_public_cli_rejects_input_receipt_payload_program_and_source_query_mismatch(self):
        for mutation in ('receipt-hash', 'payload', 'receipt-program', 'guard', 'source-query'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                packet(directory)
                path = directory / FIXTURES[0] / 'timer-old-actual-inputs'
                inputs = json.loads((directory / 'draw-timer-inputs.json').read_text())
                if mutation == 'receipt-hash':
                    inputs[0]['actual_inputs'][0]['receipt_sha256'] = '0' * 64
                elif mutation == 'payload':
                    (path / 'input-sampler0.f32').write_bytes(struct.pack('<f', 99.0))
                elif mutation == 'receipt-program':
                    receipt = json.loads((path / 'actual-inputs.json').read_text())
                    receipt['program'] = 999
                    inputs[0]['actual_inputs'][0]['receipt_sha256'] = write_json(path / 'actual-inputs.json', receipt)
                elif mutation == 'guard':
                    guard = json.loads((path / 'timer-guard.json').read_text())
                    guard['value'] = 1
                    write_json(path / 'timer-guard.json', guard)
                else:
                    inputs[0]['queried_program_sources'][0]['stages'][-1]['sha256'] = '0' * 64
                write_json(directory / 'draw-timer-inputs.json', inputs)
                result = run(directory)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(json.loads(result.stderr)['timingEvidenceQualified'])

    def test_public_cli_rejects_chronological_guard_program_source_and_draw_state_tampering(self):
        mutations = [
            lambda state: state['guard'].__setitem__('actualBefore', 1),
            lambda state: state.__setitem__('queried_fragment_source_sha256', '0' * 64),
            lambda state: state.__setitem__('currentProgramBefore', 999),
            lambda state: state.__setitem__('counterBits', 32),
            lambda state: state.__setitem__('stateUnchanged', False),
            lambda state: state['drawBuffers'].__setitem__(5, 36069),
            lambda state: state.__setitem__('program', True),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutations.index(mutation)), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                result = packet(directory)
                state = json.loads((directory / 'draw-timer-state.json').read_text())
                mutation(state[0])
                result['timer']['state_sha256'] = write_json(directory / 'draw-timer-state.json', state)
                write_json(directory / 'result.json', result)
                output = run(directory)
                self.assertNotEqual(output.returncode, 0)
                self.assertFalse(json.loads(output.stderr)['timingEvidenceQualified'])

    def test_public_cli_reports_measured_medians_and_paired_cycles_not_warmup(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            packet(directory)
            result = run(directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data['syntheticOnly'])
            self.assertFalse(data['nativeTimerQualified'])
            self.assertFalse(data['MinecraftFPS'])
            self.assertFalse(data['universalSpeedupAccepted'])
            self.assertEqual(len(data['fixtures']), 6)
            for item in data['fixtures']:
                self.assertAlmostEqual(item['old']['median_ms'], 1.05)
                self.assertAlmostEqual(item['prepared']['median_ms'], .525)
                self.assertEqual(item['prepared_over_old_median_ratio'], .5)
                self.assertEqual(item['paired_cycle_prepared_over_old_ratios'], [.5, .5])
                self.assertEqual(item['measured_samples_per_variant'], 4)


if __name__ == '__main__':
    unittest.main()
