"""Saved four-role evidence and comparison negatives, not new physical tests."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import water_legacy_branch_compare as compare

ROOT=Path(__file__).resolve().parents[1]/'reports/2026-10-06-water-legacy-branch'

class CompareTests(unittest.TestCase):
    def test_actual_four_role_inputs_and_failures(self):
        result=compare.compare(ROOT)
        self.assertTrue(result['allInputBitsEqual'])
        self.assertTrue(result['geometryHashesEqual'])
        self.assertTrue(all(all(p['fullBaseAllSevenRecordsEqual'].values()) for p in result['points']))
        self.assertEqual(result['points'][2]['predicates'],{
            'phase0-full':'none','phase0-base':'none',
            'phase45-full':'transmittedHemisphere','phase45-base':'transmittedHemisphere'})
        self.assertFalse(result['fullFrameCauseProven'])
        self.assertFalse(result['opticalFixImplemented'])

    def test_comparison_does_not_assume_inputs_identical(self):
        original=compare.runtime.audit
        def altered(raw,pack,guard):
            result=copy.deepcopy(original(raw,pack,guard))
            if str(raw).endswith('phase45-base-raw.json'):
                result['points'][2]['raw']['normal'][0]=-0.025
            return result
        with patch.object(compare.runtime,'audit',side_effect=altered):
            result=compare.compare(ROOT)
        self.assertFalse(result['allInputBitsEqual'])
        self.assertFalse(result['points'][2]['inputBitEqualityAcrossFourRoles']['normal'])
        self.assertFalse(result['points'][2]['fullBaseAllSevenRecordsEqual']['phase45'])

    def test_missing_evidence_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises((OSError,ValueError)):
                compare.compare(tmp)

if __name__=='__main__':unittest.main()
