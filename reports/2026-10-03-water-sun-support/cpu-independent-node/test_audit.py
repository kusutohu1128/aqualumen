"""Public saved-readback audit tests; no GL/app calls."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = Path(__file__).with_name('audit.py')
NATIVE = ROOT / 'reports/2026-10-03-water-sun-support/node-native-v1'


class AuditTests(unittest.TestCase):
    def test_saved_native344_is_reconstructed_and_replayed_without_gl(self):
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), str(NATIVE)],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['count'], 344)
        self.assertEqual(report['classes'], {'absent': 29, 'supported': 312, 'unknown': 3})
        self.assertTrue(report['freshLiteralCPUReplayExact'])
        self.assertTrue(report['noFalseIndependentFractionCertificate'])
        self.assertFalse(report['nativeGLExecutedByAudit'])
        self.assertFalse(report['shippingAccepted'])

    def test_modified_raw_copy_cannot_inherit_native_exporter_pass(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-audit-raw-') as folder:
            copy = Path(folder) / 'copy'
            shutil.copytree(NATIVE, copy)
            raw = copy / 'slot0.rgba32ui'
            values = bytearray(raw.read_bytes())
            values[0] ^= 1
            raw.write_bytes(values) # Only a NEW temporary copy; never native.
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), str(copy)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            report = json.loads(result.stdout)
            self.assertEqual(report['status'], 'INCONCLUSIVE')
            self.assertIn('raw digest differs', report['reason'])
            self.assertFalse(report['nativeGLExecutedByAudit'])

    def test_modified_state_copy_is_rejected_even_with_unchanged_raw(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-audit-state-') as folder:
            copy = Path(folder) / 'copy'
            shutil.copytree(NATIVE, copy)
            file = copy / 'result.json'
            metadata = json.loads(file.read_text())
            metadata['uploads'][0]['actualState']['viewport'][0] = 1
            file.write_text(json.dumps(metadata))
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), str(copy)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            report = json.loads(result.stdout)
            self.assertEqual(report['status'], 'INCONCLUSIVE')
            self.assertIn('draw state differs', report['reason'])
            self.assertFalse(report['nativeGLExecutedByAudit'])


if __name__ == '__main__':
    unittest.main()
