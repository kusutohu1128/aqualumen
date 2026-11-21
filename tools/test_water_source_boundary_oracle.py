"""Independent first-plane geometry contract, not a shader RED/GREEN."""
import math
import unittest
import water_source_boundary_oracle as oracle

P=(math.sqrt(3),0,0,0,0,math.sqrt(3),0,0,0,0,-1.000390701,-1,0,0,-.100019535,0)


class FirstPlaneTests(unittest.TestCase):
    def test_visible_first_plane_has_true_forward_distance_and_projection(self):
        hit=oracle.first_plane((0,0,-1),(0,0,-1),P,6.)
        self.assertEqual(hit['kind'],'observed-plane')
        self.assertAlmostEqual(hit['travel'],5.)
        self.assertEqual(hit['screen'],(.5,.5))
        self.assertEqual(hit['position'],(0.,0.,-6.))

    def test_no_forward_or_unobserved_plane_is_not_repaired_into_a_hit(self):
        self.assertEqual(oracle.first_plane((0,0,-1),(0,0,1),P,6.)['kind'],'no-forward-crossing')
        self.assertEqual(oracle.first_plane((0,0,-1),(0,1,0),P,6.)['kind'],'no-forward-crossing')
        self.assertEqual(oracle.first_plane((0,0,-1),(2,0,-1),P,6.)['kind'],'outside-observed-viewport')
        with self.assertRaises(ValueError):
            oracle.first_plane((0,0,-1),(math.nan,0,-1),P,6.)


if __name__=='__main__':unittest.main()
