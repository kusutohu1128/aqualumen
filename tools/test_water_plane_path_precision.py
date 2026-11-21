"""Actual original-MAIN path/Beer precision RED; no gate or shader fix here."""
import json
import math
import os
from pathlib import Path
import struct
import unittest
import water_source_boundary_audit as saved
import water_source_boundary_oracle as oracle


class PlanePathPrecisionTests(unittest.TestCase):
    def test_observed_center_receiver_uses_first_plane_beer_path_with_retained_unit_gate(self):
        capture = Path(os.environ.get('AQ_PLANE_MAIN', 'reports/2026-10-06-water-source-boundary/fixed-observed-12-01'))
        source = Path(os.environ.get('AQ_PLANE_SOURCE', 'reports/2026-10-06-water-source-boundary/fixed-observer-12-v1'))
        qualified = saved.audit(capture, source)
        self.assertEqual(qualified['observedPlaneMisses'], 0)
        state = json.loads((capture / 'green/observer-actual-inputs/state.json').read_text())
        inverse = state['matrices']['gbufferProjectionInverse']
        depths = {a[0] for a in struct.iter_unpack('<f', (capture / 'green/observer-actual-inputs/input-sampler3.f32').read_bytes())}
        self.assertEqual(len(depths), 1)
        f32 = lambda a: struct.unpack('<f', struct.pack('<f', a))[0]
        z = f32(f32(next(iter(depths))*2)-1)
        reconstructed_z = f32(f32(f32(inverse[10]*z)+inverse[14])/f32(f32(inverse[11]*z)+inverse[15]))
        tested = 0
        for index, observation in enumerate(saved.records(capture / 'green/observer-nodes.bin')):
            if observation[6][3] <= 0:
                continue
            self.assertEqual(observation[19][2], reconstructed_z)
            truth = oracle.first_plane(observation[3][:3], observation[4][:3],
                                       state['matrices']['gbufferProjection'], -reconstructed_z)
            u, v = truth['screen']
            if min(u, v, 1-u, 1-v) <= .1:
                continue
            # A genuine center-source control: edge/SSR confidence must be1,
            # not avoided through a weighted small-node or vacuous tolerance.
            self.assertEqual(observation[17][2:], (1., 1.))
            expected_unit = math.exp(-.085*truth['distance'])
            measured_unit = observation[7][1]/.125
            gate = 2e-6+2e-4*expected_unit
            self.assertLessEqual(abs(measured_unit-expected_unit), gate,
                (index, measured_unit, expected_unit, observation[6][3], truth['distance'], gate))
            tested += 1
        self.assertGreater(tested, 80)


if __name__ == '__main__':
    unittest.main()
