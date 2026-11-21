import unittest
import water_conditioned_sources_source as source
import water_conditioned_sources_audit as audit


class SourceInterface(unittest.TestCase):
    def test_new_main_source_preserves_original_geometry_and_source_adapter(self):
        sources,proposal=source.build(64)
        self.assertEqual(len(proposal),64)
        for i in range(3):
            self.assertEqual(sources[f'geometry-stage{i}.glsl'],(source.ROOT/'reports/2026-10-06-water-legacy-branch/native-sources-v2'/f'geometry-stage{i}.glsl').read_text())
        self.assertIn('WSQ_sample(p',sources['enabled.fsh'])
        self.assertIn('WRT_airSource(node.xyz)',sources['enabled.fsh'])
        self.assertIn('WRT_waterSource(node.xyz)',sources['enabled.fsh'])
        self.assertIn('float solarIntegral=WSA_cap',sources['enabled.fsh'])
        self.assertIn('WSA_allowProxies',sources['strict.fsh'])

    def test_finite_main_replay_is_distinct_from_dense_convergence(self):
        folder=source.ROOT/'reports/2026-10-06-water-conditioned-sampling'
        result=audit.audit(folder/'source-64-main-01',folder/'main-sources-64-v1')
        self.assertTrue(result['finiteProposalAndCapGatesPassed'],result['finiteProposalAndCapFailures'])
        self.assertFalse(result['denseCoefficientGatesPassed'])


if __name__=='__main__':unittest.main()
