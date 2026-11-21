import unittest
from water_coast_world_pack import ROOT,transform
import water_coast_stop_pack as stop

class WorldPack(unittest.TestCase):
    def setUp(self):
        self.original={p.relative_to(ROOT).as_posix():p.read_bytes() for p in sorted([*(ROOT/'shaders').rglob('*'),ROOT/'LICENSE']) if p.is_file()}
        self.files=transform(self.original)
    def test_exact_original_recovery(self):
        self.assertEqual(len(stop.verify(self.original,self.files)),5)
    def test_no_extra_trace_or_depth_lookup(self):
        a=self.original['shaders/gbuffers_water.fsh'].decode();b=self.files['shaders/gbuffers_water.fsh'].decode()
        for call in ('refractionTrace(','reflectionTrace(','texture(depthtex1,'):
            self.assertEqual(a.count(call),b.count(call))
        self.assertIn('(upperSurface ? 9 : 8)',b)
    def test_actual_world_variables_not_guessed_inverse(self):
        b=self.files['shaders/gbuffers_water.fsh'].decode()
        self.assertIn('gl_FragData[5]=vec4(absolutePosition,initialPath)',b)
        self.assertIn('gl_FragData[6]=vec4(transmitted,searchSeed)',b)
        self.assertIn('stopReceiverWorldPosition=relativeWorld(receiver)+cameraPosition',b)

if __name__=='__main__': unittest.main()
