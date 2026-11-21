"""Mutation tests of actual saved MAIN evidence; mutations are not GPU captures."""
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
import water_supported_rgb_audit as audit
import water_supported_rgb_source as source

ROOT=Path(__file__).resolve().parents[1]
PACKET=ROOT/'reports/2026-10-06-water-supported-rgb/main-02'
class ActualMainAuditTests(unittest.TestCase):
    def test_current_main_packet(self):
        result=audit.audit(PACKET)
        self.assertTrue(result['actualOriginalMainRGBSourceResponsesQualified'])
        self.assertTrue(result['freshDirectTESBitsMatchOriginalParent'])
        self.assertFalse(result['currentPhysicalSourceTracingValidated'])

    def test_dark_response_cannot_pass_report_flags(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-rgb-audit-') as d:
            target=Path(d)/'packet';shutil.copytree(PACKET,target)
            offset=16*(128*257+128)
            for name in ('air-slot0.rgba32f','air-repeat-slot0.rgba32f'):
                p=target/'matched-Iris-callsite'/name;b=p.read_bytes()
                p.write_bytes(b[:offset]+struct.pack('<f',0)+b[offset+4:])
            with self.assertRaises(AssertionError):audit.audit(target)

    def test_changed_current_tes_rejected(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-rgb-audit-') as d:
            target=Path(d)/'packet';shutil.copytree(PACKET,target)
            p=target/'matched-Iris-callsite/zero-slot4.rgba32f';b=p.read_bytes()
            p.write_bytes(struct.pack('<f',1234)+b[4:])
            with self.assertRaises(AssertionError):audit.audit(target)

    def test_source_hash_forgery_rejected(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-rgb-audit-') as d:
            target=Path(d)/'packet';shutil.copytree(PACKET,target)
            p=target/'both.fsh';p.write_text(p.read_text()+'\n// Not queried\n')
            with self.assertRaises(AssertionError):audit.audit(target)

    def test_unique_construction_seam(self):
        with self.assertRaises(ValueError):source.replace('x x','x','y')
        with self.assertRaises(ValueError):source.replace('a','x','y')
        self.assertEqual(source.replace('axb','x','y'),'ayb')

if __name__=='__main__':unittest.main()
