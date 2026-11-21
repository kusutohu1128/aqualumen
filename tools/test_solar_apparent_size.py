import math
import copy
import unittest

from solar_apparent_size import apparent_diameter, observed_projection, source_radius


class SolarApparentSizeTest(unittest.TestCase):
    def observation(self):
        return {
            'available': True, 'stateRestored': True, 'scopeAuthorized': True,
            'projection': {
                'available': True, 'requested': True, 'stateUnchanged': True,
                'matrixOrder': 'column-major; index=column*4+row; GLSL column vectors',
                'program': 7, 'programAfter': 7,
                'frameBefore': 12, 'frameAfter': 12,
                'stateBefore': {'binding': 9}, 'stateAfter': {'binding': 9},
                'matrices': {'gbufferProjection': {
                    'type': 35676, 'size': 1, 'location': 2,
                    'values': [1, 0, 0, 0, 0, 2, 0, 0,
                               0, 0, -1.01, -1, 0, 0, -.1, 0]}},
                'viewport': [0, 0, 1600, 800],
                'scalars': {
                    'viewWidth': {'type': 5126, 'size': 1, 'location': 3, 'value': 1600},
                    'viewHeight': {'type': 5126, 'size': 1, 'location': 4, 'value': 800}}}}

    def test_actual_projection_reconstruction(self):
        height, fov = observed_projection(self.observation())
        self.assertEqual(height, 800)
        self.assertAlmostEqual(fov, math.degrees(2 * math.atan(.5)))

    def test_unqualified_or_changed_context_rejected(self):
        for field in ('available', 'stateRestored', 'scopeAuthorized'):
            observation = self.observation()
            observation[field] = False
            with self.assertRaises(ValueError):
                observed_projection(observation)
        for field, value in (('programAfter', 8), ('frameAfter', 13),
                             ('stateAfter', {}), ('stateUnchanged', False),
                             ('matrixOrder', 'row-major'),
                             ('viewport', [0, 0, 1500, 800])):
            observation = self.observation()
            observation['projection'][field] = value
            with self.assertRaises(ValueError):
                observed_projection(observation)

    def test_nonstandard_or_invalid_matrix_rejected(self):
        original = self.observation()
        for index, value in ((8, .01), (3, .1), (5, 0),
                             (0, 3), (11, 0), (14, .1), (5, float('nan'))):
            observation = copy.deepcopy(original)
            observation['projection']['matrices']['gbufferProjection']['values'][index] = value
            with self.assertRaises(ValueError):
                observed_projection(observation)

    def test_projection_and_resolution_scaling(self):
        self.assertAlmostEqual(apparent_diameter(100, 90, math.atan(.1)), 10)
        self.assertAlmostEqual(apparent_diameter(1440, 60, .00465),
                               1.6 * apparent_diameter(900, 60, .00465))

    def test_wider_field_reduces_apparent_size(self):
        self.assertLess(apparent_diameter(900, 90, .00465),
                        apparent_diameter(900, 60, .00465))

    def test_invalid_projection_rejected(self):
        for args in ((0, 60, .00465), (900, 180, .00465),
                     (900, 60, -1), (900, float('nan'), .00465),
                     (900, 60, math.pi / 2)):
            with self.assertRaises(ValueError):
                apparent_diameter(*args)

    def test_literal_is_unique(self):
        declaration = 'const float SUN_ANGULAR_RADIUS = 0.00465;'
        self.assertEqual(source_radius(declaration), .00465)
        for source in ('', declaration + '\n' + declaration,
                       'const float SUN_ANGULAR_RADIUS = radius;'):
            with self.assertRaises(ValueError):
                source_radius(source)


if __name__ == '__main__':
    unittest.main()
