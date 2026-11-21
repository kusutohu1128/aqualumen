"""Independent saved-native replay plus byte/input tampering negatives."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import water_legacy_branch_native_audit as native

ROOT=Path(__file__).resolve().parents[1]/'reports/2026-10-06-water-legacy-branch'
IRIS=ROOT/'phase45-full-audit.json'

class NativeTests(unittest.TestCase):
    def test_actual_failed_branch_passivity_and_control(self):
        r=native.audit(ROOT/'native-03',IRIS)
        self.assertEqual(r['comparisonCount'],134)
        self.assertTrue(r['actualIrisInputBitsMatched'])
        self.assertEqual([x['rejectedCount'] for x in r['selected']],[0,0,66049,66049])
        self.assertFalse(r['wholeIrisSceneReplayed'])
        self.assertFalse(r['opticalFixImplemented'])

    def test_one_raw_bit_difference_is_not_waived(self):
        original=Path.read_bytes
        def altered(p):
            b=original(p)
            if p.name=='phase45-full-slot0.rgba32f':
                b=bytes([b[0]^1])+b[1:]
            return b
        with patch.object(Path,'read_bytes',altered):
            with self.assertRaisesRegex(ValueError,'Nonzero raw-bit'):
                native.audit(ROOT/'native-03',IRIS)

    def test_wrong_actual_iris_input_is_not_repaired(self):
        original=Path.read_text
        def altered(p,*a,**k):
            text=original(p,*a,**k)
            if p==IRIS:
                r=json.loads(text);r['points'][2]['raw']['normal'][0]=-0.025
                return json.dumps(r)
            return text
        with patch.object(Path,'read_text',altered):
            with self.assertRaisesRegex(ValueError,'Actual Iris input mismatch'):
                native.audit(ROOT/'native-03',IRIS)

if __name__=='__main__':unittest.main()
