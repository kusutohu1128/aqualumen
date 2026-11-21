"""CPU packaging/source contracts only; no GLSL compilation or renderer RED."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=Path(__file__).with_name('water_residual_light_pack.py')
BASE=ROOT/'reports/2026-10-03-water-residual-angular/baseline-guard-v2-pack.zip'
STUB=ROOT/'reports/2026-10-03-water-residual-light-integral/cpu-pack/Aqualumen-ShoreProbe-world-water-residual-light-stub-v1.zip'


class LightPackTests(unittest.TestCase):
    def test_public_builder_accepts_frozen_stub_digest_as_truthful_separate_mode(self):
        from water_residual_light_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-light-frozen-stub-') as temporary:
            root=Path(temporary)/'root'
            parent=root/'reports/2026-10-03-water-residual-angular/baseline-guard-v2-pack.zip'
            helper=root/'shaders/lib/water_residual_light.glsl'
            parent.parent.mkdir(parents=True)
            parent.write_bytes(BASE.read_bytes())
            helper.parent.mkdir(parents=True)
            with ZipFile(STUB) as archive:
                helper.write_bytes(archive.read('shaders/lib/water_residual_light.glsl'))
            output=build_pack(root,Path(temporary)/'stub-mode.zip')
            with ZipFile(output) as archive:
                metadata=json.loads(archive.read('WATER-RESIDUAL-LIGHT.json'))
                fs=archive.read('shaders/gbuffers_water.fsh').decode()
            self.assertTrue(metadata['stub_only'])
            self.assertEqual(metadata['mode'],'residual-light-integral-stub')
            self.assertEqual(metadata['supported_source_kinds'],[])
            self.assertIsNone(metadata['radial_order'])
            self.assertNotIn('bool WLS_legacyApplied()',fs)

    def test_public_pack_integral_source_contract_matches_pinned_rules_and_unconditional_base(self):
        from water_residual_light_pack import build_pack
        import re
        rules_path=ROOT/'reports/2026-10-03-water-residual-light-integral/cpu-integral/gauss-laguerre-rules-refined.json'
        rules=json.loads(rules_path.read_bytes())['rules']['8']
        with tempfile.TemporaryDirectory(prefix='aqualumen-light-rule-') as temporary:
            output=build_pack(ROOT,Path(temporary)/'candidate.zip')
            with ZipFile(output) as archive:
                helper=archive.read('shaders/lib/water_residual_light.glsl').decode()
                metadata=json.loads(archive.read('WATER-RESIDUAL-LIGHT.json'))
            self.assertEqual(metadata['refined_rules_sha256'],hashlib.sha256(rules_path.read_bytes()).hexdigest())
            for name,expected in (('radial',rules['nodes']),('weights',rules['weights'])):
                text=re.search(r'const float '+name+r'\[8\]=float\[8\]\((.*?)\);',helper,re.S).group(1)
                self.assertEqual([float(v.strip()) for v in text.split(',')],expected)
            self.assertLess(helper.index('vec3 base=waterResidualInterface('),helper.index('if (!candidate)'))
            self.assertLess(helper.index('vec3 full=environmentSkyRadiance('),helper.index('return WLS_active?base:full;'))
            self.assertIn('candidate=requested && WLS_SOURCE_KIND==1',helper)
            self.assertIn('determinant>0.0',helper)
            self.assertNotIn('max(determinant',helper)
            self.assertIn('vec3 target=normalize(',helper)
            self.assertIn('WLS_status.w=max(WLS_status.w,1.0);',helper)

    def test_public_cli_packages_approved_narrow_integral_without_runtime_or_native_sun_claim(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-light-integral-') as temporary:
            output=Path(temporary)/'candidate.zip'
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(output)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            with ZipFile(output) as archive:
                metadata=json.loads(archive.read('WATER-RESIDUAL-LIGHT.json'))
                helper=archive.read('shaders/lib/water_residual_light.glsl').decode()
                fs=archive.read('shaders/gbuffers_water.fsh').decode()
            self.assertFalse(metadata['stub_only'])
            self.assertEqual(metadata['mode'],'residual-light-integral-narrow')
            self.assertEqual(metadata['supported_source_kinds'],[1])
            self.assertTrue(metadata['native_sun_unsupported'])
            self.assertEqual(metadata['radial_order'],8)
            self.assertEqual(metadata['azimuth_order'],16)
            self.assertIn('bool WLS_legacyApplied() { return WR_status.y==1.0; }',fs)
            self.assertIn('WLS_status.y=1.0;',helper)
            self.assertNotIn('normalize(viewToEye)',helper)
            self.assertNotIn('normalize(meanNormal)',helper)
            self.assertIn('WLS_SOURCE_KIND==1',helper)
            self.assertIn('1.0+eta*eta*(dot(viewToEye,viewToEye)-1.0)',helper)
            for field in ('runtime_accepted','energy_accepted','reciprocity_accepted','visual_accepted','shipping_fix'):
                self.assertFalse(metadata[field])

    def test_public_builder_preserves_existing_file_and_rejects_shipping_aliases(self):
        from water_residual_light_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-light-paths-') as temporary:
            folder=Path(temporary)
            root=folder/'root'
            root.mkdir()
            existing=folder/'existing.zip'
            existing.write_bytes(b'user-owned unchanged')
            with self.assertRaises(FileExistsError):
                build_pack(root,existing)
            self.assertEqual(existing.read_bytes(),b'user-owned unchanged')
            alias=folder/'alias'
            alias.symlink_to(root/'shaders',target_is_directory=True)
            for output in (root/'shaders'/'bad.zip',root/'dist'/'bad.zip',alias/'bad.zip'):
                with self.subTest(output=output):
                    with self.assertRaises(ValueError):
                        build_pack(root,output)
                    self.assertFalse(output.exists())
            self.assertEqual(list(root.iterdir()),[])

    def test_public_builder_rejects_changed_parent_before_output_creation(self):
        from water_residual_light_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-light-parent-') as temporary:
            root=Path(temporary)
            parent=root/'reports/2026-10-03-water-residual-angular/baseline-guard-v2-pack.zip'
            parent.parent.mkdir(parents=True)
            parent.write_bytes(BASE.read_bytes()+b'changed outer ZIP seam')
            output=root/'new-output'/'bad.zip'
            with self.assertRaises(ValueError):
                build_pack(root,output)
            self.assertFalse(output.parent.exists())

    def test_public_pack_outer_disable_recovers_exact_resolved_parent(self):
        from water_residual_light_pack import build_pack
        resolved=ROOT/'reports/2026-10-03-underwater-resolved-normal/Aqualumen-ShoreProbe-world-underwater-resolved-normal-086-phase120-v1.zip'
        with tempfile.TemporaryDirectory(prefix='aqualumen-light-disable-') as temporary:
            output=build_pack(ROOT,Path(temporary)/'stub.zip')
            with ZipFile(output) as archive:
                fs=archive.read('shaders/gbuffers_water.fsh').decode()
            for tag in ('AQUALUMEN_RESIDUAL_HOOK','AQUALUMEN_RESIDUAL_INCLUDE'):
                begin='// '+tag+'_BEGIN\n'
                end='// '+tag+'_END\n'
                at=fs.index(begin)
                finish=fs.index(end,at)+len(end)
                fs=fs[:at]+fs[finish:]
            with ZipFile(resolved) as archive:
                self.assertEqual(fs.encode(),archive.read('shaders/gbuffers_water.fsh'))

    def test_public_builder_rejects_modified_stub_without_writing_destination(self):
        from water_residual_light_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-light-unapproved-') as temporary:
            root=Path(temporary)/'fixture-root'
            parent=root/'reports/2026-10-03-water-residual-angular/baseline-guard-v2-pack.zip'
            helper=root/'shaders/lib/water_residual_light.glsl'
            parent.parent.mkdir(parents=True)
            parent.write_bytes(BASE.read_bytes())
            helper.parent.mkdir(parents=True)
            helper.write_bytes((ROOT/'shaders/lib/water_residual_light.glsl').read_bytes().replace(b'WLS_active=false;',b'WLS_active=true;'))
            output=root/'new-output-dir'/'bad.zip'
            with self.assertRaises(ValueError):
                build_pack(root,output)
            self.assertFalse(output.parent.exists())

    def test_public_pack_stub_requests_only_enabled_eligible_sharp_source_kinds(self):
        with ZipFile(STUB) as archive:
            helper=archive.read('shaders/lib/water_residual_light.glsl').decode()
            metadata=json.loads(archive.read('WATER-RESIDUAL-LIGHT.json'))
        self.assertIn('eligible && WLS_LIGHT_ENABLED!=0 && (WLS_SOURCE_KIND==0 || WLS_SOURCE_KIND==1)',helper)
        self.assertEqual(metadata['WLS_status_channels'],['requested','featureApplied','sourceKind','rejectionCount'])

    def test_public_cli_new_stub_preserves_every_parent_byte_except_recoverable_fs(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-light-pack-') as temporary:
            output=Path(temporary)/'stub.zip'
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(output)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,str(output)+'\n')
            with ZipFile(BASE) as archive:
                parent={name:archive.read(name) for name in archive.namelist()}
            with ZipFile(output) as archive:
                child={name:archive.read(name) for name in archive.namelist()}
            self.assertTrue(parent.keys()<=child.keys())
            for name,value in parent.items():
                if name!='shaders/gbuffers_water.fsh':
                    self.assertEqual(child[name],value,name)
            fs=child['shaders/gbuffers_water.fsh'].decode()
            for tag in ('AQUALUMEN_LIGHT_INCLUDE','AQUALUMEN_LIGHT_RESTORE_ENV','AQUALUMEN_LIGHT_CALL_BEGIN_ALIAS','AQUALUMEN_LIGHT_CALL_END_ALIAS'):
                start='// '+tag+'_BEGIN\n'
                end='// '+tag+'_END\n'
                self.assertEqual(fs.count(start),1)
                self.assertEqual(fs.count(end),1)
                at=fs.index(start)
                finish=fs.index(end,at)+len(end)
                fs=fs[:at]+fs[finish:]
            self.assertEqual(fs,parent['shaders/gbuffers_water.fsh'].decode())
            # The literal old call survives: outer tagged disable recovery stays
            # compatible with the already frozen actual-main renderer loader.
            self.assertEqual(child['shaders/gbuffers_water.fsh'].count(b'color=waterResidualInterface('),1)
            metadata=json.loads(child['WATER-RESIDUAL-LIGHT.json'])
            self.assertEqual(metadata['parent_pack_sha256'],hashlib.sha256(BASE.read_bytes()).hexdigest())
            self.assertIs(type(metadata['stub_only']),bool)
            self.assertTrue(metadata['test_only'])
            self.assertTrue(metadata['not_shipping'])
            for field in ('runtime_accepted','energy_accepted','reciprocity_accepted','visual_accepted','shipping_fix'):
                self.assertFalse(metadata[field])
            helper=child['shaders/lib/water_residual_light.glsl']
            self.assertEqual(helper,(ROOT/'shaders/lib/water_residual_light.glsl').read_bytes())
            self.assertEqual(hashlib.sha256(helper).hexdigest(),metadata['light_helper_sha256'])
            self.assertIn(b'WLS_active=false;',helper)
            self.assertIn(b'waterResidualInterface(originalColor,meanNormal,viewToEye,',helper)
            self.assertIn(b'vec3 full=environmentSkyRadiance(ray,lut);',helper)
            self.assertIn(b'return WLS_active?base:full;',helper)


if __name__=='__main__':
    unittest.main(verbosity=2)
