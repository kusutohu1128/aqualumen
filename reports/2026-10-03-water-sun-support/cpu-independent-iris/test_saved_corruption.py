"""CPU corruption tests; temporary copied saved records, never runtime evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
PACKET=ROOT/'reports/2026-10-03-water-sun-support'
SCRIPT=PACKET/'cpu-independent-iris/audit.py'
PIN='911265553e2f44cf6ea475cdb3a69343fb9f7d5ae75be18ba012aa2f7133315f'
spec=importlib.util.spec_from_file_location('prepared_audit',SCRIPT)
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class SavedCorruptionTests(unittest.TestCase):
    def setUp(self):
        self.scratch=tempfile.TemporaryDirectory(prefix='support-audit-corruption-')
        self.directory=Path(self.scratch.name)
        self.raw_path=self.directory/'final-raw.json'
        shutil.copyfile(PACKET/'iris-zero-reasons/final-raw.json',self.raw_path)
        self.raw=json.loads(self.raw_path.read_bytes())

    def tearDown(self):
        self.scratch.cleanup()

    def corrupted(self,change):
        value=copy.deepcopy(self.raw);change(value)
        self.raw_path.write_text(json.dumps(value,allow_nan=True))
        return json.loads(self.raw_path.read_bytes())

    def reject(self,change):
        with self.assertRaises((ValueError,TypeError,KeyError,OverflowError)):
            audit.independent_raw(self.corrupted(change),'reasons','zero')

    def test_original_component_all16(self):
        self.assertEqual(len(audit.independent_raw(self.raw,'reasons','zero')),16)

    def test_repeated_coordinate_rejected(self):
        self.reject(lambda r:r['samplers'][0]['samples'][1].update(x=801,y=451))

    def test_nonfinite_rejected(self):
        self.reject(lambda r:r['samplers'][0]['samples'][0]['rgba'].__setitem__(0,float('nan')))

    def test_fractional_countword_rejected(self):
        self.reject(lambda r:r['samplers'][1]['samples'][0]['rgba'].__setitem__(2,.5))

    def test_field49_rejected(self):
        self.reject(lambda r:r['samplers'][1]['samples'][0]['rgba'].__setitem__(2,49+49*262144))

    def test_zero_cannot_double_count_original_rejections(self):
        def change(r):
            r['samplers'][0]['samples'][0]['rgba']=[3,48,0,0]
            r['samplers'][1]['samples'][0]['rgba']=[1,0,1+47*64+48*262144,48]
        self.reject(change)

    def test_unknown_requires_original_other_count(self):
        def change(r):
            r['samplers'][0]['samples'][0]['rgba']=[3,48,0,0]
            r['samplers'][1]['samples'][0]['rgba']=[1,0,47*64+4096+48*262144,48]
        self.reject(change)

    def test_applied_requires48_calls(self):
        def change(r):
            r['samplers'][0]['samples'][0]['rgba']=[0,0,0,0]
            r['samplers'][1]['samples'][0]['rgba']=[1,1,47*64+47*262144,0]
        self.reject(change)

    def test_wrong_identity_and_storage_rejected_by_public_boundary(self):
        pack=PACKET/'cpu-pack/Aqualumen-ShoreProbe-world-sun-support-zero-reasons-v1.zip'
        guard=PACKET/'iris-zero-reasons/guard-raw.json'
        for change in (lambda r:r.update(packSha256='0'*64),
                       lambda r:r['samplers'][0].update(actualFormat=34842)):
            self.corrupted(change)
            with self.assertRaises(ValueError): audit.public.audit(self.raw_path,pack,guard)

    def test_corrupt_zip_pin_rejected(self):
        pack=PACKET/'cpu-pack/Aqualumen-ShoreProbe-world-sun-support-zero-reasons-v1.zip'
        copied=self.directory/pack.name;shutil.copyfile(pack,copied)
        copied.write_bytes(copied.read_bytes()+b'corruption')
        with self.assertRaisesRegex(ValueError,'ZIP changed'): audit.source_contract(copied,'zero-reasons')

    def test_truncated_png_rejected(self):
        png=PACKET/'iris-zero-reasons/run/underwater-up-near.png'
        copied=self.directory/'truncated.png';copied.write_bytes(png.read_bytes()[:2048])
        with self.assertRaises(ValueError): audit.check_png(copied,(1600,900))

    def test_author_source_pin_unchanged(self):
        self.assertEqual(hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),PIN)


if __name__=='__main__': unittest.main(verbosity=2)
