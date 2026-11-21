"""Public CLI tests with synthetic CPU files, never GL/runtime evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile


SCRIPT = Path(__file__).with_name('water_residual_runtime.py')
CHANNELS = {'9':['mass','R','T','TIR'], '10':['valid','applied','minFacing','opaqueCount'],
            '11':['Cxx','Cxz','Czz','productionFlags'], '12':['barycentricX','barycentricY','barycentricZ','stagePresent']}
HELPERS = {'shaders/lib/wave_residual.glsl':b'// synthetic CPU wave helper\n',
           'shaders/lib/water_residual.glsl':b'// synthetic CPU interface helper\n'}


def fixture():
    state = dict(active=33984, binding=49, packBuffer=0, alignment=4, rowLength=0,
                 imageHeight=0, skipPixels=0, skipRows=0, skipImages=0, swap=0, lsb=0)
    raw = dict(available=True, stateRestored=True, scopeAuthorized=True,
        worldId='b22dbccb-2970-41e6-847f-f183b1ec923d', world='AqualumenNaturalV2', seed=308060,
        dimension='minecraft:overworld', observerVersion='0.3.9', program=21, expectedProgram=21,
        width=1600, height=900, renderer='NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2',
        stateBefore=state, stateAfter=state.copy(), snapshotFrame=123,
        samplers=[], samplerMetadata=[])
    for index in range(4):
        points=[]
        for p in range(16):
            values=([1,.25,.75,0], [1,1,.9,0], [.006,.002,.004,15],
                    [.1+p/100,.2,.7-p/100,1])[index]
            points.append(dict(x=20+p*50, y=450, rgba=values.copy()))
        raw['samplers'].append(dict(name='colortex'+str(9+index), active=True, type=35678,
            size=1, location=index, unit=index+3, textureId=index+71, textureExists=True,
            actualFormat=34836, width=1600, height=900, samples=points))
        raw['samplerMetadata'].append(dict(unit=index+3, textureId=index+71,
            wholeTargetReadbackBytes=1600*900*16, exportedTexelCount=16))
    return raw


class ResidualRuntimeTests(unittest.TestCase):
    def invoke(self, mutate_raw=None, mutate_metadata=None):
        with tempfile.TemporaryDirectory(prefix='aqualumen-residual-runtime-cpu-') as temporary:
            directory=Path(temporary)
            pack=directory/'Aqualumen-ShoreProbe-world-water-residual-observe-cpu-test.zip'
            parent=dict(schema='aqualumen-water-residual-probe-v1', mode='residual-interface-atlas',
                helper_sha256={n:hashlib.sha256(b).hexdigest() for n,b in HELPERS.items()})
            parent_bytes=(json.dumps(parent, sort_keys=True)+'\n').encode()
            metadata=dict(schema='aqualumen-water-residual-observe-v1', mode='residual-interface-observe',
                test_only=True, not_shipping=True, shipping_fix=False, geometry_factor=4,
                fixed_phase_seconds=120, quadrature_order=3, actual_shader_node_count_qualified=False,
                parent_pack_sha256='a'*64, parent_metadata_member='WATER-RESIDUAL-PROBE.json',
                parent_metadata_sha256=hashlib.sha256(parent_bytes).hexdigest(),
                helper_sha256=parent['helper_sha256'], target_channels={k:v.copy() for k,v in CHANNELS.items()},
                production_flags=dict(known=1,upper=2,underwater=4,residualEligible=8),
                production_flags_range=[0,15],
                production_flags_expression='float(localColumnKnown)+2.0*float(upperSurface)+4.0*float(underwater)+8.0*float(residualEligible)',
                parent_metadata_is_current_atlas_policy=False, inherited_metadata_is_current_atlas_policy=False,
                parent_metadata_is_current_optical_policy=False, GL_neutrality_verified=False,
                runtime_accepted=False, visual_accepted=False, performance_accepted=False,
                energy_accepted=False, reciprocity_accepted=False, generated_geometry_accepted=False,
                motion_accepted=False, pack_enforces_world_guard=False)
            if mutate_metadata: mutate_metadata(metadata)
            with ZipFile(pack,'w') as archive:
                archive.writestr('WATER-RESIDUAL-OBSERVE.json',json.dumps(metadata))
                archive.writestr('WATER-RESIDUAL-PROBE.json',parent_bytes)
                for name,content in HELPERS.items(): archive.writestr(name,content)
            raw=fixture()
            raw.update(packName=pack.name,packSha256=hashlib.sha256(pack.read_bytes()).hexdigest())
            if mutate_raw: mutate_raw(raw)
            raw_file=directory/'synthetic-raw.json';raw_file.write_text(json.dumps(raw))
            before={p.name:p.read_bytes() for p in directory.iterdir()}
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(raw_file),str(pack)],
                                  capture_output=True,text=True)
            self.assertEqual(before,{p.name:p.read_bytes() for p in directory.iterdir()})
            return result

    def test_public_cli_qualifies_residual_statistics_without_render_acceptance(self):
        result=self.invoke()
        self.assertEqual(result.returncode,0,result.stderr)
        observed=json.loads(result.stdout)
        self.assertIs(observed.get('readbackQualified'),True)
        self.assertIs(observed.get('operatorActiveQualified'),True)
        self.assertEqual(observed.get('operatorActivePoints'),16)
        self.assertEqual(observed.get('stagePresentPoints'),16)
        for key in ('physicalEnergyAccepted','reciprocityAccepted','geometryAccepted','shippingAccepted',
                    'visualQualityAccepted','pngSameFrameAccepted','fpsFloorAccepted','nodeCountProven'):
            self.assertIs(observed.get(key),False,key)

    def test_public_cli_rejects_noninteger_gl_state_even_when_before_after_match(self):
        def typed_state(raw):
            raw['stateBefore']['skipRows']=False
            raw['stateAfter']['skipRows']=False
        result=self.invoke(mutate_raw=typed_state)
        self.assertNotEqual(result.returncode,0,'Boolean JSON state must not pass an integer GL contract')
        self.assertEqual(result.stdout,'')
        self.assertRegex(result.stderr,r'\ARejected residual observation: [A-Za-z]+Error\n\Z')

    def test_public_cli_rejects_boolean_flag_mask_metadata(self):
        result=self.invoke(mutate_metadata=lambda m:m['production_flags'].update(known=True))
        self.assertNotEqual(result.returncode,0,'Flag masks must be integer declarations, not boolean aliases')

    def test_public_cli_readback_can_qualify_without_claiming_rejected_operator_statistics(self):
        def rejected(raw):
            for point in raw['samplers'][0]['samples']: point['rgba']=[0,0,0,0]
            for point in raw['samplers'][1]['samples']: point['rgba']=[0,0,.9,2]
            for point in raw['samplers'][2]['samples']: point['rgba']=[-1,0,-1,15]
        result=self.invoke(mutate_raw=rejected)
        self.assertEqual(result.returncode,0,result.stderr)
        observed=json.loads(result.stdout)
        self.assertIs(observed['readbackQualified'],True)
        self.assertIs(observed['operatorActiveQualified'],False)
        self.assertEqual(observed['operatorActivePoints'],0)
        self.assertEqual(observed['inactivePoints'],16)
        self.assertIs(observed['inactiveStatisticsQualified'],False)
        self.assertTrue(all(not p['operatorStatisticsQualified'] for p in observed['points']))

    def test_public_cli_rejects_applied_operator_with_bad_flags_covariance_or_coefficients(self):
        mutations=[lambda r:r['samplers'][2]['samples'][0].update(rgba=[.006,.002,.004,7]),
                   lambda r:r['samplers'][2]['samples'][0].update(rgba=[.006,.002,.004,14.5]),
                   lambda r:r['samplers'][2]['samples'][0].update(rgba=[-1,0,.004,15]),
                   lambda r:r['samplers'][2]['samples'][0].update(rgba=[.001,.1,.001,15]),
                   lambda r:r['samplers'][1]['samples'][0].update(rgba=[0,1,.9,0]),
                   lambda r:r['samplers'][1]['samples'][0].update(rgba=[1,1,0,0]),
                   lambda r:r['samplers'][1]['samples'][0].update(rgba=[1,1,.9,1]),
                   lambda r:r['samplers'][0]['samples'][0].update(rgba=[.9,.25,.65,0]),
                   lambda r:r['samplers'][0]['samples'][0].update(rgba=[1,.25,.7,0]),
                   lambda r:r['samplers'][0]['samples'][0].update(rgba=[1,.25,.75,.3])]
        for i,mutation in enumerate(mutations):
            with self.subTest(mutation=i):
                self.assertNotEqual(self.invoke(mutate_raw=mutation).returncode,0)

    def test_public_cli_preserves_generic_identity_binding_state_and_geometry_guards(self):
        def repeated(raw):
            for sampler in raw['samplers']:
                sampler['samples'][1]['x']=sampler['samples'][0]['x']
                sampler['samples'][1]['y']=sampler['samples'][0]['y']
        mutations=[lambda r:r.update(packSha256='0'*64),lambda r:r.update(seed=0),
                   lambda r:r.update(scopeAuthorized=False),lambda r:r.update(program=99),
                   lambda r:r['samplers'][3].update(unit=3),
                   lambda r:r['samplers'][3].update(textureId=71),
                   lambda r:r['samplers'][3].update(active=False),
                   lambda r:r['samplers'][3].update(actualFormat=34842),
                   lambda r:r['samplers'][3].update(size=True),
                   lambda r:r['samplers'][3].update(width=2560),
                   lambda r:r['samplers'][3]['samples'][0].update(rgba=[.2,.2,.2,1]),
                   lambda r:r['samplers'][3]['samples'][0].update(rgba=[.1,.2,.7,0]),
                   lambda r:r['samplers'][0]['samples'][0].update(rgba=[float('nan'),0,0,0]),
                   lambda r:r['samplers'][2]['samples'][0].update(rgba=[0,0,0,True]),
                   lambda r:r['stateAfter'].update(binding=999),repeated]
        for i,mutation in enumerate(mutations):
            with self.subTest(mutation=i):
                result=self.invoke(mutate_raw=mutation)
                self.assertNotEqual(result.returncode,0)
                self.assertEqual(result.stdout,'')
                self.assertRegex(result.stderr,r'\ARejected residual observation: [A-Za-z]+Error\n\Z')

    def test_public_cli_rejects_unapproved_authoritative_policy_or_helper_declarations(self):
        mutations=[lambda m:m.update(schema='aqualumen-water-tessellation-probe-v1'),
                   lambda m:m.update(mode='residual-interface-atlas'),
                   lambda m:m.update(geometry_factor=1),lambda m:m.update(fixed_phase_seconds=121),
                   lambda m:m.update(quadrature_order=9),lambda m:m.update(shipping_fix=True),
                   lambda m:m.update(parent_metadata_sha256='0'*64),
                   lambda m:m['target_channels']['11'].append('skyTmass'),
                   lambda m:m.update(production_flags_expression='15.0'),
                   lambda m:m['helper_sha256'].update({'shaders/lib/water_residual.glsl':'0'*64}),
                   lambda m:m.update(padding='x'*32769)]
        for i,mutation in enumerate(mutations):
            with self.subTest(mutation=i):
                self.assertNotEqual(self.invoke(mutate_metadata=mutation).returncode,0)


if __name__=='__main__':
    unittest.main(verbosity=2)
