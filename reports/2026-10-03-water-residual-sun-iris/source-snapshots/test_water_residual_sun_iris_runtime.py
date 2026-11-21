"""Public saved Sun telemetry contracts, not actual GPU/Iris evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from water_residual_sun_iris_runtime import qualify_texels


def water_point():
    return dict(x=801,y=451,coefficients=[1.,.02,.98,0.],
                sun_status=[1.,1.,0.,0.],covariance_flags=[.0064,0.,.0064,15.],
                stage=[.2,.3,.5,1.])


class SunIrisTelemetryTests(unittest.TestCase):
    def test_native_source_zero_status_is_sun_kind_not_missing_legacy_facing(self):
        report=qualify_texels([water_point()],enabled=1,authorized=1)
        self.assertEqual(report['qualifiedAppliedPoints'],1)
        self.assertEqual(report['requestedPoints'],1)
        self.assertFalse(report['physicalAccepted'])
        self.assertFalse(report['pixelAAAccepted'])

    def test_applied_output_cannot_hide_absent_live_authorization(self):
        with self.assertRaises(ValueError):
            qualify_texels([water_point()],enabled=1,authorized=0)

    def test_applied_output_requires_original_water_domain_and_strict_covariance(self):
        for changed in ([.0064,0.,.0064,7.],[.000001,.000002,.000001,15.],
                        [0.,0.,0.,15.]):
            point=water_point();point['covariance_flags']=changed
            with self.subTest(covariance_flags=changed),self.assertRaises(ValueError):
                qualify_texels([point],enabled=1,authorized=1)

    def test_nonfinite_or_malformed_status_is_not_an_inactive_success(self):
        for values in ([0.,0.,0.,float('nan')],[0.,0.,1.,0.],
                       [0.,.5,0.,0.],[0.,0.,0.,-.5],[1.,1.,0.,2.],[]):
            point=water_point();point['sun_status']=values
            with self.subTest(status=values),self.assertRaises(ValueError):
                qualify_texels([point],enabled=1,authorized=1)

    def test_disabled_or_unauthorized_source_cannot_claim_even_a_request(self):
        point=water_point();point['sun_status']=[1.,0.,0.,0.]
        for enabled,authorized in ((0,1),(1,0)):
            with self.subTest(enabled=enabled,authorized=authorized),self.assertRaises(ValueError):
                qualify_texels([point],enabled=enabled,authorized=authorized)

    def test_applied_output_requires_legacy_coefficients_and_tes_not_just_a_flag(self):
        for field,value in [('coefficients',[0.,0.,0.,0.]),
                            ('coefficients',[1.,.02,.8,0.]),
                            ('stage',[0.,0.,0.,0.])]:
            point=water_point();point[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                qualify_texels([point],enabled=1,authorized=1)


class SavedSunAuditTests(unittest.TestCase):
    """Synthetic JSON boundary files plus actual frozen source ZIP; no GL calls."""
    def invoke(self, mutate_raw=None, mutate_guard=None, enabled=1, mutate_files=None):
        from test_water_residual_runtime import fixture
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='sun-iris-runtime-synthetic-') as temporary:
            directory=Path(temporary)
            name=f'Aqualumen-ShoreProbe-world-native-sun-iris-enabled{enabled}-v1.zip'
            pack=directory/name
            shutil.copyfile(root/'reports/2026-10-03-water-residual-sun-iris/cpu-pack'/name,pack)
            if mutate_files:
                from zipfile import ZipFile
                with ZipFile(pack) as archive: files={i.filename:archive.read(i) for i in archive.infolist()}
                mutate_files(files)
                with ZipFile(pack,'w') as archive:
                    for n,b in files.items(): archive.writestr(n,b)
            digest=hashlib.sha256(pack.read_bytes()).hexdigest()
            raw=fixture();raw.update(packName=name,packSha256=digest)
            coordinates=((801,451),(401,451),(1201,451),(801,251),(33,451),(65,451),(129,451),(193,451),
                         (1409,451),(1473,451),(1537,451),(1567,451),(129,129),(1473,129),(129,771),(1473,771))
            for sampler in raw['samplers']:
                for point,(x,y) in zip(sampler['samples'],coordinates): point.update(x=x,y=y)
            raw.update(tag='DEBUG-shore-sampler',
                seam='FinalPassRenderer.renderFinalPass before FullScreenQuadRenderer.renderQuad; after Program.use and CustomUniforms.push',
                rawReadPolicy='GL3.2 glGetTexImage level0, bounded reusable whole-target scratch; only selected texels exported',
                samplingInterpretation='unfiltered level-zero texels, not tone-mapped or reconstructed FINAL texture() values',
                texelCoordinateConvention='integer level-zero texture coordinates; bottom-left origin',
                maximumSelectedTexels=16,selectedTexelsFiniteOnly=True,timingAcceptanceExcluded=True)
            for point in raw['samplers'][1]['samples']: point['rgba']=[enabled,enabled,0,0]
            guard=dict(schema='aqualumen-sun-guard-observation-v1',available=True,readOnly=True,
                scope='prepared-current-translucent-int-uniform',scopeAuthorized=True,
                worldId=raw['worldId'],world=raw['world'],seed=raw['seed'],dimension=raw['dimension'],
                observerVersion='0.1.0',packName=name,packSha256=digest,
                localIntegratedSinglePlayer=True,currentPipelineMatches=True,containsTessellation=True,
                pass_='TRANSLUCENT',benchmarkState='complete',supplierAuthorization=1,
                constructorProgram=43,programBefore=43,programAfter=43,frameBefore=456,frameAfter=456,
                programAndFrameUnchanged=True,seam='SodiumShader.updateUniforms TAIL',
                registrationPath='CommonUniforms.addDynamicUniforms TAIL uniform1i PER_FRAME',
                supplierPath='SunAuthorization.value(runtime(game)) fresh each invocation; no cache/latch',
                versions=dict(aqualumen_water_sun_test='0.1.0',aqualumen_benchmark='0.3.9',
                    aqualumen_physics='0.3.0',iris='1.8.8+mc1.21.1',sodium='0.6.9+mc1.21.1',minecraft='1.21.1'),
                uniform=dict(name='aqualumenSunTestAuthorized',active=True,location=5,type=5124,size=1,value=1),
                errorFlagConsumed=False,drawIssuedProven=False,fragmentFetchProven=False,
                WNSApplicationProven=False,pngSameFrameProven=False,allGLStateUnchangedProven=False)
            guard['pass']=guard.pop('pass_')
            if mutate_raw: mutate_raw(raw)
            if mutate_guard: mutate_guard(guard)
            raw_file=directory/'synthetic-final.json';guard_file=directory/'synthetic-guard.json'
            raw_file.write_text(json.dumps(raw));guard_file.write_text(json.dumps(guard))
            before={p.name:p.read_bytes() for p in directory.iterdir()}
            result=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('water_residual_sun_iris_runtime.py')),
                                   str(raw_file),str(pack),str(guard_file)],capture_output=True,text=True)
            self.assertEqual(before,{p.name:p.read_bytes() for p in directory.iterdir()})
            return result

    def test_public_cli_qualifies_sun_status_not_old_wr_status_and_keeps_frames_separate(self):
        result=self.invoke()
        self.assertEqual(result.returncode,0,result.stderr)
        observed=json.loads(result.stdout)
        self.assertTrue(observed['readbackQualified'])
        self.assertTrue(observed['guardUniformQualified'])
        self.assertTrue(observed['operatorActiveQualified'])
        self.assertEqual(observed['qualifiedAppliedPoints'],16)
        for key in ('sameFrameProven','drawIssuedProven','fragmentFetchProven','physicalAccepted','pixelAAAccepted','shippingAccepted'):
            self.assertIs(observed[key],False,key)

    def test_public_cli_zero_or_three_applications_are_negative_not_a_shader_pass(self):
        for count in (0,3):
            def inactive(raw):
                for i,p in enumerate(raw['samplers'][1]['samples']):
                    if i>=count: p['rgba']=[1,0,0,0]
            with self.subTest(count=count):
                result=self.invoke(mutate_raw=inactive)
                self.assertEqual(result.returncode,1)
                observed=json.loads(result.stdout)
                self.assertTrue(observed['readbackQualified'])
                self.assertFalse(observed['operatorActiveQualified'])
                self.assertEqual(observed['applicationVerdict'],'NEGATIVE_INSUFFICIENT_APPLICATION')
        control=self.invoke(enabled=0)
        self.assertEqual(control.returncode,0,control.stderr)
        observed=json.loads(control.stdout)
        self.assertEqual(observed['applicationVerdict'],'DISABLED_CONTROL')
        self.assertFalse(observed['operatorActiveQualified'])

    def test_public_cli_rejects_inactive_corrupt_flags_tes_and_missing_frame(self):
        def inactive_bad_flags(raw):
            raw['samplers'][1]['samples'][0]['rgba']=[0,0,0,0]
            raw['samplers'][2]['samples'][0]['rgba']=[0,0,0,8]
        def inactive_bad_stage(raw):
            raw['samplers'][1]['samples'][0]['rgba']=[0,0,0,0]
            raw['samplers'][3]['samples'][0]['rgba']=[.2,.2,.2,1]
        for mutation in (inactive_bad_flags,inactive_bad_stage,lambda r:r.update(snapshotFrame=True)):
            with self.subTest(mutation=mutation):
                result=self.invoke(mutate_raw=mutation)
                self.assertEqual(result.returncode,1)
                self.assertEqual(result.stdout,'')

    def test_public_cli_preserves_typed_scope_bindings_and_state_guards(self):
        def repeated(raw):
            for s in raw['samplers']: s['samples'][1].update(x=s['samples'][0]['x'],y=s['samples'][0]['y'])
        def boolean_state(raw):
            raw['stateBefore']['skipRows']=False;raw['stateAfter']['skipRows']=False
        mutations=[lambda r:r.update(seed=True),lambda r:r.update(packSha256='0'*64),
            lambda r:r.update(observerVersion='0.4.0'),lambda r:r.update(scopeAuthorized=False),
            lambda r:r.update(width=2560),lambda r:r.update(program=0),
            lambda r:r['samplers'][0].update(type=True),lambda r:r['samplers'][0].update(size=True),
            lambda r:r['samplers'][0].update(actualFormat=34842),lambda r:r['samplers'][0].update(active=False),
            lambda r:r['samplers'][1].update(textureId=71),lambda r:r['samplers'][1].update(unit=3),
            lambda r:r['samplerMetadata'][0].update(exportedTexelCount=True),
            lambda r:r['samplers'][0]['samples'][0].update(rgba=[float('nan'),0,0,0]),
            lambda r:r['samplers'][0]['samples'][0].update(x=1600),
            lambda r:r['stateAfter'].update(binding=999),repeated,boolean_state]
        for i,mutation in enumerate(mutations):
            with self.subTest(mutation=i):
                result=self.invoke(mutate_raw=mutation)
                self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,'')
                self.assertRegex(result.stderr,r'\ARejected Sun observation: [A-Za-z]+Error\n\Z')
        def extras(raw):
            raw['samplers'].extend(dict(name='colortex'+str(i),active=False,reason='inactive_uniform') for i in (13,14,15))
        result=self.invoke(mutate_raw=extras)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_public_cli_rejects_wrong_prepared_uniform_program_frame_route_and_versions(self):
        mutations=[lambda g:g['uniform'].update(type=5126),lambda g:g['uniform'].update(size=True),
            lambda g:g['uniform'].update(value=0),lambda g:g['uniform'].update(value=True),
            lambda g:g['uniform'].update(active=False),lambda g:g['uniform'].update(location=-1),
            lambda g:g.update(programAfter=44),lambda g:g.update(frameAfter=457),
            lambda g:g.update(frameBefore=True,frameAfter=True),lambda g:g.update(supplierAuthorization=True),
            lambda g:g.update(available=False),lambda g:g.update(packSha256='0'*64),
            lambda g:g.update(registrationPath='CommonUniforms.addNonDynamicUniforms'),
            lambda g:g.update(scope='water-draw'),lambda g:g.update(benchmarkState='sampling'),
            lambda g:g['versions'].update(iris='1.9.0'),lambda g:g.update(fragmentFetchProven=True)]
        for i,mutation in enumerate(mutations):
            with self.subTest(mutation=i):
                result=self.invoke(mutate_guard=mutation)
                self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,'')

    def test_public_cli_rejects_rehashed_source_and_manifest_tampering(self):
        def guard_bypass(files):
            name='shaders/gbuffers_water.fsh';files[name]=files[name].replace(b'if (aqualumenSunTestAuthorized==1)',b'if (true)')
            m=json.loads(files['WATER-RESIDUAL-SUN-IRIS.json'])
            m['observer_water_fs_sha256']=hashlib.sha256(files[name]).hexdigest()
            files['WATER-RESIDUAL-SUN-IRIS.json']=json.dumps(m).encode()
        def policy(files):
            m=json.loads(files['WATER-RESIDUAL-SUN-IRIS.json']);m['pixel_AA_equivalence_accepted']=True
            files['WATER-RESIDUAL-SUN-IRIS.json']=json.dumps(m).encode()
        for mutation in (guard_bypass,policy,
            lambda f:f.update({'shaders/lib/water_residual_sun.glsl':b'// altered helper\n'}),
            lambda f:f.update({'shaders/gbuffers_water.tes':b'// altered geometry\n'})):
            with self.subTest(mutation=mutation):
                result=self.invoke(mutate_files=mutation)
                self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,'')

    def test_public_cli_requires_exact_declared_coordinates_role_order_and_actual_final_protocol(self):
        def moved(raw):
            for s in raw['samplers']: s['samples'][0]['x']=802
        def reordered(raw):
            raw['samplers'][0],raw['samplers'][1]=raw['samplers'][1],raw['samplers'][0]
        for mutation in (moved,reordered,lambda r:r.update(tag='unknown'),lambda r:r.update(seam='after draw')):
            with self.subTest(mutation=mutation):
                result=self.invoke(mutate_raw=mutation)
                self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,'')

if __name__=='__main__':unittest.main()
