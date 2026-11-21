import math
import json
import copy
import unittest
from water_coast_world_geometry import ROOT,first_cube,SavedCoast

class Geometry(unittest.TestCase):
    def test_first_dark_wall_not_colored_background(self):
        def block(c):return {'Name':'minecraft:stone' if c[2] in (2,4) else 'minecraft:water'}
        r=first_cube([.3,.4,.5],[0,0,1],block)
        self.assertEqual(r['cell'],[0,0,2]);self.assertAlmostEqual(r['travelMetres'],1.5)
        self.assertEqual(r['normal'],[0,0,-1])
    def test_negative_coordinates_and_downward_floor(self):
        def block(c):return {'Name':'minecraft:sand' if c[1]<0 else 'minecraft:water'}
        r=first_cube([-1.3,1.4,-2.5],[0,-1,0],block)
        self.assertEqual(r['cell'],[-2,-1,-3]);self.assertAlmostEqual(r['travelMetres'],1.4)
    def test_cutout_stops_before_floor(self):
        def block(c):return {'Name':'minecraft:seagrass' if c[1]==1 else 'minecraft:sand' if c[1]<1 else 'minecraft:water'}
        self.assertEqual(first_cube([.3,2.4,.5],[0,-1,0],block)['status'],'unsupported_geometry')
    def test_edge_tie_not_fake_receiver(self):
        r=first_cube([.5,.5,.3],[math.sqrt(.5),math.sqrt(.5),0],lambda c:{'Name':'minecraft:air'})
        self.assertEqual(r['status'],'unsupported_edge_tie')
    def test_nonnormalized_ray_rejected(self):
        with self.assertRaises(ValueError):first_cube([.3,.4,.5],[0,-2,0],lambda c:{'Name':'minecraft:air'})
    def test_actual_saved_region_decoder_and_hash(self):
        base=ROOT/'reports/2026-10-06-water-coast-stop'
        receipt=json.loads((base/'saved-test-coast-terrain.json').read_text())
        saved=SavedCoast(base/'saved-test-coast-terrain',receipt)
        self.assertEqual(saved.block((-192,64,321)),{'Name':'minecraft:air'})
        self.assertEqual(saved.chunk_evidence[(-12,20)]['data_version'],3955)
        bad=copy.deepcopy(receipt);bad['regionSHA256']='0'*64
        with self.assertRaises(ValueError):SavedCoast(base/'saved-test-coast-terrain',bad)

if __name__=='__main__':unittest.main()
