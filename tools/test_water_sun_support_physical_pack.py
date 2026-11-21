"""Public CPU physical-view packaging contracts; never renderer acceptance."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=Path(__file__).with_name('water_sun_support_physical_pack.py')
PARENTS=ROOT/'reports/2026-10-03-water-sun-support/cpu-pack'


class PhysicalViewPackTests(unittest.TestCase):
    def test_public_zero_cli_restores_physical_final_and_removes_only_role_store(self):
        with tempfile.TemporaryDirectory(prefix='sun-physical-view-cpu-') as temporary:
            destination=Path(temporary)/'new-zero-physical.zip'
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(destination),
                '--mode','zero'],text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            with ZipFile(destination) as observed,ZipFile(PARENTS/'Aqualumen-ShoreProbe-world-sun-support-zero-reasons-v1.zip') as parent:
                for name in parent.namelist():
                    expected=(parent.read('original/shaders/final.fsh') if name=='shaders/final.fsh' else
                        parent.read('SUN-SUPPORT-physical.fsh') if name=='shaders/gbuffers_water.fsh' else parent.read(name))
                    self.assertEqual(observed.read(name),expected,name)
                metadata=json.loads(observed.read('WATER-SUN-SUPPORT-PHYSICAL-VIEW.json'))
                self.assertEqual(metadata['mode'],'zero')
                self.assertTrue(metadata['inherited_MRT_and_TES_retained'])
                self.assertFalse(metadata['fully_observer_free'])
                self.assertFalse(metadata['current_FINAL_fixed16_qualification_available'])
                self.assertFalse(metadata['shipping_accepted'])
                self.assertEqual(observed.read(metadata['parent_final_member']),parent.read('shaders/final.fsh'))
                self.assertEqual(observed.read(metadata['parent_water_member']),parent.read('shaders/gbuffers_water.fsh'))
                self.assertEqual(metadata['parent_final_sha256'],hashlib.sha256(parent.read('shaders/final.fsh')).hexdigest())
                self.assertEqual(metadata['parent_water_sha256'],hashlib.sha256(parent.read('shaders/gbuffers_water.fsh')).hexdigest())
                self.assertNotIn(b'uniform sampler2D colortex9;',observed.read('shaders/final.fsh'))
                self.assertNotIn(b'AQUALUMEN_SUN_SUPPORT_STORE_BEGIN',observed.read('shaders/gbuffers_water.fsh'))

    def test_public_reject_cli_preserves_every_other_member_and_same_original_final(self):
        with tempfile.TemporaryDirectory(prefix='sun-physical-reject-cpu-') as temporary:
            destination=Path(temporary)/'new-reject-physical.zip'
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(destination),
                '--mode','reject'],text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            with ZipFile(destination) as observed,ZipFile(PARENTS/'Aqualumen-ShoreProbe-world-sun-support-reject-reasons-v1.zip') as parent:
                for name in parent.namelist():
                    if name not in ('shaders/final.fsh','shaders/gbuffers_water.fsh'):
                        self.assertEqual(observed.read(name),parent.read(name),name)
                self.assertEqual(observed.read('shaders/final.fsh'),parent.read('original/shaders/final.fsh'))
                self.assertEqual(observed.read('shaders/gbuffers_water.fsh'),parent.read('SUN-SUPPORT-physical.fsh'))
                metadata=json.loads(observed.read('WATER-SUN-SUPPORT-PHYSICAL-VIEW.json'))
                self.assertEqual(metadata['mode'],'reject')
                self.assertIsNone(metadata['certificate_sha256'])
                self.assertFalse(metadata['operator_application_observed'])

    def test_invalid_mode_overwrite_shipping_alias_and_frozen_reports_cannot_publish(self):
        from water_sun_support_physical_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='sun-physical-guards-cpu-') as temporary:
            destination=Path(temporary)/'pack.zip'
            for mode in (True,'bad',None):
                with self.assertRaises(ValueError): build_pack(ROOT,destination,mode)
                self.assertFalse(destination.exists())
            destination.write_bytes(b'preserved')
            with self.assertRaises(FileExistsError): build_pack(ROOT,destination)
            self.assertEqual(destination.read_bytes(),b'preserved')
            alias=Path(temporary)/'shipping';alias.symlink_to(ROOT/'shaders',target_is_directory=True)
            with self.assertRaises(ValueError): build_pack(ROOT,alias/'physical-new-test.zip')
            self.assertFalse((ROOT/'shaders/physical-new-test.zip').exists())
            old=ROOT/'reports/2026-10-03-water-sun-support/cpu-pack/physical-new-test.zip'
            with self.assertRaises(ValueError): build_pack(ROOT,old)
            self.assertFalse(old.exists())

    def test_tampered_parent_rejects_before_new_output_directory_exists(self):
        from water_sun_support_physical_pack import build_pack,FROZEN,PARENTS
        with tempfile.TemporaryDirectory(prefix='sun-physical-tamper-cpu-') as temporary:
            root=Path(temporary);name=PARENTS['zero'][0];parent=root/FROZEN/name
            parent.parent.mkdir(parents=True);parent.write_bytes((ROOT/FROZEN/name).read_bytes()+b'changed')
            destination=root/'new-output/pack.zip'
            with self.assertRaises(ValueError): build_pack(root,destination)
            self.assertFalse(destination.parent.exists())


if __name__=='__main__': unittest.main(verbosity=2)
