"""Public synthetic CPU contracts, never actual Iris or shader evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from test_water_sun_support_runtime import support_fixture

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).with_name('water_sun_prepared_runtime.py')
PACKS = ROOT / 'reports/2026-10-03-water-prepared-iris/cpu-pack'


def fixture(directory, role='reasons'):
    raw_file, _, guard_file = support_fixture(directory, mode='zero', observe=role)
    name = f'Aqualumen-ShoreProbe-world-sun-prepared-{role}-v1.zip'
    pack = directory / name
    pack.write_bytes((PACKS / name).read_bytes())
    identity = dict(packName=name, packSha256=hashlib.sha256(pack.read_bytes()).hexdigest())
    for path in (raw_file, guard_file):
        value = json.loads(path.read_text())
        value.update(identity)
        path.write_text(json.dumps(value))
    if role == 'reasons':
        raw = json.loads(raw_file.read_text())
        for i in range(16):
            raw['samplers'][1]['samples'][i]['rgba'][2] = 64 * 48 + 262144 * 48
        raw_file.write_text(json.dumps(raw))
    return raw_file, pack, guard_file


class PreparedRuntime(unittest.TestCase):
    def invoke(self, role='reasons', change=None):
        with tempfile.TemporaryDirectory(prefix='prepared-runtime-synthetic-') as temporary:
            directory = Path(temporary)
            paths = fixture(directory, role)
            if change:
                change(paths)
            before = {p.name: p.read_bytes() for p in directory.iterdir()}
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), *map(str, paths)],
                                    text=True, capture_output=True)
            self.assertEqual(before, {p.name: p.read_bytes() for p in directory.iterdir()})
            return result

    def test_new_source_identity_preserves_valid_negative_reason_gate(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['schema'], 'aqualumen-water-sun-prepared-runtime-v1')
        self.assertEqual(report['role'], 'reasons')
        self.assertEqual(report['selectedPoints'], 16)
        self.assertTrue(report['sourceRecoveryQualified'])
        self.assertTrue(report['readbackQualified'])
        self.assertEqual(report['qualifiedAppliedPoints'], 2)
        self.assertEqual(report['minimumQualifiedAppliedPoints'], 4)
        self.assertEqual(report['applicationVerdict'], 'NEGATIVE_INSUFFICIENT_APPLICATION')
        self.assertEqual(report['certificateCounts']['support'], 768)
        self.assertFalse(report['operatorActiveQualified'])
        self.assertFalse(report['physicalAccepted'])
        self.assertFalse(report['sameFrameProven'])

    def test_input_roles_keep_first_target_not_tes_or_application(self):
        result = self.invoke(role='inputs')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['role'], 'inputs')
        self.assertEqual(report['recordedFirstTargets'], 16)
        self.assertEqual(report['firstReasonHistogram']['4'], 16)
        self.assertEqual(report['firstTargetExactSupportClasses'], {'1': 16})
        self.assertTrue(report['inputEvidenceQualified'])
        self.assertFalse(report['TESObserved'])
        self.assertFalse(report['applicationObserved'])
        self.assertFalse(report['certificateCountsCollected'])
        self.assertFalse(report['all48RawInputsObserved'])

    def test_minimum_four_is_not_waived_by_prepared_source_recovery(self):
        for count in (3, 4):
            def change(paths):
                raw = json.loads(paths[0].read_text())
                for i in range(16):
                    raw['samplers'][0]['samples'][i]['rgba'] = [0, 0, 0, 0] if i < count else [3, 48, 0, 0]
                    raw['samplers'][1]['samples'][i]['rgba'][1] = 1 if i < count else 0
                    raw['samplers'][1]['samples'][i]['rgba'][3] = 0 if i < count else 48
                paths[0].write_text(json.dumps(raw))
            result = self.invoke(change=change)
            self.assertEqual(result.returncode, 1 if count == 3 else 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['qualifiedAppliedPoints'], count)
            self.assertEqual(report['operatorActiveQualified'], count == 4)
            self.assertEqual(report['minimumQualifiedAppliedPoints'], 4)
            self.assertFalse(report['physicalAccepted'])
            self.assertFalse(report['performanceAccepted'])

    def test_rehashed_helper_metadata_or_unrelated_member_cannot_hide_source_changes(self):
        for member in ('shaders/lib/water_sun_support.glsl', 'shaders/lib/water_residual_sun.glsl',
                       'shaders/gbuffers_water.tes', 'shaders/final.fsh', 'WATER-SUN-PREPARED.json'):
            def change(paths):
                with ZipFile(paths[1]) as archive:
                    files = {n: archive.read(n) for n in archive.namelist()}
                if member.endswith('.json'):
                    metadata = json.loads(files[member])
                    metadata['visual_accepted'] = True
                    files[member] = json.dumps(metadata).encode()
                else:
                    files[member] += b'// synthetic tampered member\n'
                    metadata = json.loads(files['WATER-SUN-PREPARED.json'])
                    if member in metadata['current_sha256']:
                        metadata['current_sha256'][member] = hashlib.sha256(files[member]).hexdigest()
                    files['WATER-SUN-PREPARED.json'] = json.dumps(metadata).encode()
                with ZipFile(paths[1], 'w') as archive:
                    for name, content in files.items():
                        archive.writestr(name, content)
                for path in (paths[0], paths[2]):
                    value = json.loads(path.read_text())
                    value['packSha256'] = hashlib.sha256(paths[1].read_bytes()).hexdigest()
                    path.write_text(json.dumps(value))
            with self.subTest(member=member):
                result = self.invoke(change=change)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, '')
                self.assertIn('Rejected prepared Sun observation:', result.stderr)

    def test_physical_display_is_explicitly_not_a_final_readback_contract(self):
        from water_sun_prepared_runtime import audit
        with tempfile.TemporaryDirectory(prefix='prepared-physical-synthetic-') as temporary:
            directory = Path(temporary)
            name = 'Aqualumen-ShoreProbe-world-sun-prepared-physical-v1.zip'
            pack = directory / name
            pack.write_bytes((PACKS / name).read_bytes())
            before = pack.read_bytes()
            with self.assertRaisesRegex(ValueError, 'Physical FINAL has no qualified selected telemetry'):
                audit(directory / 'missing-raw.json', pack, directory / 'missing-guard.json')
            self.assertEqual(pack.read_bytes(), before)

    def test_saved_identity_binding_state_and_guard_fail_closed_without_dropping_points(self):
        mutations = [
            (0, lambda r: r.update(packSha256='0' * 64)),
            (0, lambda r: r.update(worldId='0' * 36)),
            (0, lambda r: r['samplers'][1].update(textureId=r['samplers'][0]['textureId'])),
            (0, lambda r: r['samplers'][0].update(type=5124)),
            (0, lambda r: r['samplers'][2].update(actualFormat=34842)),
            (0, lambda r: r['samplers'][0]['samples'][1].update(x=801, y=451)),
            (0, lambda r: r['samplers'][0]['samples'][0].update(rgba=[float('nan'), 0, 0, 0])),
            (0, lambda r: r['stateAfter'].update(binding=999)),
            (2, lambda g: g['uniform'].update(value=0)),
            (2, lambda g: g['uniform'].update(type=5126)),
            (2, lambda g: g.update(frameAfter=g['frameBefore'] + 1)),
            (2, lambda g: g.update(benchmarkState='sampling'))]
        for index, (path_index, mutation) in enumerate(mutations):
            def change(paths):
                value = json.loads(paths[path_index].read_text())
                mutation(value)
                paths[path_index].write_text(json.dumps(value))
            with self.subTest(index=index):
                result = self.invoke(change=change)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, '')
                self.assertIn('Rejected prepared Sun observation:', result.stderr)

    def test_zero_and_unknown_counts_keep_original_whole_rejection_accounting(self):
        for word in (48 + 262144 * 48, 64 * 47 + 4096 + 262144 * 48):
            def change(paths):
                raw = json.loads(paths[0].read_text())
                # This selected point remains rejected hemisphere48: neither
                # absent48+rejected48 nor unknown1+other0 is valid accounting.
                raw['samplers'][1]['samples'][2]['rgba'][2] = word
                paths[0].write_text(json.dumps(raw))
            result = self.invoke(change=change)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, '')
            self.assertIn('Rejected prepared Sun observation:', result.stderr)

    def test_input_zero_target_is_no_observed_failure_not_continuous_zero(self):
        def change(paths):
            raw = json.loads(paths[0].read_text())
            for point in raw['samplers'][3]['samples']:
                point['rgba'] = [0., 0., 0., 0.]
            paths[0].write_text(json.dumps(raw))
        result = self.invoke(role='inputs', change=change)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['recordedFirstTargets'], 0)
        self.assertEqual(report['firstReasonHistogram']['0'], 16)
        self.assertFalse(report['continuousCapZeroProven'])
        self.assertFalse(report['applicationObserved'])
        self.assertTrue(all(p['exactSupportReference'] is None for p in report['points']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
