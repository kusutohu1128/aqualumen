"""CPU packaging/source contracts only; not shader execution or neutrality."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile


STORE = (
    '// AQUALUMEN_RESIDUAL_OBSERVE_STORE_BEGIN\n'
    '    gl_FragData[1]=WR_coefficients;\n'
    '    gl_FragData[2]=WR_status;\n'
    '    gl_FragData[3]=vec4(WR_covariance,float(localColumnKnown)+2.0*float(upperSurface)'
    '+4.0*float(underwater)+8.0*float(residualEligible));\n'
    '// AQUALUMEN_RESIDUAL_OBSERVE_STORE_END\n'
)


class ResidualObservePackTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]

    def test_public_cli_observes_actual_main_fields_preserving_physical_parent(self):
        from water_residual_pack import build_pack as build_parent
        before = {p: p.read_bytes() for p in (self.root/'shaders').rglob('*') if p.is_file()}
        with tempfile.TemporaryDirectory(prefix='aqualumen-residual-observe-cpu-') as temporary:
            folder = Path(temporary)
            parent = build_parent(self.root, folder/'parent.zip')
            target = folder/'observe.zip'
            run = subprocess.run([sys.executable, '-B', str(self.root/'tools/water_residual_observe_pack.py'), str(target)],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            with ZipFile(parent) as old, ZipFile(target) as new:
                water = new.read('shaders/gbuffers_water.fsh').decode()
                self.assertEqual(water.count(STORE), 1)
                self.assertEqual(water.replace(STORE, ''), old.read('shaders/gbuffers_water.fsh').decode())
                self.assertLess(water.index('gl_FragData[4]=tessStageCoord;'), water.index(STORE))
                self.assertLess(water.rindex('gl_FragData[1]=vec4(n,'), water.index(STORE))
                self.assertIn('/* RENDERTARGETS:0,9,10,11,12 */', water)
                for name in old.namelist():
                    if (name.startswith('original/') or name.endswith('.json') or
                            name in ('shaders/gbuffers_water.vsh', 'shaders/gbuffers_water.tcs',
                                     'shaders/gbuffers_water.tes', 'shaders/prepare.fsh',
                                     'shaders/shaders.properties', 'shaders/lib/wave_residual.glsl',
                                     'shaders/lib/water_residual.glsl', 'LICENSE')):
                        self.assertEqual(new.read(name), old.read(name), name)
                changed = {'shaders/gbuffers_water.fsh','shaders/final.fsh',
                           'UNDERWATER-PROBE.txt','WATER-TESSELLATION-PROBE.txt',
                           'UNDERWATER-RESOLVED-PROBE.txt','WATER-RESIDUAL-PROBE.txt'}
                for name in set(old.namelist())-changed:
                    self.assertEqual(new.read(name),old.read(name),name)
                metadata = json.loads(new.read('WATER-RESIDUAL-OBSERVE.json'))
                self.assertEqual(metadata['schema'], 'aqualumen-water-residual-observe-v1')
                self.assertEqual(metadata['mode'], 'residual-interface-observe')
                self.assertEqual(metadata['parent_pack_sha256'], hashlib.sha256(parent.read_bytes()).hexdigest())
                self.assertEqual(metadata['parent_metadata_member'], 'WATER-RESIDUAL-PROBE.json')
                self.assertEqual(metadata['parent_metadata_sha256'], hashlib.sha256(old.read('WATER-RESIDUAL-PROBE.json')).hexdigest())
                parent_metadata = json.loads(old.read('WATER-RESIDUAL-PROBE.json'))
                self.assertEqual(metadata['helper_sha256'], parent_metadata['helper_sha256'])
                self.assertEqual(metadata['geometry_factor'], 4)
                self.assertEqual(metadata['fixed_phase_seconds'], 120.0)
                self.assertEqual(metadata['quadrature_order'], 3)
                self.assertNotIn('quadrature_nodes', metadata)
                self.assertEqual(metadata['target_channels']['9'], ['mass','R','T','TIR'])
                self.assertEqual(metadata['target_channels']['10'], ['valid','applied','minFacing','opaqueCount'])
                self.assertEqual(metadata['target_channels']['11'], ['Cxx','Cxz','Czz','productionFlags'])
                self.assertEqual(metadata['production_flags'], {'known':1,'upper':2,'underwater':4,'residualEligible':8})
                self.assertEqual(metadata['production_flags_range'], [0,15])
                self.assertEqual(metadata['production_flags_expression'],
                                 'float(localColumnKnown)+2.0*float(upperSurface)+4.0*float(underwater)+8.0*float(residualEligible)')
                self.assertIs(metadata['test_only'], True)
                self.assertIs(metadata['not_shipping'], True)
                for key in ('shipping_fix', 'GL_neutrality_verified', 'runtime_accepted', 'energy_accepted',
                            'reciprocity_accepted', 'visual_accepted', 'performance_accepted',
                            'generated_geometry_accepted', 'motion_accepted', 'pack_enforces_world_guard',
                            'actual_shader_node_count_qualified', 'parent_metadata_is_current_atlas_policy',
                            'inherited_metadata_is_current_atlas_policy', 'parent_metadata_is_current_optical_policy'):
                    self.assertIs(metadata[key], False, key)
            self.assertEqual(before, {p:p.read_bytes() for p in before})

    def test_public_api_relabels_atlas_and_keeps_exact_parent_final_and_legends(self):
        from water_residual_pack import build_pack as build_parent
        from water_residual_observe_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-residual-observe-display-') as temporary:
            folder = Path(temporary)
            parent = build_parent(self.root,folder/'parent.zip')
            target = build_pack(self.root,folder/'observe.zip')
            with ZipFile(parent) as old, ZipFile(target) as new:
                final = new.read('shaders/final.fsh').decode()
                self.assertIn('panel=probeNormal.yzw;',final)
                self.assertIn('abs(probeNormal.x-1.0)>0.002',final)
                self.assertIn('panel=probeState.rgb;',final)
                self.assertIn('vec3(clamp(probeState.w,0.0,1.0),0.0,0.0)',final)
                self.assertIn('panel=vec3(probeReflection.w/15.0);',final)
                self.assertIn('probeReflection.y/sqrt(',final)
                self.assertNotIn('probeNormal.xyz*0.5+0.5',final)
                self.assertNotIn('probeState.z<0.5',final)
                self.assertIn('pow(tone(texture(colortex0,q).rgb),vec3(1.0/2.2))',final)
                self.assertIn('probeStage.a<0.5',final)
                self.assertEqual(new.read('PARENT-RESIDUAL-OBSERVE-final.fsh'),old.read('shaders/final.fsh'))
                for name in ('UNDERWATER-PROBE.txt','WATER-TESSELLATION-PROBE.txt',
                             'UNDERWATER-RESOLVED-PROBE.txt','WATER-RESIDUAL-PROBE.txt'):
                    self.assertEqual(new.read('PARENT-RESIDUAL-OBSERVE-'+name),old.read(name),name)
                    self.assertIn(b'WATER-RESIDUAL-OBSERVE.json',new.read(name))
                metadata = json.loads(new.read('WATER-RESIDUAL-OBSERVE.json'))
                self.assertIs(metadata['FINAL_atlas_policy_changed'],True)
                self.assertEqual(metadata['parent_final_sha256'],hashlib.sha256(old.read('shaders/final.fsh')).hexdigest())
                legend = new.read('WATER-RESIDUAL-OBSERVE.txt')
                self.assertIn(b'mass,R,T,TIR',legend)
                self.assertIn(b'valid,applied,minFacing,opaqueCount',legend)
                self.assertIn(b'Cxx,Cxz,Czz,productionFlags',legend)
                self.assertIn(b'node count is not observed',legend)

    def test_public_api_rejects_existing_shipping_alias_and_publication_race(self):
        from water_residual_observe_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-residual-observe-guards-') as temporary:
            folder = Path(temporary)
            existing = folder/'existing.zip'
            existing.write_bytes(b'user-owned archive')
            alias = folder/'existing-alias.zip'
            alias.symlink_to(existing)
            dangling = folder/'dangling.zip'
            dangling.symlink_to(folder/'not-present.zip')
            for target in (existing,alias,dangling):
                with self.subTest(target=target.name),self.assertRaises(FileExistsError):
                    build_pack(self.root,target)
            self.assertEqual(existing.read_bytes(),b'user-owned archive')
            self.assertTrue(dangling.is_symlink())
            for name in ('shaders','dist'):
                shipping_alias = folder/(name+'-alias')
                shipping_alias.symlink_to(self.root/name,target_is_directory=True)
                for target in (self.root/name/'observe-forbidden-test.zip',
                               shipping_alias/'observe-forbidden-test.zip'):
                    with self.subTest(target=str(target)),self.assertRaises(ValueError):
                        build_pack(self.root,target)
                    self.assertFalse(target.exists())
            target = folder/'race.zip'
            actual_link = os.link
            def raced_link(source,destination):
                Path(destination).write_bytes(b'concurrent user-owned archive')
                return actual_link(source,destination)
            with patch('water_residual_observe_pack.os.link',side_effect=raced_link):
                with self.assertRaises(FileExistsError):
                    build_pack(self.root,target)
            self.assertEqual(target.read_bytes(),b'concurrent user-owned archive')
            self.assertEqual(list(folder.glob('.residual-observe-*.zip')),[])

    def test_public_api_determinism_and_dynamic_current_helper_provenance(self):
        from water_residual_pack import PARENT_RELATIVE,HELPERS
        from water_residual_observe_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-residual-observe-snapshot-') as temporary:
            folder = Path(temporary)
            fixture = folder/'fixture-root'
            for name in (PARENT_RELATIVE,*map(Path,HELPERS)):
                target = fixture/name
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(self.root/name,target)
            first = build_pack(fixture,folder/'first.zip')
            repeat = build_pack(fixture,folder/'repeat.zip')
            self.assertEqual(first.read_bytes(),repeat.read_bytes())
            helper = fixture/'shaders/lib/water_residual.glsl'
            helper.write_bytes(helper.read_bytes()+b'\n// CPU fixture snapshot changed, no live source change.\n')
            current = build_pack(fixture,folder/'current.zip')
            with ZipFile(first) as old,ZipFile(current) as new:
                old_meta = json.loads(old.read('WATER-RESIDUAL-OBSERVE.json'))
                new_meta = json.loads(new.read('WATER-RESIDUAL-OBSERVE.json'))
                self.assertNotEqual(old_meta['parent_pack_sha256'],new_meta['parent_pack_sha256'])
                self.assertNotEqual(old_meta['helper_sha256'],new_meta['helper_sha256'])
                self.assertEqual(new_meta['helper_sha256']['shaders/lib/water_residual.glsl'],
                                 hashlib.sha256(helper.read_bytes()).hexdigest())
                self.assertEqual(new.read('shaders/lib/water_residual.glsl'),helper.read_bytes())
                for name in ('shaders/gbuffers_water.vsh','shaders/gbuffers_water.tcs',
                             'shaders/gbuffers_water.tes','shaders/gbuffers_water.fsh'):
                    self.assertEqual(new.read(name),old.read(name),name)

    def test_public_api_rejects_malformed_serialized_parent_seams_without_output(self):
        from water_residual_observe_pack import build_pack
        mutations = (
            ('shaders/gbuffers_water.fsh',b'/* RENDERTARGETS:0,9,10,11,12 */',b'/* RENDERTARGETS:0,9,10,11 */'),
            ('shaders/gbuffers_water.fsh',b'    gl_FragData[4]=tessStageCoord;\n',b''),
            ('shaders/gbuffers_water.fsh',b'    bool residualEligible=',b'    bool renamedEligibility='),
            ('shaders/gbuffers_water.fsh',b'    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n',b''),
            ('shaders/final.fsh',b'else if (probeState.z<0.5)',b'else if (probeState.z<0.4)'),
            ('shaders/lib/water_residual.glsl',b'#ifndef',b'// corrupt CPU I/O fixture\n#ifndef'),
        )
        for member,before,after in mutations:
            with self.subTest(member=member,seam=before),tempfile.TemporaryDirectory(
                    prefix='aqualumen-residual-observe-corrupt-') as temporary:
                destination = Path(temporary)/'not-created'/'observe.zip'
                class CorruptedParentRead(ZipFile):
                    def read(self,name,pwd=None):
                        content = super().read(name,pwd)
                        filename = name if isinstance(name,str) else name.filename
                        if filename==member:
                            self_test.assertIn(before,content)
                            return content.replace(before,after,1)
                        return content
                self_test = self
                # Corrupt the serialized ZIP read boundary, not the parent builder/model.
                with patch('water_residual_observe_pack.ZipFile',CorruptedParentRead):
                    with self.assertRaises(ValueError):
                        build_pack(self.root,destination)
                self.assertFalse(destination.parent.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
