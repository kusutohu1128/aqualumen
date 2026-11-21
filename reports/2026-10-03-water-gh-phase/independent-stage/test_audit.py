"""Public saved-file audit tests; no GPU or mocked renderer."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
PACKET = HERE.parent
PACK = PACKET / 'cpu-pack/Aqualumen-ShoreProbe-world-gh-phase-0-physical-v1.zip'


class SavedStageAudit(unittest.TestCase):
    def run_pair(self, stage, guard=None):
        with tempfile.TemporaryDirectory(prefix='aqualumen-stage-audit-') as scratch:
            changed = Path(scratch) / 'stage.json'
            changed.write_text(json.dumps(stage))
            guard_file = PACKET / 'runtime/phase0-physical-guard.json'
            if guard is not None:
                guard_file = Path(scratch) / 'guard.json'
                guard_file.write_text(json.dumps(guard))
            return subprocess.run([sys.executable, '-B', str(HERE / 'audit.py'), '--pair',
                str(changed), str(guard_file), str(PACK)],
                capture_output=True, text=True)

    def test_saved_prepared_pair_is_qualified_without_draw_claim(self):
        result = subprocess.run([sys.executable, '-B', str(HERE / 'audit.py'), '--pair',
            str(PACKET / 'runtime/phase0-physical-stage.json'),
            str(PACKET / 'runtime/phase0-physical-guard.json'), str(PACK)],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report['preparedLinkedStagePairQualified'])
        self.assertEqual(report['stageTypes'], [35633, 36488, 36487, 35632])
        self.assertFalse(report['drawIssuedProven'])

    def test_empty_actual_context_version_is_rejected(self):
        stage = json.loads((PACKET / 'runtime/phase0-physical-stage.json').read_text())
        stage['capabilities']['version'] = ''
        self.assertNotEqual(self.run_pair(stage).returncode, 0)

    def test_stage_changed_current_program_is_rejected(self):
        stage = json.loads((PACKET / 'runtime/phase0-physical-stage.json').read_text())
        stage['programAfter'] += 1
        self.assertNotEqual(self.run_pair(stage).returncode, 0)

    def test_guard_value_boolean_is_not_scalar_int_one(self):
        stage = json.loads((PACKET / 'runtime/phase0-physical-stage.json').read_text())
        guard = json.loads((PACKET / 'runtime/phase0-physical-guard.json').read_text())
        guard['uniform']['value'] = True
        self.assertNotEqual(self.run_pair(stage, guard).returncode, 0)

    def test_missing_actual_source_hash_is_rejected(self):
        stage = json.loads((PACKET / 'runtime/phase0-physical-stage.json').read_text())
        del stage['stages'][2]['sourceSha256']
        self.assertNotEqual(self.run_pair(stage).returncode, 0)

    def test_separate_valid_observer_frames_do_not_imply_same_draw(self):
        stage = json.loads((PACKET / 'runtime/phase0-physical-stage.json').read_text())
        stage['frameBefore'] += 1
        stage['frameAfter'] += 1
        result = self.run_pair(stage)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report['preparedProgramFrameCoordinatesMatch'])
        self.assertTrue(report['separateObserverEvents'])
        self.assertFalse(report['drawIssuedProven'])


if __name__ == '__main__':
    unittest.main()
