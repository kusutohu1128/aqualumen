"""Public TEST ZIP contracts only, not renderer or physical evidence."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=Path(__file__).with_name('water_sun_support_pack.py')
FROZEN=ROOT/'reports/2026-10-03-water-snell-main/cpu-pack'


class SupportPackTests(unittest.TestCase):
    def test_public_reject_cli_preserves_all_parent_shader_and_original_bytes(self):
        with tempfile.TemporaryDirectory(prefix='sun-support-cpu-') as temporary:
            destination=Path(temporary)/'Aqualumen-ShoreProbe-world-sun-support-reject-reasons-v1.zip'
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(destination),
                '--mode','reject','--observe','reasons'],text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            with ZipFile(destination) as observed,ZipFile(FROZEN/'Aqualumen-SnellMain-stable-reasons-v1.zip') as parent:
                for name in parent.namelist():
                    self.assertEqual(observed.read(name),parent.read(name),name)
                metadata=json.loads(observed.read('WATER-SUN-SUPPORT.json'))
                self.assertEqual(metadata['mode'],'reject')
                self.assertEqual(metadata['observe'],'reasons')
                self.assertTrue(metadata['parent_shader_bytes_exact'])
                self.assertFalse(metadata['certificate_present'])
                self.assertFalse(metadata['physical_accepted'])

    def test_public_reject_inputs_preserves_first_target_layout_and_no_count_claims(self):
        with tempfile.TemporaryDirectory(prefix='sun-support-cpu-') as temporary:
            destination=Path(temporary)/'reject-inputs.zip'
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(destination),
                '--mode','reject','--observe','inputs'],text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            with ZipFile(destination) as observed,ZipFile(FROZEN/'Aqualumen-SnellMain-stable-inputs-v1.zip') as parent:
                for name in parent.namelist(): self.assertEqual(observed.read(name),parent.read(name),name)
                metadata=json.loads(observed.read('WATER-SUN-SUPPORT.json'))
                self.assertFalse(metadata['C12_is_TES'])
                self.assertTrue(metadata['countsNotCollected'])
                self.assertFalse(metadata['current_certificate_counts_observed'])
                self.assertEqual(metadata['target_channels']['12'][-1],'encodedFirstReasonAndNode')

    def test_invalid_modes_overwrite_and_shipping_paths_do_not_publish(self):
        from water_sun_support_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='sun-support-cpu-') as temporary:
            destination=Path(temporary)/'pack.zip'
            for mode,observe in [('wrong','reasons'),('reject','wrong')]:
                with self.assertRaises(ValueError): build_pack(ROOT,destination,mode,observe)
                self.assertFalse(destination.exists())
            destination.write_bytes(b'preserved')
            with self.assertRaises(FileExistsError): build_pack(ROOT,destination)
            self.assertEqual(destination.read_bytes(),b'preserved')
            with self.assertRaises(ValueError): build_pack(ROOT,ROOT/'dist/sun-support-new.zip')
            self.assertFalse((ROOT/'dist/sun-support-new.zip').exists())

    def test_tampered_frozen_parent_is_rejected_before_output_directory_writes(self):
        from water_sun_support_pack import build_pack,FROZEN as relative,PARENTS
        with tempfile.TemporaryDirectory(prefix='sun-support-parent-cpu-') as temporary:
            root=Path(temporary);filename=PARENTS['reasons'][0]
            parent=root/relative/filename;parent.parent.mkdir(parents=True)
            parent.write_bytes((ROOT/relative/filename).read_bytes()+b'changed')
            destination=root/'new-output/pack.zip'
            with self.assertRaises(ValueError): build_pack(root,destination)
            self.assertFalse(destination.parent.exists())

    def test_public_zero_cli_keeps_parent_recovery_and_separate_certificate_count_lane(self):
        with tempfile.TemporaryDirectory(prefix='sun-support-zero-cpu-') as temporary:
            destination=Path(temporary)/'zero-reasons.zip'
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(destination),
                '--mode','zero','--observe','reasons'],text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            from water_sun_support_pack import recover_helper,recover_water,CERTIFICATE
            with ZipFile(destination) as observed,ZipFile(FROZEN/'Aqualumen-SnellMain-stable-reasons-v1.zip') as parent:
                helper=observed.read('shaders/lib/water_residual_sun.glsl')
                water=observed.read('shaders/gbuffers_water.fsh')
                self.assertEqual(recover_helper(helper),parent.read('shaders/lib/water_residual_sun.glsl'))
                self.assertEqual(recover_water(water,'reasons'),parent.read('shaders/gbuffers_water.fsh'))
                self.assertEqual(observed.read(CERTIFICATE),(ROOT/CERTIFICATE).read_bytes())
                metadata=json.loads(observed.read('WATER-SUN-SUPPORT.json'))
                self.assertTrue(metadata['certificate_present'])
                self.assertFalse(metadata['countsNotCollected'])
                self.assertEqual(metadata['target_channels']['10'][2],'certificateCounts')
                self.assertEqual(metadata['certificate_count_policy']['formula'],
                                 'zero+64*support+4096*unknown+262144*calls')
                self.assertFalse(metadata['runtime_accepted'])
                from water_sun_support_pack import HELPER,WATER,SUPPORT_STORE,FAILURE,BODIES,_tag
                for name in parent.namelist():
                    if name not in (HELPER,WATER): self.assertEqual(observed.read(name),parent.read(name),name)
                self.assertEqual(helper.count(FAILURE.encode()),5)
                self.assertNotIn(b'WNS_status.z=',helper)
                self.assertIn((FAILURE+_tag('POLICY')+'// AQUALUMEN_SNELL_MAIN_REPLACE_BEGIN:BRANCH\n').encode(),helper)
                self.assertIn(b'nodeValid=snell.status==1 && WSP_supportClass==1;',helper)
                self.assertEqual(water.decode().replace(SUPPORT_STORE,'').encode(),
                                 observed.read(metadata['physical_water_fs_member']))
                for name in BODIES:
                    with self.assertRaises(ValueError):
                        recover_helper(helper.replace(_tag(name).encode(),b'',1))
                with self.assertRaises(ValueError): recover_water(water+b'changed','reasons')

    def test_zero_inputs_public_cli_preserves_every_nonhelper_parent_member_without_count_claim(self):
        from water_sun_support_pack import HELPER,WATER,recover_helper,INPUT_STORE
        with tempfile.TemporaryDirectory(prefix='sun-support-zero-inputs-cpu-') as temporary:
            destination=Path(temporary)/'zero-inputs.zip'
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(destination),
                '--mode','zero','--observe','inputs'],text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            with ZipFile(destination) as observed,ZipFile(FROZEN/'Aqualumen-SnellMain-stable-inputs-v1.zip') as parent:
                for name in parent.namelist():
                    if name!=HELPER: self.assertEqual(observed.read(name),parent.read(name),name)
                self.assertEqual(recover_helper(observed.read(HELPER)),parent.read(HELPER))
                metadata=json.loads(observed.read('WATER-SUN-SUPPORT.json'))
                self.assertTrue(metadata['certificate_present'])
                self.assertTrue(metadata['countsNotCollected'])
                self.assertFalse(metadata['current_certificate_counts_observed'])
                self.assertFalse(metadata['C12_is_TES'])
                self.assertEqual(metadata['target_channels']['12'][-1],'encodedFirstReasonAndNode')
                self.assertEqual(observed.read(WATER).decode().replace(INPUT_STORE,'').encode(),
                                 observed.read(metadata['physical_water_fs_member']))

    def test_unapproved_certificate_and_malformed_helper_cannot_publish(self):
        from water_sun_support_pack import build_pack,FROZEN as relative,PARENTS,CERTIFICATE,transform_helper,HELPER
        with tempfile.TemporaryDirectory(prefix='sun-support-certificate-cpu-') as temporary:
            root=Path(temporary);filename=PARENTS['reasons'][0]
            parent=root/relative/filename;parent.parent.mkdir(parents=True)
            parent.write_bytes((ROOT/relative/filename).read_bytes())
            certificate=root/CERTIFICATE;certificate.parent.mkdir(parents=True)
            certificate.write_bytes((ROOT/CERTIFICATE).read_bytes()+b'changed')
            destination=root/'new-output/pack.zip'
            with self.assertRaises(ValueError): build_pack(root,destination,'zero')
            self.assertFalse(destination.parent.exists())
            with ZipFile(parent) as archive:
                helper=archive.read(HELPER)
                with self.assertRaises(ValueError): transform_helper(helper.replace(b'nodeValid=snell.status==1;',b'nodeValid=true;'))

    def test_shipping_symlink_alias_and_old_report_paths_reject_before_writes(self):
        from water_sun_support_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='sun-support-alias-cpu-') as temporary:
            alias=Path(temporary)/'shipping';alias.symlink_to(ROOT/'shaders',target_is_directory=True)
            with self.assertRaises(ValueError): build_pack(ROOT,alias/'support-new-test.zip','zero')
            self.assertFalse((ROOT/'shaders/support-new-test.zip').exists())
            old=ROOT/'reports/2026-10-03-water-snell-main/support-new-test.zip'
            with self.assertRaises(ValueError): build_pack(ROOT,old)
            self.assertFalse(old.exists())


if __name__=='__main__': unittest.main(verbosity=2)
