"""CPU public CAP snapshot/recovery tests; no GL or physics acceptance."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=Path(__file__).with_name('water_residual_sun_cap_pack.py')
STUB=ROOT/'reports/2026-10-03-water-residual-native-sun/cpu-pack-stub/Aqualumen-ShoreProbe-world-water-residual-native-sun-stub-v1.zip'
GUARD=ROOT/'reports/2026-10-03-water-residual-angular/baseline-guard-v2-pack.zip'
RESOLVED=ROOT/'reports/2026-10-03-underwater-resolved-normal/Aqualumen-ShoreProbe-world-underwater-resolved-normal-086-phase120-v1.zip'
MEMBER='shaders/lib/water_residual_sun.glsl'
CAP='shaders/lib/water_residual_sun_cap.glsl'


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


class SunCapPackTests(unittest.TestCase):
    def test_public_builder_rejects_unapproved_cap_helper_before_output_writes(self):
        from water_residual_sun_cap_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-sun-cap-helper-') as temporary:
            root=Path(temporary)
            parent=root/'reports/2026-10-03-water-residual-native-sun/cpu-pack-stub/Aqualumen-ShoreProbe-world-water-residual-native-sun-stub-v1.zip'
            parent.parent.mkdir(parents=True)
            parent.write_bytes(STUB.read_bytes())
            helper=root/CAP
            helper.parent.mkdir(parents=True)
            helper.write_bytes((ROOT/CAP).read_bytes().replace(b'determinant>0.0',b'determinant>=0.0'))
            output=root/'new-output-dir'/'bad.zip'
            with self.assertRaises(ValueError):
                build_pack(root,output)
            self.assertFalse(output.parent.exists())

    def test_public_builder_rejects_changed_frozen_stub_before_output_writes(self):
        from water_residual_sun_cap_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-sun-cap-parent-') as temporary:
            root=Path(temporary)
            parent=root/'reports/2026-10-03-water-residual-native-sun/cpu-pack-stub/Aqualumen-ShoreProbe-world-water-residual-native-sun-stub-v1.zip'
            parent.parent.mkdir(parents=True)
            with ZipFile(STUB) as archive,ZipFile(parent,'w') as changed:
                for name in archive.namelist():
                    value=archive.read(name)
                    if name=='shaders/gbuffers_water.fsh':
                        value=value.replace(b'AQUALUMEN_SUN_INCLUDE_BEGIN',b'MALFORMED_SUN_INCLUDE_BEGIN')
                    changed.writestr(name,value)
            output=root/'new-output-dir'/'bad.zip'
            with self.assertRaises(ValueError):
                build_pack(root,output)
            self.assertFalse(output.parent.exists())

    def test_public_builder_preserves_existing_files_and_rejects_shipping_aliases(self):
        from water_residual_sun_cap_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-sun-cap-paths-') as temporary:
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

    def test_public_pack_keeps_pinned_positive_rules_raw_inputs_and_saved_full_fallback(self):
        from water_residual_sun_cap_pack import build_pack
        import re
        rules_path=ROOT/'reports/2026-10-03-water-residual-native-sun/cpu-integral/gauss-legendre-cap-rules.json'
        math_path=ROOT/'tools/water_residual_sun_integral.py'
        rules=json.loads(rules_path.read_bytes())['rules']['4']
        with tempfile.TemporaryDirectory(prefix='aqualumen-sun-cap-rules-') as temporary:
            output=build_pack(ROOT,Path(temporary)/'cap.zip')
            with ZipFile(output) as archive:
                helper=archive.read(MEMBER).decode()
                metadata=json.loads(archive.read('WATER-RESIDUAL-SUN-CAP.json'))
        self.assertEqual(metadata['cap_rules_sha256'],hashlib.sha256(rules_path.read_bytes()).hexdigest())
        self.assertEqual(metadata['cpu_source_math_sha256'],hashlib.sha256(math_path.read_bytes()).hexdigest())
        for name,expected in (('radial',rules['nodes']),('weights',rules['weights'])):
            text=re.search(r'const float '+name+r'\[4\]=float\[4\]\((.*?)\);',helper,re.S).group(1)
            self.assertEqual([float(v.strip()) for v in text.split(',')],expected)
        wrapper=helper[helper.index('vec3 waterResidualSunInterface('):]
        branch=wrapper.index('if (!candidate)')
        self.assertLess(wrapper.index('vec3 full=waterResidualInterface('),branch)
        self.assertLess(wrapper.index('vec3 base=waterResidualInterface('),branch)
        self.assertEqual(wrapper.count('waterResidualInterface('),2)
        self.assertNotIn('waterResidualInterface(',wrapper[branch:])
        self.assertIn('if (requested && (!beamValid || sourcePresent)) WNS_status.w=1.0;',wrapper)
        self.assertIn('bool candidate=requested && sourcePresent && inverseValid;',wrapper)
        self.assertIn('WNS_status.y=1.0;',wrapper)
        self.assertIn('determinant>0.0',wrapper)
        self.assertNotIn('max(determinant',wrapper)
        self.assertNotIn('normalize(meanNormal)',wrapper)
        self.assertNotIn('normalize(viewToEye)',wrapper)
        self.assertIn('1.0+eta*eta*(dot(viewToEye,viewToEye)-1.0)',wrapper)
        self.assertIn('vec3 target=normalize(',wrapper)
        self.assertIn('float radius=SUN_ANGULAR_RADIUS;',wrapper)
        self.assertIn('integral*=capDelta*TAU/12.0;',wrapper)
        self.assertIn('vec3 result=base+beam*(integral/projectedArea);',wrapper)
        self.assertIn('return full;',wrapper[wrapper.index('if (!valid)'):])
        self.assertLess(helper.index('vec3 full=environmentSkyRadiance('),helper.index('return WNS_active?base:full;'))
        self.assertLess(helper.index('vec3 base=sampleSky(lut,ray)+moonDisk('),helper.index('return WNS_active?base:full;'))

    def test_public_cli_replaces_only_stub_helper_with_truthful_cap_snapshot(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-sun-cap-pack-') as temporary:
            output=Path(temporary)/'cap.zip'
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(output)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,str(output)+'\n')
            with ZipFile(STUB) as archive:
                parent={name:archive.read(name) for name in archive.namelist()}
            with ZipFile(output) as archive:
                child={name:archive.read(name) for name in archive.namelist()}
            self.assertTrue(parent.keys()<=child.keys())
            for name,value in parent.items():
                if name!=MEMBER:
                    self.assertEqual(child[name],value,name)
            self.assertEqual(child[MEMBER],(ROOT/CAP).read_bytes())
            self.assertNotEqual(child[MEMBER],parent[MEMBER])
            metadata=json.loads(child['WATER-RESIDUAL-SUN-CAP.json'])
            self.assertEqual(metadata['schema'],'aqualumen-water-residual-sun-cap-v1')
            self.assertEqual(metadata['mode'],'residual-native-sun-sharp-cap')
            self.assertTrue(metadata['test_only'])
            self.assertTrue(metadata['not_shipping'])
            self.assertFalse(metadata['stub_only'])
            self.assertEqual(metadata['parent_stub_pack_sha256'],hashlib.sha256(STUB.read_bytes()).hexdigest())
            self.assertEqual(metadata['sun_cap_helper_sha256'],hashlib.sha256(child[MEMBER]).hexdigest())
            self.assertEqual(metadata['helper_input_path'],CAP)
            self.assertEqual(metadata['helper_archive_member'],MEMBER)
            self.assertEqual(metadata['radial_order'],4)
            self.assertEqual(metadata['azimuth_order'],12)
            self.assertTrue(metadata['parent_stub_metadata_is_provenance_only'])
            for field in ('runtime_accepted','energy_accepted','reciprocity_accepted','visual_accepted','shipping_fix','pixel_AA_equivalence_accepted','pack_enforces_world_guard'):
                self.assertFalse(metadata[field])
            fs=child['shaders/gbuffers_water.fsh'].decode()
            tags=('AQUALUMEN_SUN_INCLUDE','AQUALUMEN_SUN_RESTORE_ENV',
                  'AQUALUMEN_SUN_CALL_BEGIN_ALIAS','AQUALUMEN_SUN_CALL_END_ALIAS')
            with ZipFile(GUARD) as archive:
                self.assertEqual(remove_tags(fs,tags).encode(),archive.read('shaders/gbuffers_water.fsh'))
            with ZipFile(RESOLVED) as archive:
                self.assertEqual(remove_tags(fs,('AQUALUMEN_RESIDUAL_HOOK','AQUALUMEN_RESIDUAL_INCLUDE')).encode(),archive.read('shaders/gbuffers_water.fsh'))


if __name__=='__main__':
    unittest.main(verbosity=2)
