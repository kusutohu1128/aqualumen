"""Pure CPU oracle public API checks; no GL/device or shader execution."""
import math
import unittest
from water_residual_coefficient_oracle import quadrature


class CoefficientOracleTests(unittest.TestCase):
    def test_zero_covariance_normal_incidence_matches_closed_interface(self):
        actual = quadrature((0,-1,0),(0,0,0),(0,-1,0))
        normal_R = ((1.333-1)/(1.333+1))**2
        self.assertAlmostEqual(actual['coefficients'][0],1,places=12)
        self.assertAlmostEqual(actual['coefficients'][1],normal_R,places=12)
        self.assertAlmostEqual(actual['coefficients'][2],1-normal_R,places=12)
        self.assertEqual(actual['coefficients'][3],0)
        self.assertTrue(actual['domain_valid'])

    def test_nonzero_covariance_changes_response_without_changing_mass(self):
        actual=quadrature((0,-1,0),(.01,.004,.02),(0,-1,0))
        normal_R=((1.333-1)/(1.333+1))**2
        self.assertAlmostEqual(actual['coefficients'][0],1,places=12)
        self.assertGreater(actual['coefficients'][1],normal_R)
        self.assertTrue(actual['domain_valid'])
        self.assertTrue(all(node['weight']>0 for node in actual['nodes']))

    def test_small_nonzero_covariance_at_66_degrees_is_all_TIR(self):
        angle=math.radians(66)
        actual=quadrature((0,-1,0),(.0001,0,.0001),(-math.sin(angle),-math.cos(angle),0))
        for coefficient,expected in zip(actual['coefficients'],(1,1,0,1)):
            self.assertAlmostEqual(coefficient,expected,places=12)
        self.assertTrue(actual['domain_valid'])
        self.assertTrue(all(node['TIR'] and node['T']==0 for node in actual['nodes']))

    def test_indefinite_matrix_is_not_repaired_by_absolute_tolerance(self):
        with self.assertRaises(ValueError):
            quadrature((0,-1,0),(1e-8,2e-8,1e-8),(0,-1,0))


if __name__ == '__main__':
    unittest.main()
