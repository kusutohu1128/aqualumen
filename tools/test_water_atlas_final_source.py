"""CPU auditor tests only; recorded raw is not a new GL/Minecraft execution."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import water_atlas_final_source as module

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT/'reports/2026-10-06-water-band-atlas/host-20261006/phase0-v013-final-source.json'
PACK = ROOT/'reports/2026-10-06-water-band-atlas/cpu-pack/Aqualumen-ShoreProbe-world-gh-phase-0-diagnostic-aligned-v2.zip'


class FinalSourceTests(unittest.TestCase):
    def test_recorded_main_qualifies_only_bounded_scope(self):
        report = module.audit(RAW, PACK)
        self.assertTrue(report['actualCoordinateAndFetchSourceQualified'])
        for flag in ['atlasTexelAddressesObserved', 'drawFreshnessProven', 'alignedRuntimeAccepted', 'physicalBandFixAccepted']:
            self.assertFalse(report[flag])

    def reject_changed_raw(self, mutate):
        raw = json.loads(RAW.read_text())
        mutate(raw)
        original = Path.read_text
        def read(path, *args, **kwargs):
            return json.dumps(raw) if path == RAW else original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', read), self.assertRaises(ValueError):
            module.audit(RAW, PACK)

    def test_failed_observation_rejected(self):
        self.reject_changed_raw(lambda r: r.update(available=False))

    def test_changed_frame_rejected(self):
        self.reject_changed_raw(lambda r: r.update(frameAfter=r['frameBefore']+1))

    def test_changed_view_type_rejected(self):
        self.reject_changed_raw(lambda r: r['viewUniforms']['viewWidth'].update(type=5124))

    def test_changed_source_digest_rejected(self):
        self.reject_changed_raw(lambda r: r['stages'][1].update(sourceSha256='0'*64))

    def test_literal_and_output_transform_only(self):
        a = 'void main(){vec2 x=vec2(.5);gl_FragColor=vec4(x,0.0,1.0);}'
        b = 'void main(){ vec2 x = vec2(0.5f); iris_FragData0 = vec4(x,0.0f,1.0f); }'
        self.assertEqual(module.main_tokens(a), module.main_tokens(b, True))
        self.assertNotEqual(module.main_tokens(a), module.main_tokens(b.replace('0.5f', '0.4f'), True))


if __name__ == '__main__':
    unittest.main()
