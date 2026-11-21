"""Independent finite-cap/reference and actual source-audit regression tests."""
import json
import math
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import water_supported_sources_audit as audit

ROOT = Path(__file__).resolve().parents[1]


class SourceReferenceTests(unittest.TestCase):
    def test_cap_constant_solid_angle_not_projected_area(self):
        with patch.object(audit.model, 'inverse_kernel', return_value=dict(kernel=1., supported=True)):
            for n, azimuth in ((4, 12), (16, 48)):
                value = audit.cap(None, (.24, .15, .959), .00465, n, azimuth)
                exact = 4*math.pi*math.sin(.00465/2)**2
                self.assertAlmostEqual(value['value'], exact, delta=exact*2e-14)
                self.assertEqual(value['supported'], n*azimuth)

    def test_positive_cap_and_absent_vertical(self):
        item = json.loads((ROOT/'reports/2026-10-06-water-supported-transmission/actual-iris-inputs.json').read_text())['points'][2]
        raw = item['raw']; p = audit.model.prepare(raw['normal'][:3], raw['view'][:3], raw['covariance'][:3])
        a = audit.cap(p, (.24, .15, .959), .00465)
        b = audit.cap(p, (.24, .15, .959), .00465, 16, 48)
        self.assertGreater(a['value'], 0)
        self.assertEqual(a['supported'], 48)
        self.assertLess(abs(a['value']-b['value']), 2e-4*b['value'])
        absent = audit.cap(p, (0, 1, 0), .00465)
        self.assertEqual(absent['absent'], 48)
        self.assertEqual(absent['value'], 0)

    def test_inactive_old_packet_is_rejected(self):
        # Stored real OLD acquisition, not a mocked GPU execution.
        with self.assertRaises(AssertionError):
            audit.audit(ROOT/'reports/2026-10-06-water-supported-sources/main-01')

    def test_actual_source_packet(self):
        result = audit.audit(ROOT/'reports/2026-10-06-water-supported-sources/main-02')
        self.assertEqual(result['exactRawComparisons'], 920)
        self.assertTrue(result['actualOpaqueTracePositiveQualified'])
        self.assertFalse(result['physicalOffscreenVisibilityProven'])

    def test_forged_solar_raw_cannot_pass_producer_flag(self):
        packet = ROOT/'reports/2026-10-06-water-supported-sources/main-02'
        original = Path.read_bytes
        def mutate(path):
            blob = original(path)
            if path.parent == packet/'sun' and path.name in ('ledger-slot6.rgba32f', 'ledger-repeat-slot6.rgba32f'):
                offset = 16*(128*257+128)
                blob = blob[:offset]+struct.pack('<f', 0)+blob[offset+4:]
            return blob
        # In-memory reader mutation only. No Evidence file is edited/copied.
        with patch.object(Path, 'read_bytes', mutate), patch.object(audit, 'CASES', ('sun', 'rain')):
            with self.assertRaises(AssertionError):
                audit.audit(packet)


if __name__ == '__main__':
    unittest.main()
