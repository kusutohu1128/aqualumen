"""Real saved-data audit mutation tests; synthetic mutations are not GPU results."""
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
import water_supported_glsl_audit as audit
import water_supported_glsl_source as source

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'reports/2026-10-06-water-supported-glsl/gpu-64-01'
class SavedGpuAuditTests(unittest.TestCase):
    def test_current_actual_gpu_packet(self):
        result=audit.audit(EVIDENCE)
        self.assertTrue(result['allFourReferenceGatesPassed'])
        self.assertFalse(result['originalWaterMainExecuted'])

    def mutate(self,name,transform):
        with tempfile.TemporaryDirectory(prefix='aqualumen-supported-audit-test-') as d:
            target=Path(d)/'packet';shutil.copytree(EVIDENCE,target)
            p=target/name;p.write_bytes(transform(p.read_bytes()))
            with self.assertRaises(AssertionError):audit.audit(target)

    def test_nonidentical_repeat_rejected(self):
        self.mutate('repeat-slot0.rgba32f',lambda b:struct.pack('<f',0.)+b[4:])

    def test_wrong_raw_input_rejected(self):
        self.mutate('slot1.rgba32f',lambda b:struct.pack('<f',0.)+b[4:])

    def test_zero_response_rejected_even_with_identical_repeats(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-supported-audit-test-') as d:
            target=Path(d)/'packet';shutil.copytree(EVIDENCE,target)
            for name in ('slot0.rgba32f','repeat-slot0.rgba32f'):
                p=target/name;b=p.read_bytes();p.write_bytes(struct.pack('<f',0.)+b[4:])
            with self.assertRaises(AssertionError):audit.audit(target)

    def test_builder_order_and_mass(self):
        for order in (48,64,96):
            text=source.build(order)
            self.assertIn(f'const int WST_order={order};',text)
            rule=source.model.legendre(order)
            self.assertAlmostEqual(sum(w for _,w in rule),2,places=12)
            self.assertEqual(len(rule),order)

if __name__=='__main__':unittest.main()
