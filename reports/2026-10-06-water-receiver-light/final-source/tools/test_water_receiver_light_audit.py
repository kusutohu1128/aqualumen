"""Public audit rejects copied misleading actual capture packets; no collaborator mocks."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from water_receiver_light_audit import OUT, audit


class ActualResourceAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='aqualumen-resource-audit-')
        cls.folder=Path(cls.temporary.name)
        for name in ('build-receipt.json','install.json','archived-triangle-input-contract.json',
                     'material-queries.bin','request.properties'):
            shutil.copyfile(OUT/name,cls.folder/name)
        shutil.copytree(OUT/'actual-resources',cls.folder/'actual-resources')
        cls.original=json.loads((cls.folder/'actual-resources/readback.json').read_text())

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def tearDown(self):
        (self.folder/'actual-resources/readback.json').write_text(json.dumps(self.original))

    def reject(self, modify, message):
        data=copy.deepcopy(self.original)
        modify(data)
        (self.folder/'actual-resources/readback.json').write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,message):
            audit(self.folder)

    def test_actual_positive_capture(self):
        result=audit(self.folder)
        self.assertEqual(result['controlledGPUFetches'],80)
        self.assertFalse(result['sourceRadiance'])
        self.assertFalse(result['liveMeshResourceEpochProven'])

    def test_wrong_world(self):
        self.reject(lambda d:d.update(world_id='00000000-0000-0000-0000-000000000000'),'scope')

    def test_false_live_epoch_claim(self):
        self.reject(lambda d:d.update(liveMeshResourceEpochProven=True),'scope')

    def test_changed_actually_linked_source(self):
        self.reject(lambda d:d.update(linkedFragmentSource=d['linkedFragmentSource']+'\n// changed'),'linked source')

    def test_missing_original_return(self):
        self.reject(lambda d:d.update(originalMultiDrawReturned=False),'scope')

    def test_nonfinite_actual_uniform(self):
        self.reject(lambda d:d['resources']['uniforms']['shadowProjection']['values'].__setitem__(0,float('nan')),'nonfinite')

    def test_changed_raw_texture_hash(self):
        self.reject(lambda d:d['resources']['textures']['gtexture']['levels'][0].update(SHA256='0'*64),'sampled pixels')

    def test_guessed_filter(self):
        self.reject(lambda d:d['resources']['textures']['gtexture'].update(minFilter=9729),'filtering')

    def test_wrong_material_fetch(self):
        self.reject(lambda d:d['materialFetch']['observations'][0]['rgba'].__setitem__(0,0),'filter mismatch')

    def test_natural_derivative_overclaim(self):
        self.reject(lambda d:d['materialFetch'].update(naturalFragmentDerivatives=True),'fetch scope')


if __name__=='__main__':
    unittest.main()
