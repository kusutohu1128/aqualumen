"""Actual saved-packet reader positives/negatives, not new live GPU tests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import water_legacy_branch_runtime as b

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'reports/2026-10-06-water-legacy-branch'
PACK=EVIDENCE/'cpu-pack-v2/Aqualumen-ShoreProbe-world-legacy-branch-45-full-v2.zip'

class RuntimeTests(unittest.TestCase):
    def test_actual_selected_record_is_bounded_and_not_physical(self):
        r=b.audit(EVIDENCE/'phase45-full-raw.json',PACK,EVIDENCE/'phase45-full-guard.json')
        self.assertEqual(r['selectedPoints'],4)
        self.assertEqual(r['points'][2]['firstPredicate'],'transmittedHemisphere')
        self.assertTrue(all(p['forwardRayCorrespondenceQualified'] for p in r['points']))
        self.assertFalse(r['physicalAccepted'])
        self.assertFalse(r['thisPacketIsOriginalSixteenQualification'])
        self.assertEqual(r['originalSixteenMinimumAppliedGateUnchanged'],4)

    def test_changed_ray_coordinate_alias_and_restore_rejected(self):
        raw=json.loads((EVIDENCE/'phase45-full-raw.json').read_text())
        alterations=[lambda r:r['samplers'][5]['samples'][2]['rgba'].__setitem__(1,.125),
                     lambda r:r['samplers'][0]['samples'][2].__setitem__('y',154),
                     lambda r:r['samplers'][1].__setitem__('textureId',r['samplers'][0]['textureId']),
                     lambda r:r['stateAfter'].__setitem__(next(iter(r['stateAfter'])),99999),
                     lambda r:r.__setitem__('world','新規ワールド')]
        with tempfile.TemporaryDirectory() as tmp:
            for i,alter in enumerate(alterations):
                clone=copy.deepcopy(raw);alter(clone);path=Path(tmp)/f'negative{i}.json';path.write_text(json.dumps(clone))
                with self.assertRaises(ValueError):b.audit(path,PACK,EVIDENCE/'phase45-full-guard.json')

    def test_old_sixteen_gate_cannot_accept_new_four_point_layout(self):
        from water_gh_phase_runtime import _readback
        from water_residual_sun_iris_runtime import IDENTITY
        raw=json.loads((EVIDENCE/'phase45-full-raw.json').read_text())
        identity={**IDENTITY,'packName':PACK.name,'packSha256':raw['packSha256']}
        with self.assertRaises(ValueError):_readback(raw,identity)

if __name__=='__main__':unittest.main()
