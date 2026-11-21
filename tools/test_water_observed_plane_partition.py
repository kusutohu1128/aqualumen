"""Public interval behavior against independent plane intersections on real inputs."""
import json
import math
from pathlib import Path
import unittest
import water_source_boundary_audit as saved
import water_source_boundary_oracle as oracle
import water_supported_conditioned as model
import water_supported_rotated as rotated
import water_observed_plane_partition as candidate

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / 'reports/2026-10-06-water-source-boundary/fixed-observed-12-01'


class ObservedPlaneTests(unittest.TestCase):
    def test_every_real_input_node_matches_independent_first_plane_visibility(self):
        state = json.loads((CAPTURE / 'green/observer-actual-inputs/state.json').read_text())
        matrix = state['matrices']['gbufferModelView']
        projection = state['matrices']['gbufferProjection']
        nodes = saved.records(CAPTURE / 'green/observer-nodes.bin')
        visible = 0
        for raw in nodes:
            p = model.t.prepare(raw[10][:3], raw[11][:3], raw[12][:3], raw[10][3])
            q, _ = rotated.basis(p)
            x, z = raw[8][:2]
            forward = rotated.node(p, q, x, z, 1)
            self.assertTrue(forward['supported'])
            axis = tuple(a + b for a, b in zip(p['view'], forward['target']))
            length = math.sqrt(model.t.dot(axis, axis))
            facet = tuple(a / length for a in axis)
            offset = saved.transform(matrix, facet)
            start = tuple(raw[2][i] + .06 * offset[i] for i in range(3))
            ray = saved.transform(matrix, forward['target'])
            truth = oracle.first_plane(start, ray, projection, state['planeViewDistance'])
            expected = truth['kind'] == 'observed-plane'
            spans = candidate.partition(p, matrix, projection, raw[2][:3], state['planeViewDistance'], x)
            admitted = any(lo < z < hi for lo, hi in spans)
            self.assertEqual(admitted, expected, (x, z, truth))
            visible += expected
        self.assertGreater(visible, 90)

    def test_interval_interiors_and_gaps_match_independent_dense_geometry_queries(self):
        state = json.loads((CAPTURE / 'green/observer-actual-inputs/state.json').read_text())
        raw = saved.records(CAPTURE / 'green/observer-nodes.bin')[0]
        p = model.t.prepare(raw[10][:3], raw[11][:3], raw[12][:3], raw[10][3])
        matrix, projection = (state['matrices'][n] for n in ('gbufferModelView', 'gbufferProjection'))
        q, _ = rotated.basis(p)
        count = 0
        for ix in range(41):
            x = -4 + .2*ix
            spans = candidate.partition(p, matrix, projection, raw[2][:3], 6., x)
            for iz in range(257):
                z = -8 + 16*(iz+.37)/257
                node = rotated.node(p, q, x, z, 1)
                expected = False
                if node['supported']:
                    axis = tuple(a+b for a, b in zip(p['view'], node['target']))
                    length = math.sqrt(model.t.dot(axis, axis))
                    offset = saved.transform(matrix, tuple(a/length for a in axis))
                    start = tuple(raw[2][i]+.06*offset[i] for i in range(3))
                    truth = oracle.first_plane(start, saved.transform(matrix, node['target']), projection, 6.)
                    expected = truth['kind'] == 'observed-plane'
                self.assertEqual(any(lo < z < hi for lo, hi in spans), expected, (x, z))
                count += 1
        self.assertEqual(count, 10537)

    def test_edge_fade_panels_do_not_cross_a_fade_or_nearest_border_knot(self):
        state = json.loads((CAPTURE / 'green/observer-actual-inputs/state.json').read_text())
        raw = saved.records(CAPTURE / 'green/observer-nodes.bin')[0]
        p = model.t.prepare(raw[10][:3], raw[11][:3], raw[12][:3], raw[10][3])
        matrix, projection = (state['matrices'][n] for n in ('gbufferModelView', 'gbufferProjection'))
        def region(screen):
            u, v = screen
            distances = (u, v, 1-u, 1-v)
            if min(distances) >= .08:
                return 'full-source'
            return min(range(4), key=lambda i: distances[i])
        for x in (-2., -1., 0., 1., 2.):
            spans = candidate.partition(p, matrix, projection, raw[2][:3], 6., x, fade_knots=True)
            for lo, hi in spans:
                regions = []
                for fraction in (.01, .25, .5, .75, .99):
                    _, plane = candidate.plane_node(p, matrix, projection, raw[2][:3], 6., x, lo+(hi-lo)*fraction)
                    self.assertEqual(plane['kind'], 'observed-plane')
                    regions.append(region(plane['screen']))
                self.assertEqual(len(set(regions)), 1, (x, lo, hi, regions))


if __name__ == '__main__':
    unittest.main()
