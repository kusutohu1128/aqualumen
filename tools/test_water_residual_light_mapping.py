"""Public CPU mapping contracts; no GL/shader/source-integration acceptance."""
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

import water_residual_light_mapping as mapping


def unit(v):
    length = math.sqrt(sum(x*x for x in v))
    return tuple(x/length for x in v)


def independent_forward(v, n, eta=1.333):
    facing = sum(a*b for a, b in zip(n, v))
    cost = math.sqrt(1-eta*eta*(1-facing*facing))
    return tuple(-eta*v[i]+(eta*facing-cost)*n[i] for i in range(3))


def finite_difference(v, t):
    # Orthonormal tangent directions; exponential-map area is one at the origin.
    axis = (0, 0, 1) if abs(t[2]) < .9 else (1, 0, 0)
    cross = lambda a, b: (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
                           a[0]*b[1]-a[1]*b[0])
    tangent = unit(cross(t, axis))
    bitangent = cross(t, tangent)
    derivatives = []
    h = mapping.FD_STEP
    for direction in (tangent, bitangent):
        rays = [tuple(t[i]*math.cos(h)+sign*direction[i]*math.sin(h)
                      for i in range(3)) for sign in (-1, 1)]
        slopes = [mapping.map_light(v, ray)["slope"] for ray in rays]
        derivatives.append(tuple((slopes[1][i]-slopes[0][i])/(2*h) for i in (0, 1)))
    a, b = derivatives
    return abs(a[0]*b[1]-a[1]*b[0])


class LightMappingTest(unittest.TestCase):
    def test_public_offaxis_mapping_reconstructs_transmitted_direction(self):
        v, t = unit((0, -1, 0)), unit((.2, 1, .05))
        result = subprocess.run([sys.executable, "-B", str(Path(mapping.__file__)),
                                 "--v", *map(str, v), "--t", *map(str, t)],
                                text=True, capture_output=True, check=True)
        actual = json.loads(result.stdout)
        reconstructed = independent_forward(v, actual["normal"])
        self.assertLess(max(abs(a-b) for a, b in zip(t, reconstructed)), 1e-11)

    def test_normal_incidence_has_nontrivial_slope_solid_angle_jacobian(self):
        actual = mapping.map_light((0, -1, 0), (0, 1, 0))
        self.assertAlmostEqual(actual["jacobian_slope_per_solid_angle"],
                               1/(1.333-1)**2, places=11)

    def test_independent_tangent_area_matches_jacobian_offaxis(self):
        cases = [((0, -1, 0), (0, 1, 0)), ((0, -1, 0), (.2, 1, .05)),
                 ((.12, -1, -.08), (.45, 1, .2)), ((.2, -1, .15), (-.2, 1, .1)),
                 ((0, -1, 0), (math.sin(.69), math.cos(.69), 0))]
        for raw_v, raw_t in cases:
            v, t = unit(raw_v), unit(raw_t)
            actual = mapping.map_light(v, t)
            expected = finite_difference(v, t)
            with self.subTest(v=v, t=t):
                self.assertLessEqual(abs(actual["jacobian_slope_per_solid_angle"]-expected),
                                     mapping.FD_ABSOLUTE+mapping.FD_RELATIVE*expected)
                self.assertLess(actual["reconstruction_error"], 1e-11)

    def test_invalid_hemisphere_singular_or_wrong_branch_is_rejected(self):
        eta = 1.333
        horizontal_n_v = (math.sqrt(.75), -.5, 0)
        horizontal_n_t = (-math.sqrt(1-(eta*.5)**2), eta*.5, 0)
        cases = [((0, 1, 0), (0, 1, 0), eta), ((0, -1, 0), (0, -1, 0), eta),
                 ((0, -1, 0), (1, 0, 0), eta), ((0, -1, 0), unit((1, .01, 0)), eta),
                 (horizontal_n_v, horizontal_n_t, eta), ((0, -1, 0), (0, 1, 0), 1)]
        for v, t, index in cases:
            with self.subTest(v=v, t=t, eta=index), self.assertRaises(ValueError):
                mapping.map_light(v, t, index)

    def test_no_caller_normalization_or_nonfinite_values(self):
        for v in ((0, -.99, 0), (0, -1.0000001, 0), (math.nan, -1, 0), (0, -1, math.inf)):
            with self.assertRaises(ValueError):
                mapping.map_light(v, (0, 1, 0))

    def test_forward_critical_and_tir_are_rejected_without_clamping(self):
        for v, eta in (((.8, -.6, 0), 1.25), ((.8, -.6, 0), 1.333)):
            with self.assertRaises(ValueError):
                mapping.forward_snell(v, (0, -1, 0), eta)


if __name__ == "__main__":
    unittest.main()
