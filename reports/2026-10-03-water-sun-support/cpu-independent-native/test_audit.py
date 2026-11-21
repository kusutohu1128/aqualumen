"""Public saved-binary CPU contracts; synthetic, never GL evidence."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

MODULE=Path(__file__).with_name('audit.py')


def load():
    spec=importlib.util.spec_from_file_location('support_saved_audit',MODULE)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class SavedAuditTests(unittest.TestCase):
    def test_public_saved_binary_pair_reports_exact_repeat_without_renderer_claim(self):
        audit=load()
        with tempfile.TemporaryDirectory(prefix='support-saved-cpu-') as temporary:
            first=Path(temporary)/'a.f32';second=Path(temporary)/'b.f32'
            values=struct.pack('<4f',1,.25,0,-.5)
            first.write_bytes(values);second.write_bytes(values)
            report=audit.check_raw_pair(first,second,4,require_bit_identity=True)
            self.assertEqual(report,dict(samples=4,max_absolute_delta=0.0,bit_identical=True))

    def test_public_frozen_source_contract_recovers_both_policies_without_old_pack_policy(self):
        audit=load();expected,pins=audit.expected_sources()
        self.assertEqual(len(pins),4)
        self.assertIn('geometry-stage2.glsl',expected)
        self.assertEqual(audit.restore_support(expected['zero-physical-expanded.fsh'].decode()).encode(),
                         expected['reject-physical-expanded.fsh'])
        for mode in ('reject','zero'):
            for role in ('reasons','inputs'):
                self.assertIn(mode+'-'+role+'-metadata.json',expected)

    def test_public_saved_packet_audit_rejects_incomplete_capture_without_gl_claim(self):
        audit=load()
        with tempfile.TemporaryDirectory(prefix='support-incomplete-cpu-') as temporary:
            with self.assertRaises(ValueError): audit.audit(Path(temporary))

    def test_raw_repeats_require_bits_and_reject_truncated_nonfinite_and_outside_gate(self):
        audit=load()
        with tempfile.TemporaryDirectory(prefix='support-negative-cpu-') as temporary:
            first=Path(temporary)/'a.f32';second=Path(temporary)/'b.f32'
            first.write_bytes(struct.pack('<f',0))
            second.write_bytes(struct.pack('<f',-0.0))
            with self.assertRaises(ValueError): audit.check_raw_pair(first,second,1,require_bit_identity=True)
            second.write_bytes(b'bad')
            with self.assertRaises(ValueError): audit.check_raw_pair(first,second,1)
            second.write_bytes(struct.pack('<f',float('nan')))
            with self.assertRaises(ValueError): audit.check_raw_pair(first,second,1)
            second.write_bytes(struct.pack('<f',.5))
            with self.assertRaises(ValueError): audit.check_raw_pair(first,second,1,absolute=.49)

    def test_actual_saved_six_cases_replay_retains_no_observed_zero_branch(self):
        audit=load();packet=MODULE.parents[1]/'native-v1'
        report=audit.audit(packet)
        self.assertEqual(report['status'],'PASS_SAVED_NATIVE_REPLAY')
        self.assertEqual(len(report['cases']),6)
        self.assertEqual(report['actualZeroNodes'],0)
        self.assertFalse(report['zeroBranchObserved'])
        self.assertFalse(report['zeroBranchExecutionWitnessQualified'])
        self.assertFalse(report['physicsAccepted'])


if __name__=='__main__': unittest.main(verbosity=2)
