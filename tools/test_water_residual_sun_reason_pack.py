"""Public source-package tests; CPU-only, never shader/runtime acceptance."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=Path(__file__).with_name('water_residual_sun_reason_pack.py')
PARENT=ROOT/'reports/2026-10-03-water-residual-sun-iris/cpu-pack/Aqualumen-ShoreProbe-world-native-sun-iris-enabled1-v1.zip'
SUN='shaders/lib/water_residual_sun.glsl'
HELPER_SHA='a0708a5d59dfb126473bf51c033f7f76b7d7edcdcf258303f35593f3a91196c3'


def strip_helper(source):
    return re.sub(r'// AQUALUMEN_SUN_REASONS_BEGIN:([A-Z]+)\n.*?// AQUALUMEN_SUN_REASONS_END:\1\n','',source,flags=re.S)


class SunReasonPackTests(unittest.TestCase):
    def test_public_cli_constructs_reason_observer_with_exact_helper_and_physical_recovery(self):
        with tempfile.TemporaryDirectory(prefix='sun-reason-pack-cpu-') as temporary:
            output=Path(temporary)/'test.zip'
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(output)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            with ZipFile(PARENT) as parent,ZipFile(output) as archive:
                metadata=json.loads(archive.read('WATER-RESIDUAL-SUN-REASONS.json'))
                self.assertEqual(metadata['schema'],'aqualumen-water-residual-sun-reasons-v1')
                helper=archive.read(SUN).decode()
                self.assertEqual(strip_helper(helper).encode(),parent.read(SUN))
                self.assertEqual(hashlib.sha256(strip_helper(helper).encode()).hexdigest(),HELPER_SHA)
                self.assertEqual(archive.read('PARENT-SUN-REASONS-helper.glsl'),parent.read(SUN))
                physical=archive.read('PARENT-SUN-REASONS-physical.fsh')
                self.assertEqual(physical,parent.read('PARENT-SUN-IRIS-physical.fsh'))
                water=archive.read('shaders/gbuffers_water.fsh').decode()
                recovered=re.sub(r'// AQUALUMEN_SUN_REASONS_STORE_BEGIN\n.*?// AQUALUMEN_SUN_REASONS_STORE_END\n','',water,flags=re.S)
                self.assertEqual(recovered.encode(),physical)
                self.assertIn('gl_FragData[1]=WNS_reasons;',water)
                for key in ('shipping_fix','runtime_accepted','GL_neutrality_verified','physics_accepted','pixel_AA_equivalence_accepted'):
                    self.assertIs(metadata[key],False,key)

    def test_public_pack_distinguishes_reflected_from_transmitted_hemisphere_without_optical_change(self):
        with tempfile.TemporaryDirectory(prefix='sun-reason-category-cpu-') as temporary:
            output=Path(temporary)/'test.zip'
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(output)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            with ZipFile(output) as archive:
                metadata=json.loads(archive.read('WATER-RESIDUAL-SUN-REASONS.json'))
                self.assertEqual(metadata['reason_categories']['3'],'reflected_hemisphere')
                self.assertEqual(metadata['reason_categories']['9'],'transmission_hemisphere')
                self.assertEqual(metadata['reason_groups']['hemisphere'],[3,9])
                helper=archive.read(SUN).decode()
                self.assertIn('WNS_recordReason(reasonInverse?(transmitted.y>0.0?3.0:9.0):4.0);',helper)
                self.assertIn('if (reason==3.0 || reason==9.0) WNS_reasons.y+=1.0;',helper)
                self.assertEqual(hashlib.sha256(strip_helper(helper).encode()).hexdigest(),HELPER_SHA)
                self.assertIn('probeNormal.x/9.0',archive.read('shaders/final.fsh').decode())

    def test_public_pack_preserves_every_parent_member_except_diagnostic_helper_fs_and_panels(self):
        from water_residual_sun_reason_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='sun-reason-originals-cpu-') as temporary:
            output=build_pack(ROOT,Path(temporary)/'test.zip')
            with ZipFile(PARENT) as parent,ZipFile(output) as archive:
                for name in parent.namelist():
                    if name not in (SUN,'shaders/gbuffers_water.fsh','shaders/final.fsh'):
                        self.assertEqual(archive.read(name),parent.read(name),name)
                metadata=json.loads(archive.read('WATER-RESIDUAL-SUN-REASONS.json'))
                self.assertEqual(metadata['minimum_qualified_applied_points'],4)
                self.assertEqual(len(metadata['fixed_texel_coordinates']),16)
                self.assertTrue(metadata['loop_only'])
                self.assertFalse(metadata['pre_or_post_loop_rejection_categorized'])
                self.assertFalse(metadata['coefficient_telemetry_current'])
                helper=archive.read(SUN).decode()
                self.assertEqual(helper.count('if (!nodeValid) { valid=false; WNS_status.w+=1.0; continue; }'),5)
                self.assertIn('float reason=kind==1?6.0:(!(reflection.a<=0.0)?7.0:8.0);',helper)
                self.assertIn('if (WNS_reasons.x==0.0) WNS_reasons.x=reason;',helper)
                water=archive.read('shaders/gbuffers_water.fsh').decode()
                self.assertIn('gl_FragData[2]=WNS_status;',water)
                self.assertIn('gl_FragData[4]=tessStageCoord;',water)

    def test_public_api_rejects_overwrite_dangling_and_shipping_aliases(self):
        from water_residual_sun_reason_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='sun-reason-paths-cpu-') as temporary:
            directory=Path(temporary);output=directory/'existing.zip';output.write_bytes(b'user-owned')
            with self.assertRaises(FileExistsError): build_pack(ROOT,output)
            self.assertEqual(output.read_bytes(),b'user-owned')
            dangling=directory/'dangling.zip';dangling.symlink_to(directory/'absent.zip')
            with self.assertRaises(FileExistsError): build_pack(ROOT,dangling)
            for target in (ROOT/'shaders',ROOT/'dist'):
                alias=directory/target.name;alias.symlink_to(target,target_is_directory=True)
                with self.assertRaises(ValueError): build_pack(ROOT,alias/'sun-reason-cpu-forbidden.zip')
            self.assertFalse((ROOT/'shaders/sun-reason-cpu-forbidden.zip').exists())
            self.assertFalse((ROOT/'dist/sun-reason-cpu-forbidden.zip').exists())

    def test_public_api_rejects_tampered_or_malformed_parent_before_any_output(self):
        from water_residual_sun_reason_pack import build_pack,PARENT_RELATIVE
        with ZipFile(PARENT) as archive: original={i.filename:archive.read(i) for i in archive.infolist()}
        for name,changed in ((SUN,b'// tampered helper\n'),('shaders/gbuffers_water.fsh',b'// missing STORE\n')):
            with self.subTest(name=name),tempfile.TemporaryDirectory(prefix='sun-reason-tamper-cpu-') as temporary:
                root=Path(temporary);parent=root/PARENT_RELATIVE;parent.parent.mkdir(parents=True)
                files={**original,name:changed}
                with ZipFile(parent,'w') as archive:
                    for n,b in files.items(): archive.writestr(n,b)
                output=root/'absent-output-directory/test.zip'
                before=parent.read_bytes()
                with self.assertRaises(ValueError): build_pack(root,output)
                self.assertFalse(output.parent.exists());self.assertEqual(parent.read_bytes(),before)

    def test_public_api_atomic_link_collision_preserves_winner_and_removes_own_scratch(self):
        from water_residual_sun_reason_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='sun-reason-link-cpu-') as temporary:
            directory=Path(temporary);output=directory/'winner.zip'
            def racing_link(scratch,destination):
                Path(destination).write_bytes(b'concurrent-winner')
                raise FileExistsError('synthetic filesystem-boundary race')
            with patch('water_residual_sun_reason_pack.os.link',side_effect=racing_link):
                with self.assertRaises(FileExistsError): build_pack(ROOT,output)
            self.assertEqual(output.read_bytes(),b'concurrent-winner')
            self.assertEqual([p.name for p in directory.iterdir()],['winner.zip'])


if __name__=='__main__':unittest.main()
