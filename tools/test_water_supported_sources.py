"""Source-adapter contracts; native execution is qualified separately."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SourceAdapterContracts(unittest.TestCase):
    def source(self):
        return (ROOT / 'shaders/lib/water_supported_sources_test.glsl').read_text()

    def test_no_derivative_celestial_lookup_in_quadrature(self):
        source = self.source()
        for forbidden in ('environmentSkyRadiance(', 'sunDisk(', 'moonDisk(',
                          'fwidth(', 'dFdx(', 'dFdy('):
            self.assertNotIn(forbidden, source)
        self.assertIn('sampleSky(colortex6,ray)', source)

    def test_real_receiver_and_reflection_sources(self):
        source = self.source()
        self.assertIn('refractionTrace(', source)
        self.assertIn('texture(colortex4,uv).rgb', source)
        self.assertIn('reflectionTrace(', source)
        self.assertIn('waterTransmission(hit.a)', source)
        self.assertIn('WSA_reflectionMisses', source)

    def test_sun_uses_same_supported_kernel_and_visibility(self):
        source = self.source()
        self.assertIn('vec4 node=WST_kernel(p,target);', source)
        self.assertIn('WSA_airTrace(target,uv)', source)
        self.assertNotIn('reflected.y', source)
        self.assertIn('cachedSolarTransmission(colortex6)', source)
        self.assertIn('(1.0-0.85*rainStrength)', source)
        self.assertIn('SUN_ANGULAR_RADIUS', source)

    def test_unknown_is_explicit_and_no_covariance_repair(self):
        source = self.source()
        self.assertIn('WSA_airUnknown', source)
        self.assertIn('WSA_proxyUsed', source)
        self.assertIn('WRT_sourceKnown=false', source)
        self.assertIn('WST_prepare(n,v,c,1.333)', source)
        self.assertNotIn('normalize(v)', source)
        self.assertNotIn('max(c.', source)

    def test_disabled_and_invalid_preserve_original(self):
        source = self.source()
        self.assertIn('if(!eligible||!p.valid)return originalColor;', source)
        self.assertIn('if(WRT_status.y!=1.0)return originalColor;', source)
        self.assertIn('return result;', source)
        self.assertNotIn('originalColor+result', source)


if __name__ == '__main__':
    unittest.main()
