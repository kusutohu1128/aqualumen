"""CPU public guarded observation packaging; no renderer or Mod qualification."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=Path(__file__).with_name('water_residual_sun_iris_pack.py')
CAP=ROOT/'reports/2026-10-03-water-residual-native-sun/cpu-pack-cap/Aqualumen-ShoreProbe-world-water-residual-native-sun-cap-v1.zip'
PHYSICAL='PARENT-SUN-IRIS-physical.fsh'
STORE=('// AQUALUMEN_SUN_IRIS_OBSERVE_STORE_BEGIN\n'
       '    gl_FragData[1]=WR_coefficients;\n'
       '    gl_FragData[2]=WNS_status;\n'
       '    gl_FragData[3]=vec4(WR_covariance,float(localColumnKnown)+2.0*float(upperSurface)+4.0*float(underwater)+8.0*float(residualEligible));\n'
       '// AQUALUMEN_SUN_IRIS_OBSERVE_STORE_END\n')


def remove_block(source,tag,replacement=''):
    begin='// '+tag+'_BEGIN\n'
    end='// '+tag+'_END\n'
    if source.count(begin)!=1 or source.count(end)!=1:
        raise AssertionError('Expected one removable block: '+tag)
    at=source.index(begin)
    finish=source.index(end,at)+len(end)
    return source[:at]+replacement+source[finish:]


class SunIrisPackTests(unittest.TestCase):
    def test_public_observation_uses_actual_fields_original_flags_and_truthful_panels(self):
        from water_residual_sun_iris_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-sun-iris-observation-') as temporary:
            output=build_pack(ROOT,Path(temporary)/'observed.zip')
            with ZipFile(output) as archive:
                fs=archive.read('shaders/gbuffers_water.fsh').decode()
                final=archive.read('shaders/final.fsh').decode()
                metadata=json.loads(archive.read('WATER-RESIDUAL-SUN-IRIS.json'))
                sun=archive.read('shaders/lib/water_residual_sun.glsl').decode()
                legacy=archive.read('shaders/lib/water_residual.glsl').decode()
        self.assertTrue(fs.endswith(STORE+'}\n'))
        self.assertEqual(fs.count('    gl_FragData[4]=tessStageCoord;\n'),1)
        self.assertIn('vec4 WNS_status=vec4(0.0);',sun)
        self.assertIn('vec4 WR_coefficients=vec4(0.0);',legacy)
        self.assertIn('vec3 WR_covariance=vec3(0.0);',legacy)
        self.assertEqual(metadata['production_flags'],{'known':1,'upper':2,'underwater':4,'residualEligible':8})
        self.assertEqual(metadata['production_flags_range'],[0,15])
        self.assertIn('flags15 does not prove authorization',metadata['flags_scope'])
        self.assertIn('not directly exported',metadata['legacy_status_scope'])
        self.assertIn('pow(tone(texture(colortex0,q).rgb),vec3(1.0/2.2))',final)
        self.assertIn('probeStage.a<0.5',final)
        self.assertIn('panel=probeNormal.yzw;',final)
        self.assertIn('panel=vec3(probeState.x,probeState.y,rejected/(rejected+1.0));',final)
        self.assertIn('probeReflection.w/15.0',final)
        self.assertNotIn('else if (probeState.z<0.5)',final)
        self.assertFalse(metadata['FS_C0_source_observation_changed'])
        self.assertFalse(metadata['cap_helper_source_changed'])

    def test_public_builder_rejects_malformed_frozen_cap_before_output_writes(self):
        from water_residual_sun_iris_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-sun-iris-parent-') as temporary:
            root=Path(temporary)
            parent=root/'reports/2026-10-03-water-residual-native-sun/cpu-pack-cap/Aqualumen-ShoreProbe-world-water-residual-native-sun-cap-v1.zip'
            parent.parent.mkdir(parents=True)
            with ZipFile(CAP) as archive,ZipFile(parent,'w') as changed:
                for name in archive.namelist():
                    value=archive.read(name)
                    if name=='shaders/gbuffers_water.fsh':
                        value=value.replace(b'color=waterResidualInterface(',b'color=malformedCall(')
                    changed.writestr(name,value)
            output=root/'new-output-dir'/'bad.zip'
            with self.assertRaises(ValueError):
                build_pack(root,output)
            self.assertFalse(output.parent.exists())

    def test_public_builder_preserves_existing_file_and_rejects_shipping_aliases(self):
        from water_residual_sun_iris_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-sun-iris-paths-') as temporary:
            folder=Path(temporary)
            root=folder/'empty-root'
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

    def test_public_api_and_cli_reject_invalid_enabled_before_output_creation(self):
        from water_residual_sun_iris_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-sun-iris-enabled-') as temporary:
            root=Path(temporary)/'empty-root'
            for invalid in (-1,2,True,False,1.0,None,'1'):
                with self.subTest(invalid=invalid):
                    output=Path(temporary)/'new-output-dir'/'bad.zip'
                    with self.assertRaises(ValueError):
                        build_pack(root,output,invalid)
                    self.assertFalse(output.parent.exists())
            output=Path(temporary)/'cli-output'/'bad.zip'
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(output),'--enabled','2'],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(output.parent.exists())

    def test_public_both_enabled_modes_recover_cap_guard_and_resolved_parents_exactly(self):
        from water_residual_sun_iris_pack import build_pack
        with ZipFile(CAP) as archive:
            cap_water=archive.read('shaders/gbuffers_water.fsh')
            cap_final=archive.read('shaders/final.fsh')
        old_call=('    color=waterResidualInterface(color,n,v,worldPosition,viewPos,max(footprint*1.25,0.035),\n'
                  '        localColumnKnown?localColumn.x:0.0,skyAccess,caveAmbient,scatter,residualEligible);\n')
        guard=ROOT/'reports/2026-10-03-water-residual-angular/baseline-guard-v2-pack.zip'
        resolved=ROOT/'reports/2026-10-03-underwater-resolved-normal/Aqualumen-ShoreProbe-world-underwater-resolved-normal-086-phase120-v1.zip'
        with tempfile.TemporaryDirectory(prefix='aqualumen-sun-iris-recovery-') as temporary:
            physicals=[]
            for enabled in (0,1):
                output=build_pack(ROOT,Path(temporary)/('enabled'+str(enabled)+'.zip'),enabled)
                with ZipFile(output) as archive:
                    observed=archive.read('shaders/gbuffers_water.fsh').decode()
                    physical=archive.read(PHYSICAL).decode()
                    metadata=json.loads(archive.read('WATER-RESIDUAL-SUN-IRIS.json'))
                    self.assertEqual(archive.read('PARENT-SUN-IRIS-final.fsh'),cap_final)
                self.assertEqual(metadata['enabled'],enabled)
                self.assertIn('#define NATIVE_SUN_ENABLED '+str(enabled)+'\n',physical)
                self.assertEqual(remove_block(observed,'AQUALUMEN_SUN_IRIS_OBSERVE_STORE'),physical)
                recovered=remove_block(physical,'AQUALUMEN_SUN_IRIS_GUARD_CALL',old_call)
                for tag in ('AQUALUMEN_SUN_IRIS_GUARD_UNIFORM','AQUALUMEN_SUN_IRIS_CONFIG'):
                    recovered=remove_block(recovered,tag)
                self.assertEqual(recovered.encode(),cap_water)
                physicals.append(physical)
                sun_disabled=recovered
                for tag in ('AQUALUMEN_SUN_INCLUDE','AQUALUMEN_SUN_RESTORE_ENV',
                            'AQUALUMEN_SUN_CALL_BEGIN_ALIAS','AQUALUMEN_SUN_CALL_END_ALIAS'):
                    sun_disabled=remove_block(sun_disabled,tag)
                with ZipFile(guard) as archive:
                    self.assertEqual(sun_disabled.encode(),archive.read('shaders/gbuffers_water.fsh'))
                for tag in ('AQUALUMEN_RESIDUAL_HOOK','AQUALUMEN_RESIDUAL_INCLUDE'):
                    recovered=remove_block(recovered,tag)
                with ZipFile(resolved) as archive:
                    self.assertEqual(recovered.encode(),archive.read('shaders/gbuffers_water.fsh'))
            self.assertEqual(physicals[0].replace('#define NATIVE_SUN_ENABLED 0','#define NATIVE_SUN_ENABLED 1'),physicals[1])

    def test_public_cli_builds_caller_guarded_observer_and_exact_physical_fs(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-sun-iris-pack-') as temporary:
            output=Path(temporary)/'guarded.zip'
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(output),'--enabled','1'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,str(output)+'\n')
            with ZipFile(CAP) as archive:
                parent={name:archive.read(name) for name in archive.namelist()}
            with ZipFile(output) as archive:
                child={name:archive.read(name) for name in archive.namelist()}
            self.assertTrue(parent.keys()<=child.keys())
            for name,value in parent.items():
                if name not in ('shaders/gbuffers_water.fsh','shaders/final.fsh'):
                    self.assertEqual(child[name],value,name)
            physical=child[PHYSICAL].decode()
            observed=child['shaders/gbuffers_water.fsh'].decode()
            self.assertEqual(observed.count(STORE),1)
            self.assertEqual(observed.replace(STORE,''),physical)
            self.assertIn('uniform int aqualumenSunTestAuthorized;',physical)
            self.assertIn('    if (aqualumenSunTestAuthorized==1) {\n'
                          '    color=waterResidualInterface(',physical)
            self.assertEqual(physical.count('color=waterResidualInterface('),1)
            self.assertIn('#define NATIVE_SUN_ENABLED 1',physical)
            metadata=json.loads(child['WATER-RESIDUAL-SUN-IRIS.json'])
            self.assertEqual(metadata['schema'],'aqualumen-water-residual-sun-iris-v1')
            self.assertEqual(metadata['mode'],'guarded-native-sun-observe')
            self.assertEqual(metadata['enabled'],1)
            self.assertEqual(metadata['parent_cap_pack_sha256'],hashlib.sha256(CAP.read_bytes()).hexdigest())
            self.assertEqual(metadata['physical_water_fs_member'],PHYSICAL)
            self.assertEqual(metadata['physical_water_fs_sha256'],hashlib.sha256(child[PHYSICAL]).hexdigest())
            self.assertEqual(metadata['target_channels']['10'],['requested','featureApplied','sourceKind','rejectionCount'])
            self.assertEqual(metadata['guard_uniform'],{'name':'aqualumenSunTestAuthorized','glsl_type':'int','required_value':1,'default_if_mod_absent':0})
            self.assertTrue(metadata['test_only'])
            self.assertTrue(metadata['not_shipping'])
            self.assertTrue(metadata['world_guard_requires_mod'])
            for field in ('runtime_accepted','actual_guard_runtime_verified','GL_neutrality_verified','energy_accepted','reciprocity_accepted','visual_accepted','shipping_fix','actual_shader_node_count_qualified'):
                self.assertFalse(metadata[field])


if __name__=='__main__':
    unittest.main(verbosity=2)
