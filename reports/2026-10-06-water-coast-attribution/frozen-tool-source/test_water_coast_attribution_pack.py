"""CPU contracts only, not GL/Iris neutrality or physical acceptance."""
import unittest
from water_coast_attribution_pack import ROOT, transform, verify


class CoastAttributionPackTest(unittest.TestCase):
    def setUp(self):
        self.original = {p.relative_to(ROOT).as_posix(): p.read_bytes()
            for p in sorted([*(ROOT/'shaders').rglob('*'), ROOT/'LICENSE']) if p.is_file()}

    def test_exact_production_recovery_and_unchanged_geometry(self):
        self.assertEqual(len(verify(self.original, transform(self.original))), 5)

    def test_no_second_trace_or_lookup(self):
        old = self.original['shaders/gbuffers_water.fsh'].decode()
        new = transform(self.original)['shaders/gbuffers_water.fsh'].decode()
        for symbol in ('reflectionTrace(', 'refractionTrace(', 'localWaterColumn('):
            self.assertEqual(old.count(symbol), new.count(symbol))
        self.assertIn('gl_FragData[2]=vec4(fresnel,float(receiverKind),receiverConfidence,thickness);', new)

    def test_literal_targets_and_nonwater_zero(self):
        new = transform(self.original)['shaders/gbuffers_water.fsh'].decode()
        branch = new[new.index('if (materialId!=10000.0)'):new.index('vec3 viewPos=')]
        for i in (1, 2, 3):
            self.assertIn(f'gl_FragData[{i}]=vec4(0.0);', branch)
        self.assertIn('/* RENDERTARGETS:0,9,10,11 */', new)

    def test_iris_clear_annotation_requires_four_explicit_components(self):
        prepare = transform(self.original)['shaders/prepare.fsh'].decode()
        for i in (9, 10, 11):
            self.assertIn(f'const vec4 colortex{i}ClearColor = vec4(0.0,0.0,0.0,0.0);', prepare)


if __name__ == '__main__':
    unittest.main()
