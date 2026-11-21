"""CPU public packaging/recovery contracts, not renderer or cap acceptance."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=Path(__file__).with_name('water_residual_sun_pack.py')
BASE=ROOT/'reports/2026-10-03-water-residual-angular/baseline-guard-v2-pack.zip'
RESOLVED=ROOT/'reports/2026-10-03-underwater-resolved-normal/Aqualumen-ShoreProbe-world-underwater-resolved-normal-086-phase120-v1.zip'
TAGS=('AQUALUMEN_SUN_INCLUDE','AQUALUMEN_SUN_RESTORE_ENV',
      'AQUALUMEN_SUN_CALL_BEGIN_ALIAS','AQUALUMEN_SUN_CALL_END_ALIAS')


def remove_tags(source,tags):
    for tag in tags:
        begin='// '+tag+'_BEGIN\n'
        end='// '+tag+'_END\n'
        if source.count(begin)!=1 or source.count(end)!=1:
            raise AssertionError('Expected one removable block: '+tag)
        at=source.index(begin)
        finish=source.index(end,at)+len(end)
        source=source[:at]+source[finish:]
    return source


class SunPackTests(unittest.TestCase):
    def test_public_pack_stub_keeps_native_source_derivative_order_and_legacy_arguments(self):
        from water_residual_sun_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-native-sun-source-') as temporary:
            output=build_pack(ROOT,Path(temporary)/'stub.zip')
            with ZipFile(output) as archive:
                helper=archive.read('shaders/lib/water_residual_sun.glsl').decode()
                fs=archive.read('shaders/gbuffers_water.fsh').decode()
                metadata=json.loads(archive.read('WATER-RESIDUAL-SUN.json'))
        self.assertIn('#define NATIVE_SUN_ENABLED 1',helper)
        self.assertIn('bool requested=eligible && NATIVE_SUN_ENABLED!=0;',helper)
        self.assertIn('WNS_status=vec4(float(requested),0.0,0.0,0.0);',helper)
        self.assertNotIn('WNS_active=true',helper)
        self.assertNotIn('WNS_status.y=1',helper)
        self.assertIn('return waterResidualInterface(originalColor,meanNormal,viewToEye,\n'
                      '        relativePosition,viewOrigin,effectiveFootprint,columnDepth,\n'
                      '        skyAccess,caveAmbient,scatter,eligible);',helper)
        select=helper.index('return WNS_active?base:full;')
        self.assertLess(helper.index('vec3 full=environmentSkyRadiance(ray,lut);'),select)
        self.assertLess(helper.index('vec3 base=sampleSky(lut,ray)+moonDisk(ray,sunDirection());'),select)
        self.assertLess(fs.index('#include "/lib/water_residual_sun.glsl"'),fs.index('#define environmentSkyRadiance WNS_baseSky'))
        self.assertLess(fs.index('#define environmentSkyRadiance WNS_baseSky'),fs.index('#include "/lib/water_residual.glsl"'))
        self.assertLess(fs.index('#include "/lib/water_residual.glsl"'),fs.index('#undef environmentSkyRadiance'))
        self.assertIn('bool WNS_legacyApplied() { return WR_status.y==1.0; }',fs)
        self.assertIn('#define waterResidualInterface waterResidualSunInterface',fs)
        self.assertNotIn('water_residual_light.glsl',fs)
        for field in ('atmosphere_source_changed','source_return_replaced','scatter_policy_changed','scalar_units_changed','native_sun_implemented'):
            self.assertFalse(metadata[field])

    def test_public_builder_rejects_unapproved_sun_helper_without_output(self):
        from water_residual_sun_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-native-sun-helper-') as temporary:
            root=Path(temporary)
            parent=root/'reports/2026-10-03-water-residual-angular/baseline-guard-v2-pack.zip'
            helper=root/'shaders/lib/water_residual_sun.glsl'
            parent.parent.mkdir(parents=True)
            parent.write_bytes(BASE.read_bytes())
            helper.parent.mkdir(parents=True)
            helper.write_bytes((ROOT/'shaders/lib/water_residual_sun.glsl').read_bytes().replace(b'WNS_active=false;',b'WNS_active=true;'))
            output=root/'new-output-dir'/'bad.zip'
            with self.assertRaises(ValueError):
                build_pack(root,output)
            self.assertFalse(output.parent.exists())

    def test_public_builder_rejects_malformed_parent_seams_at_digest_gate_without_output(self):
        from water_residual_sun_pack import build_pack
        with ZipFile(BASE) as archive:
            files={name:archive.read(name) for name in archive.namelist()}
        for before,after in ((b'#include "/lib/water_residual.glsl"',b'#include "/lib/malformed.glsl"'),
                             (b'color=waterResidualInterface(',b'color=malformedResidualInterface(')):
            with self.subTest(seam=before),tempfile.TemporaryDirectory(prefix='aqualumen-native-sun-seam-') as temporary:
                root=Path(temporary)
                parent=root/'reports/2026-10-03-water-residual-angular/baseline-guard-v2-pack.zip'
                parent.parent.mkdir(parents=True)
                changed=files['shaders/gbuffers_water.fsh'].replace(before,after)
                self.assertNotEqual(changed,files['shaders/gbuffers_water.fsh'])
                with ZipFile(parent,'w') as archive:
                    for name,value in files.items():
                        archive.writestr(name,changed if name=='shaders/gbuffers_water.fsh' else value)
                output=root/'new-output-dir'/'bad.zip'
                with self.assertRaises(ValueError):
                    build_pack(root,output)
                self.assertFalse(output.parent.exists())

    def test_public_builder_rejects_overwrite_and_shipping_aliases_before_reading_sources(self):
        from water_residual_sun_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-native-sun-paths-') as temporary:
            folder=Path(temporary)
            root=folder/'root'
            root.mkdir()
            existing=folder/'user.zip'
            existing.write_bytes(b'user-owned unchanged')
            with self.assertRaises(FileExistsError):
                build_pack(root,existing)
            self.assertEqual(existing.read_bytes(),b'user-owned unchanged')
            dangling=folder/'dangling.zip'
            dangling.symlink_to(folder/'missing.zip')
            with self.assertRaises(FileExistsError):
                build_pack(root,dangling)
            self.assertTrue(dangling.is_symlink())
            alias=folder/'alias'
            alias.symlink_to(root/'shaders',target_is_directory=True)
            for output in (root/'shaders'/'bad.zip',root/'dist'/'bad.zip',alias/'bad.zip'):
                with self.subTest(output=output):
                    with self.assertRaises(ValueError):
                        build_pack(root,output)
                    self.assertFalse(output.exists())
            self.assertEqual(list(root.iterdir()),[])

    def test_public_cli_new_native_stub_preserves_parent_and_exact_disable_recovery(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-native-sun-pack-') as temporary:
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
            self.assertEqual(remove_tags(fs,TAGS).encode(),parent['shaders/gbuffers_water.fsh'])
            disabled=remove_tags(fs,('AQUALUMEN_RESIDUAL_HOOK','AQUALUMEN_RESIDUAL_INCLUDE'))
            with ZipFile(RESOLVED) as archive:
                self.assertEqual(disabled.encode(),archive.read('shaders/gbuffers_water.fsh'))
            self.assertEqual(fs.count('color=waterResidualInterface('),1)
            metadata=json.loads(child['WATER-RESIDUAL-SUN.json'])
            self.assertEqual(metadata['schema'],'aqualumen-water-residual-sun-v1')
            self.assertEqual(metadata['mode'],'residual-native-sun-stub')
            self.assertEqual(metadata['parent_pack_sha256'],hashlib.sha256(BASE.read_bytes()).hexdigest())
            self.assertTrue(metadata['test_only'])
            self.assertTrue(metadata['not_shipping'])
            self.assertTrue(metadata['stub_only'])
            self.assertEqual(metadata['WNS_status_channels'],['requested','featureApplied','sourceKind','rejectionCount'])
            self.assertEqual(metadata['WNS_feature_applied_stub'],0)
            self.assertEqual(metadata['supported_source_kinds'],[])
            for field in ('runtime_accepted','energy_accepted','reciprocity_accepted','visual_accepted','shipping_fix','pack_enforces_world_guard'):
                self.assertFalse(metadata[field])
            helper=child['shaders/lib/water_residual_sun.glsl']
            self.assertEqual(helper,(ROOT/'shaders/lib/water_residual_sun.glsl').read_bytes())
            self.assertEqual(hashlib.sha256(helper).hexdigest(),metadata['sun_helper_sha256'])
            self.assertEqual(hashlib.sha256(child['shaders/lib/atmosphere.glsl']).hexdigest(),metadata['atmosphere_sha256'])


if __name__=='__main__':
    unittest.main(verbosity=2)
