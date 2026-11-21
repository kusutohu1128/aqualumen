"""Synthetic protocol tests only; never fresh Minecraft/GPU evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from test_water_gh_phase_runtime import saved_fixture

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / 'reports/2026-10-06-water-band-atlas/cpu-pack'
SCRIPT = ROOT / 'tools/water_atlas_aligned_runtime.py'


def synthetic_fixture(directory, phase):
    # Existing synthetic fixture generator, NOT a mutated saved real capture.
    raw, _, guard = saved_fixture(directory, phase)
    name = f'Aqualumen-ShoreProbe-world-gh-phase-{phase}-diagnostic-aligned-v2.zip'
    pack = PACKS / name
    digest = hashlib.sha256(pack.read_bytes()).hexdigest()
    for fixture in (raw, guard):
        fixture.update(packName=name, packSha256=digest)
    return raw, pack, guard


class AlignedRuntimeTests(unittest.TestCase):
    def audit_fixture(self, phase=0, raw_mutation=None, guard_mutation=None):
        from water_atlas_aligned_runtime import audit
        with tempfile.TemporaryDirectory(prefix='atlas-SYNTHETIC-') as temp:
            directory = Path(temp)
            raw, pack, guard = synthetic_fixture(directory, phase)
            if raw_mutation:
                raw_mutation(raw)
            if guard_mutation:
                guard_mutation(guard)
            raw_path, guard_path = directory/'SYNTHETIC-final.json', directory/'SYNTHETIC-guard.json'
            raw_path.write_text(json.dumps(raw))
            guard_path.write_text(json.dumps(guard))
            before = {p.name: p.read_bytes() for p in directory.iterdir()}
            try:
                return audit(raw_path, pack, guard_path)
            finally:
                self.assertEqual(before, {p.name: p.read_bytes() for p in directory.iterdir()})

    def test_both_named_aligned_sources_qualify_selected_protocol_not_addresses(self):
        for phase in (0, 45):
            report = self.audit_fixture(phase)
            self.assertEqual(report['phase_degrees'], phase)
            self.assertEqual(report['selectedPoints'], 16)
            self.assertEqual(report['qualifiedAppliedPoints'], 16)
            self.assertEqual(report['minimumQualifiedAppliedPoints'], 4)
            self.assertTrue(report['sourceRecoveryQualified'])
            for field in ('atlasTexelAddressesObserved', 'atlasCoordinateQualified',
                          'alignedRuntimeAccepted', 'physicalAccepted', 'visualAccepted',
                          'shippingAccepted', 'sameFrameProven', 'fragmentFetchProven'):
                self.assertFalse(report[field], field)
            self.assertIn('PENDING_ATLAS_ADDRESS_QUALIFICATION', report['remainingRequirements'])

    def test_old_real_identity_cannot_be_accepted_as_new_capture(self):
        with self.assertRaises(ValueError):
            self.audit_fixture(raw_mutation=lambda r:r.update(
                packName='Aqualumen-ShoreProbe-world-gh-phase-0-diagnostic-v1.zip'))
        with self.assertRaises(ValueError):
            self.audit_fixture(guard_mutation=lambda g:g.update(packSha256='0'*64))

    def test_retains_original_sample_order_all_roles_guard_and_state_gates(self):
        def state(r): r['stateAfter']['binding'] += 1
        cases = (
            lambda r:r.update(renderer='llvmpipe synthetic'),
            lambda r:r.update(worldId='ordinary-world'),
            lambda r:r.update(width=2560, height=1440),
            lambda r:r['samplers'][6]['samples'][0].update(x=1114,y=169),
            lambda r:r['samplers'][6]['samples'].pop(),
            lambda r:r['samplers'][5].update(textureId=r['samplers'][4]['textureId']),
            lambda r:r['samplers'][0].update(active=False), state,
            lambda r:r['samplers'][4]['samples'][0].update(rgba=[0,0,.5,0]),
            lambda r:r['samplers'][6]['samples'][0].update(rgba=[float('nan'),0,0,1]),
        )
        for i, mutate in enumerate(cases):
            with self.subTest(case=i), self.assertRaises(ValueError):
                self.audit_fixture(raw_mutation=mutate)
        for mutate in (lambda g:g['uniform'].update(value=0),
                       lambda g:g['uniform'].update(type=5126),
                       lambda g:g.update(benchmarkState='sampling')):
            with self.assertRaises(ValueError):
                self.audit_fixture(guard_mutation=mutate)

    def test_rehashed_archive_and_old_filename_alias_are_rejected(self):
        from water_atlas_aligned_runtime import source_policy
        name = 'Aqualumen-ShoreProbe-world-gh-phase-0-diagnostic-aligned-v2.zip'
        encoded = (PACKS/name).read_bytes()
        with self.assertRaises(ValueError):
            source_policy(encoded, 'Aqualumen-ShoreProbe-world-gh-phase-0-diagnostic-v1.zip')
        with tempfile.TemporaryDirectory(prefix='atlas-SYNTHETIC-tamper-') as temp:
            candidate = Path(temp)/name
            with ZipFile(PACKS/name) as archive:
                members = {n:archive.read(n) for n in archive.namelist()}
            members['shaders/final.fsh'] += b'\n// SYNTHETIC tamper\n'
            metadata = json.loads(members['WATER-ATLAS-ALIGNED.json'])
            metadata['current_FINAL_sha256'] = hashlib.sha256(members['shaders/final.fsh']).hexdigest()
            members['WATER-ATLAS-ALIGNED.json'] = json.dumps(metadata).encode()
            with ZipFile(candidate, 'w') as archive:
                for member, content in members.items():
                    archive.writestr(member, content)
            with self.assertRaises(ValueError):
                source_policy(candidate.read_bytes(), name)

    def test_cli_reports_three_applications_negative_without_waiving_four(self):
        with tempfile.TemporaryDirectory(prefix='atlas-SYNTHETIC-cli-') as temp:
            directory = Path(temp)
            raw, pack, guard = synthetic_fixture(directory, 45)
            for i, sample in enumerate(raw['samplers'][1]['samples']):
                sample['rgba'] = [1,1,12585984,0] if i<3 else [1,0,0,0]
            raw_path, guard_path = directory/'SYNTHETIC-final.json', directory/'SYNTHETIC-guard.json'
            raw_path.write_text(json.dumps(raw)); guard_path.write_text(json.dumps(guard))
            result = subprocess.run([sys.executable, str(SCRIPT), str(raw_path), str(pack), str(guard_path)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['qualifiedAppliedPoints'], 3)
            self.assertEqual(report['applicationVerdict'], 'NEGATIVE_INSUFFICIENT_APPLICATION')
            self.assertFalse(report['alignedRuntimeAccepted'])


if __name__ == '__main__':
    unittest.main()
