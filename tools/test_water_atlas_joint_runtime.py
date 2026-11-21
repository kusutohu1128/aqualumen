"""CPU protocol/model regression tests; none are a new Minecraft/GL run."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
import water_atlas_joint_runtime as module

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/2026-10-06-water-band-atlas/joint-20261006'
PACK=ROOT/'reports/2026-10-06-water-band-atlas/cpu-pack/Aqualumen-ShoreProbe-world-gh-phase-0-diagnostic-aligned-v2.zip'
RAW=OUT/'phase0-joint-alignment.json'


class JointTests(unittest.TestCase):
    def audit(self,path=RAW,baseline=None):
        return module.audit(path,PACK,OUT/'phase0-original16.json',OUT/'phase0-guard.json',baseline)

    def test_recorded_alignment_is_not_physical_acceptance(self):
        r=self.audit();self.assertTrue(r['encodedOutputCorrespondenceQualified'])
        self.assertEqual(r['selectedPoints'],16);self.assertEqual(r['originalSixteenMinimumAppliedGate'],4)
        for key in ['physicalAccepted','visualAccepted','shippingAccepted','wholeBandCausalityAccepted','directShaderLocalAddressReadbackObserved']:
            self.assertFalse(r[key])

    def reject(self,mutate):
        raw=json.loads(RAW.read_text());mutate(raw);original=Path.read_text
        def read(p,*args,**kwargs):return json.dumps(raw) if p==RAW else original(p,*args,**kwargs)
        with patch.object(Path,'read_text',read),self.assertRaises(ValueError):self.audit()

    def test_changed_output_color_rejected(self):
        self.reject(lambda r:r['output']['pixels'][0]['rgba'].__setitem__(0,.99))

    def test_wrong_output_coordinate_rejected(self):
        self.reject(lambda r:r['output']['pixels'][0].update(x=0))

    def test_different_quad_frame_rejected(self):
        self.reject(lambda r:r.update(afterFrame=r['beforeFrame']+1))

    def test_unrestored_target_read_buffer_rejected(self):
        self.reject(lambda r:r['output']['readMetadata'].update(targetReadBufferAfter=36065))

    def test_source_binding_alias_rejected(self):
        self.reject(lambda r:r['raw']['samplers'][1].update(textureId=r['raw']['samplers'][0]['textureId']))

    def test_band_requires_separate_alignment(self):
        with self.assertRaises(ValueError):self.audit(OUT/'phase0-joint-band.json')
        r=self.audit(OUT/'phase0-joint-band.json',OUT/'phase0-joint-alignment-audit.json')
        self.assertEqual(r['selectedPoints'],4);self.assertTrue(r['encodedOutputCorrespondenceQualified'])

    def test_real_mixin_package_failure_pattern(self):
        def separated(d):return not 'dev.aqualumen.atlasjoint.JointObserver'.startswith(d['package']+'.')
        with ZipFile(OUT/'joint-probe-v012-source.zip') as z:
            old=json.loads(z.read('tools/atlas-joint-probe/aqualumen-atlas-joint.mixins.json'))
        self.assertFalse(separated(old))
        current=json.loads((ROOT/'tools/atlas-joint-probe/aqualumen-atlas-joint.mixins.json').read_text())
        self.assertTrue(separated(current))


if __name__=='__main__':unittest.main()
