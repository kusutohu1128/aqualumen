"""Public audit tests of preserved actual saved packet, no GL execution."""
from pathlib import Path
import tempfile
import unittest
from audit import audit,ROOT,typed

PACKET=ROOT/'reports/2026-10-03-water-residual-sun-reasons/root-native-passivity'
PACK=ROOT/'reports/2026-10-03-water-residual-sun-reasons/cpu-pack/Aqualumen-ShoreProbe-world-native-sun-reasons-v1.zip'
BINARY=ROOT/'build/water_residual_sun_reason_probe-v1'


class SavedPacketTests(unittest.TestCase):
    def test_public_audit_preserves_full_corps_and_separates_native_from_physics(self):
        result=audit(PACKET,PACK,BINARY)
        self.assertEqual(result['status'],'PASS')
        self.assertEqual([c['inspected_points'] for c in result['cases'][:4]],[5025]*4)
        self.assertEqual(result['typedGuardQueries'],45)
        self.assertEqual(result['rawMapsFinite'],270)
        self.assertEqual(result['attachedStageDigestsChecked'],80)
        for key in ('physicalAccepted','pixelAAAccepted','IrisAccepted','visualAccepted','shippingAccepted'):
            self.assertFalse(result[key])

    def test_public_audit_rejects_another_executable_without_running_it(self):
        with tempfile.TemporaryDirectory(prefix='reason-audit-cpu-') as temporary:
            binary=Path(temporary)/'not-executed';binary.write_bytes(b'wrong CPU boundary input')
            with self.assertRaises(ValueError): audit(PACKET,PACK,binary)

    def test_public_audit_rejects_missing_or_replaced_saved_result(self):
        with tempfile.TemporaryDirectory(prefix='reason-audit-cpu-') as temporary:
            directory=Path(temporary);(directory/'result.json').write_text('{"status":"PASS"}')
            with self.assertRaises(ValueError): audit(directory,PACK,BINARY)

    def test_typed_json_boundary_rejects_boolean_integer_alias(self):
        with self.assertRaises(ValueError): typed(dict(type=5124,size=True,value=True),dict(type=5124,size=1,value=1))


if __name__=='__main__': unittest.main(verbosity=2)
