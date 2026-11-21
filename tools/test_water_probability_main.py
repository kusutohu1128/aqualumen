"""Actual four-stage MAIN readback must satisfy the retained dense T gate.

AQ_PROBABILITY_MAIN selects an immutable captured packet, never an ordinary
Minecraft world. The original fast64 packet is the optical RED control.
"""
import os
from pathlib import Path
import struct
import unittest
import water_supported_transmission as model


class ProbabilityMainTests(unittest.TestCase):
    def test_actual_diffuse_main_meets_unchanged_dense_transmission_gate(self):
        root = Path(os.environ.get('AQ_PROBABILITY_MAIN',
            'reports/2026-10-06-water-fast-inverse/main-probability-8-01'))
        point = 16 * (128 * 257 + 128)
        def pixel(slot):
            return struct.unpack_from('<4f',
                (root / 'diffuse' / f'enabled-slot{slot}.rgba32f').read_bytes(), point)
        normal, view, covariance, transmitted = [pixel(i) for i in (1, 2, 3, 6)]
        context = model.prepare(normal[:3], view[:3], covariance[:3], covariance[3])
        reference = model.integrate_light(context, 256)['value']
        gate = 2e-6 + 2e-4 * abs(reference)
        self.assertLessEqual(abs(4 * transmitted[0] - reference), gate)


if __name__ == '__main__':
    unittest.main()
