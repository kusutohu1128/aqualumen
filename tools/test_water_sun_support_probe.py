"""Public CPU construction contracts; never execute the GL entry point."""
import json
import os
from pathlib import Path
import subprocess
import struct
import tempfile
import unittest
from zipfile import ZipFile

from water_sun_support_pack import build_pack

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get('SUN_SUPPORT_PROBE_BINARY', str(
    ROOT/'reports/2026-10-03-water-sun-support/cpu-native/water-sun-support-probe-final-v1')))


class PublicSupportConstruction(unittest.TestCase):
    def test_four_source_roles_recover_zero_policy_and_parent_geometry_exactly(self):
        with tempfile.TemporaryDirectory() as temporary:
            roots=[]
            for mode,role in [('reject','reasons'),('zero','reasons'),('reject','inputs'),('zero','inputs')]:
                directory=Path(temporary)/(mode+'-'+role)
                archive=build_pack(ROOT,directory.with_suffix('.zip'),mode,role)
                with ZipFile(archive) as packed:
                    packed.extractall(directory)
                roots.append(str(directory/'shaders'))
            result=subprocess.run([str(BINARY),'--cpu-contract',*roots],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            observation=json.loads(result.stdout)
            self.assertFalse(observation['GLExecuted'])
            self.assertTrue(observation['zero_restores_reject_exact'])
            self.assertEqual(observation['roles'],['physical','reasons','inputs'])

    def test_exact_reject_parent_roles_recover_same_physical_main(self):
        with tempfile.TemporaryDirectory() as temporary:
            roots = []
            for role in ('reasons', 'inputs'):
                directory = Path(temporary)/role
                archive = build_pack(ROOT, directory.with_suffix('.zip'), 'reject', role)
                with ZipFile(archive) as packed:
                    packed.extractall(directory)
                roots.append(str(directory/'shaders'))
            result = subprocess.run([str(BINARY), '--cpu-contract', *roots],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            observation = json.loads(result.stdout)
            self.assertFalse(observation['GLExecuted'])
            self.assertTrue(observation['reject_parent_source_exact'])
            self.assertTrue(observation['observer_recovers_variant_physical_exact'])

    def test_public_counts_distinguish_certified_zero_from_unknown_fallback(self):
        for zero,supported,unknown,applied,rejected in [(48,0,0,1,0),(0,47,1,0,1)]:
            packed = zero+64*supported+4096*unknown+262144*48
            result = subprocess.run([str(BINARY),'--cpu-counts',str(packed),str(applied),str(rejected)],
                                    capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            observation=json.loads(result.stdout)
            self.assertEqual(observation['counts'],[zero,supported,unknown,48])
            self.assertFalse(observation['continuum_zero_proven'])

    def test_changed_included_inverse_module_rejects_exact_parent_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            roots=[]
            for role in ('reasons','inputs'):
                directory=Path(temporary)/role
                archive=build_pack(ROOT,directory.with_suffix('.zip'),'reject',role)
                with ZipFile(archive) as packed:
                    packed.extractall(directory)
                roots.append(str(directory/'shaders'))
            node=Path(roots[0])/'lib/water_snell_inverse.glsl'
            node.write_bytes(node.read_bytes()+b'// changed actual included module\n')
            result=subprocess.run([str(BINARY),'--cpu-contract',*roots],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('adapted stable module differs',result.stderr)

    def test_malformed_countword_or_applied_unknown_is_rejected(self):
        cases=[('1.5','0','0'),(str(262144*48+64*47),'0','0'),
               (str(262144*48+4096+64*47),'1','0'),('16777216','0','0')]
        for packed,applied,rejected in cases:
            result=subprocess.run([str(BINARY),'--cpu-counts',packed,applied,rejected],
                                  capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('count/status contract rejected',result.stderr)

    def test_existing_native_output_rejects_before_gl_or_source_reads(self):
        with tempfile.TemporaryDirectory() as temporary:
            sentinel=Path(temporary)/'preserved.txt'
            sentinel.write_text('untouched')
            result=subprocess.run([str(BINARY),*(['absent']*4),temporary],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('NEW output required',result.stderr)
            self.assertEqual(sentinel.read_text(),'untouched')

    def test_certificate_unknown_requires_counted_other_reason_not_hemisphere(self):
        packed=64*47+4096+262144*48
        valid=[0,-1,0,1, 0,-1,0,1, .007,.002,.003,15, 0,1,0,64*2+1,
               2,0,0,1, 1,0,packed,1]
        invalid=valid[:]
        invalid[15]=64*3+1
        invalid[16:20]=[3,1,0,0]
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'synthetic-observation.f32'
            for values,accepted in [(valid,True),(invalid,False)]:
                path.write_bytes(struct.pack('<24f',*values))
                result=subprocess.run([str(BINARY),'--cpu-readback',str(path),'1','1','1'],
                                      capture_output=True,text=True)
                self.assertEqual(result.returncode==0,accepted,result.stderr)

    def test_changed_certificate_rejects_even_with_valid_parent_archives(self):
        with tempfile.TemporaryDirectory() as temporary:
            roots=[]
            for mode,role in [('reject','reasons'),('zero','reasons'),('reject','inputs'),('zero','inputs')]:
                directory=Path(temporary)/(mode+'-'+role)
                archive=build_pack(ROOT,directory.with_suffix('.zip'),mode,role)
                with ZipFile(archive) as packed:
                    packed.extractall(directory)
                roots.append(str(directory/'shaders'))
            certificate=Path(roots[1])/'lib/water_sun_support.glsl'
            certificate.write_bytes(certificate.read_bytes()+b'// changed actual include\n')
            result=subprocess.run([str(BINARY),'--cpu-contract',*roots],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Q24 certificate source pin differs',result.stderr)


if __name__ == '__main__':
    unittest.main()
