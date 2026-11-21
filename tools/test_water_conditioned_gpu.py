"""Public fixture generation and independent sampler-capture audit contracts."""
import tempfile
import unittest
from pathlib import Path
import struct
import shutil
import water_conditioned_gpu_source as source
import water_conditioned_gpu_audit as audit


class Fixtures(unittest.TestCase):
    def test_fixture_preserves_raw_inputs_and_rejectable_negative_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'fixture'
            source.build(out)
            records=list(struct.iter_unpack('<12f',(out/'inputs.f32').read_bytes()))
            self.assertEqual(len(records),256)
            self.assertEqual(records[60*4][8:11],(0.,0.,0.))
            self.assertEqual(records[62*4][11],8.)
            self.assertEqual(records[63*4][7],1.)
            self.assertIn('WSQ_sample',(out/'sample.fsh').read_text())

    def test_audit_rejects_repeat_corruption_in_actual_gpu_capture(self):
        packet=source.ROOT/'reports/2026-10-06-water-conditioned-sampling/gpu-capture-01'
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'corrupted'
            shutil.copytree(packet,out)
            path=out/'repeat-slot0.rgba32f'
            data=bytearray(path.read_bytes());data[0]^=1;path.write_bytes(data)
            with self.assertRaisesRegex(AssertionError,'repeat'):
                audit.audit(out)

    def test_actual_gpu_selected_coordinates_meet_predeclared_gates(self):
        import os
        packet=os.environ.get('AQUALUMEN_SAMPLER_PACKET','gpu-capture-02')
        fixture=os.environ.get('AQUALUMEN_SAMPLER_FIXTURE','gpu-fixture-v2')
        folder=source.ROOT/'reports/2026-10-06-water-conditioned-sampling'
        result=audit.audit(folder/packet,folder/fixture)
        self.assertTrue(result['allSelectedNodeGatesPassed'],result['numericFailures'])

    def test_old_approximate_cdf_capture_remains_numerically_rejected(self):
        folder=source.ROOT/'reports/2026-10-06-water-conditioned-sampling'
        result=audit.audit(folder/'gpu-capture-01',folder/'gpu-fixture-v1')
        self.assertFalse(result['allSelectedNodeGatesPassed'])


if __name__=='__main__':unittest.main()
