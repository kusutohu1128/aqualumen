"""Synthetic saved-file CPU contracts, not actual Iris or shader evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys

from test_water_residual_runtime import fixture
from water_residual_sun_iris_runtime import COORDINATES
from water_residual_sun_reason_pack import build_pack
from water_residual_sun_reason_runtime import audit


ROOT=Path(__file__).resolve().parents[1]


class SavedReasonTests(unittest.TestCase):
    def invoke(self, mutate_raw=None, mutate_guard=None, mutate_files=None, cli=False):
        with tempfile.TemporaryDirectory(prefix='sun-reasons-runtime-synthetic-') as temporary:
            directory=Path(temporary)
            pack=build_pack(ROOT,directory/'Aqualumen-ShoreProbe-world-sun-reasons-cpu.zip')
            if mutate_files:
                from zipfile import ZipFile
                with ZipFile(pack) as archive: files={i.filename:archive.read(i) for i in archive.infolist()}
                mutate_files(files)
                with ZipFile(pack,'w') as archive:
                    for name,content in files.items(): archive.writestr(name,content)
            digest=hashlib.sha256(pack.read_bytes()).hexdigest()
            raw=fixture();raw.update(packName=pack.name,packSha256=digest,
                tag='DEBUG-shore-sampler',
                seam='FinalPassRenderer.renderFinalPass before FullScreenQuadRenderer.renderQuad; after Program.use and CustomUniforms.push',
                rawReadPolicy='GL3.2 glGetTexImage level0, bounded reusable whole-target scratch; only selected texels exported',
                samplingInterpretation='unfiltered level-zero texels, not tone-mapped or reconstructed FINAL texture() values',
                texelCoordinateConvention='integer level-zero texture coordinates; bottom-left origin',
                maximumSelectedTexels=16,selectedTexelsFiniteOnly=True,timingAcceptanceExcluded=True)
            for i in range(16):
                raw['samplers'][0]['samples'][i]['rgba']=([0,0,0,0] if i<2 else [3,48,0,0])
                raw['samplers'][1]['samples'][i]['rgba']=([1,1,0,0] if i<2 else [1,0,0,48])
                for sampler in raw['samplers']:
                    sampler['samples'][i].update(zip(('x','y'),COORDINATES[i]))
            raw['samplers'].extend(dict(name='colortex'+str(i),active=False,reason='inactive_uniform')
                                   for i in (13,14,15))
            guard=dict(schema='aqualumen-sun-guard-observation-v1',available=True,readOnly=True,
                observerVersion='0.1.0',scope='prepared-current-translucent-int-uniform',
                scopeAuthorized=True,localIntegratedSinglePlayer=True,currentPipelineMatches=True,
                containsTessellation=True,benchmarkState='complete',supplierAuthorization=1,
                constructorProgram=43,programBefore=43,programAfter=43,frameBefore=456,frameAfter=456,
                programAndFrameUnchanged=True,seam='SodiumShader.updateUniforms TAIL',
                registrationPath='CommonUniforms.addDynamicUniforms TAIL uniform1i PER_FRAME',
                supplierPath='SunAuthorization.value(runtime(game)) fresh each invocation; no cache/latch',
                uniform=dict(name='aqualumenSunTestAuthorized',active=True,location=5,type=5124,size=1,value=1),
                versions=dict(aqualumen_water_sun_test='0.1.0',aqualumen_benchmark='0.3.9',
                    aqualumen_physics='0.3.0',iris='1.8.8+mc1.21.1',sodium='0.6.9+mc1.21.1',minecraft='1.21.1'),
                errorFlagConsumed=False,drawIssuedProven=False,fragmentFetchProven=False,
                WNSApplicationProven=False,pngSameFrameProven=False,allGLStateUnchangedProven=False)
            guard['pass']='TRANSLUCENT'
            for key in ('worldId','world','seed','dimension','packName','packSha256'): guard[key]=raw[key]
            if mutate_raw: mutate_raw(raw)
            if mutate_guard: mutate_guard(guard)
            raw_file=directory/'synthetic-final.json';guard_file=directory/'synthetic-guard.json'
            raw_file.write_text(json.dumps(raw));guard_file.write_text(json.dumps(guard))
            before={p.name:p.read_bytes() for p in directory.iterdir()}
            try:
                if cli:
                    return subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('water_residual_sun_reason_runtime.py')),
                        str(raw_file),str(pack),str(guard_file)],capture_output=True,text=True)
                return audit(raw_file,pack,guard_file)
            finally: self.assertEqual(before,{p.name:p.read_bytes() for p in directory.iterdir()})

    def test_reason_evidence_qualifies_without_promoting_two_applications(self):
        report=self.invoke()
        self.assertTrue(report['reasonEvidenceQualified'])
        self.assertTrue(report['readbackQualified'])
        self.assertTrue(report['guardUniformQualified'])
        self.assertEqual(report['qualifiedAppliedPoints'],2)
        self.assertEqual(report['loopRejectedPoints'],14)
        self.assertEqual(report['groupedRejectedNodes']['hemisphere'],14*48)
        self.assertEqual(report['firstReasonHistogram']['3'],14)
        self.assertFalse(report['perCategoryNodeCountsObserved'])
        self.assertEqual(report['applicationVerdict'],'NEGATIVE_INSUFFICIENT_APPLICATION')
        self.assertFalse(report['operatorActiveQualified'])
        self.assertFalse(report['coefficientClosureObserved'])
        self.assertFalse(report['physicalAccepted'])
        self.assertFalse(report['sameFrameProven'])

    def test_rejects_stale_coefficient_manifest_even_when_rehashed_identity_matches(self):
        def stale(files):
            name='WATER-RESIDUAL-SUN-REASONS.json'
            metadata=json.loads(files[name])
            metadata['target_channels']['9']=['mass','R','T','TIR']
            metadata['coefficient_telemetry_current']=True
            files[name]=json.dumps(metadata).encode()
        with self.assertRaises(ValueError): self.invoke(mutate_files=stale)

    def test_rejects_old_coefficient_payload_or_contradictory_node_accounting(self):
        invalid=([1,.25,.75,0],[float('nan'),0,0,0],[True,48,0,0],
                 [3,47,0,0],[3,0,48,0],[1,48,0,0],[0,48,0,0],
                 [3,48,1,0],[10,0,0,48],[-1,0,0,48],[9,.5,0,47.5])
        for reason in invalid:
            with self.subTest(reason=reason),self.assertRaises(ValueError):
                self.invoke(mutate_raw=lambda r:r['samplers'][0]['samples'][2].update(rgba=reason))

    def test_rejects_rehashed_helper_or_source_changes_hidden_inside_removable_tags(self):
        def changed(files):
            name='shaders/lib/water_residual_sun.glsl'
            files[name]=files[name].replace(b'    WNS_reasons=vec4(0.0);\n',
                                           b'    WNS_reasons=vec4(0.0);\n    WNS_active=true;\n')
            metadata=json.loads(files['WATER-RESIDUAL-SUN-REASONS.json'])
            metadata['instrumented_helper_sha256']=hashlib.sha256(files[name]).hexdigest()
            metadata['helper_sha256'][name]=metadata['instrumented_helper_sha256']
            files['WATER-RESIDUAL-SUN-REASONS.json']=json.dumps(metadata).encode()
        with self.assertRaises(ValueError): self.invoke(mutate_files=changed)

    def test_public_cli_preserves_valid_negative_application_as_json_with_exit_one(self):
        result=self.invoke(cli=True)
        self.assertEqual(result.returncode,1,result.stderr)
        report=json.loads(result.stdout)
        self.assertTrue(report['reasonEvidenceQualified'])
        self.assertEqual(report['applicationVerdict'],'NEGATIVE_INSUFFICIENT_APPLICATION')
        self.assertFalse(report['operatorActiveQualified'])

    def test_loop_one_and_unclassified_pre_or_post_fallback_remain_distinct(self):
        for reason,classification in (([3,1,0,0],'CLASSIFIED_LOOP_REJECTION'),
                                     ([0,0,0,0],'UNCLASSIFIED_PRE_OR_POST_LOOP_REJECTION')):
            def changed(raw):
                raw['samplers'][0]['samples'][2]['rgba']=reason
                raw['samplers'][1]['samples'][2]['rgba']=[1,0,0,1]
            report=self.invoke(mutate_raw=changed)
            self.assertEqual(report['points'][2]['reasonClassification'],classification)
            self.assertFalse(report['operatorActiveQualified'])

    def test_separate_transmitted_and_reflected_categories_keep_group_accounting(self):
        for first,groups in ((1,[0,0,48]),(2,[0,0,48]),(3,[48,0,0]),(4,[0,0,48]),
                            (5,[0,0,48]),(6,[0,48,0]),(7,[0,48,0]),(8,[0,0,48]),(9,[48,0,0])):
            with self.subTest(first=first):
                report=self.invoke(mutate_raw=lambda r:r['samplers'][0]['samples'][2].update(rgba=[first,*groups]))
                self.assertEqual(report['points'][2]['reasonTuple'],[first,*groups])
                self.assertTrue(report['reasonEvidenceQualified'])

    def test_exact_minimum_four_and_zero_source_do_not_claim_coefficients_or_physics(self):
        def four(raw):
            for i in (2,3):
                raw['samplers'][0]['samples'][i]['rgba']=[0,0,0,0]
                raw['samplers'][1]['samples'][i]['rgba']=[1,1,0,0]
        report=self.invoke(mutate_raw=four)
        self.assertEqual(report['qualifiedAppliedPoints'],4)
        self.assertEqual(report['applicationVerdict'],'QUALIFIED_SELECTED_APPLICATION')
        self.assertTrue(report['operatorActiveQualified'])
        self.assertFalse(report['coefficientClosureObserved'])
        def absent(raw):
            for sampler in raw['samplers'][:2]:
                for point in sampler['samples']: point['rgba']=[0,0,0,0]
            for point in raw['samplers'][1]['samples']: point['rgba']=[1,0,0,0]
        report=self.invoke(mutate_raw=absent)
        self.assertEqual(report['qualifiedAppliedPoints'],0)
        self.assertEqual(report['loopRejectedPoints'],0)
        self.assertFalse(report['operatorActiveQualified'])

    def test_rejects_applied_or_disabled_reason_contradictions_and_bad_original_domain(self):
        mutations=[lambda r:r['samplers'][0]['samples'][0].update(rgba=[3,1,0,0]),
            lambda r:r['samplers'][1]['samples'][0].update(rgba=[1,1,0,1]),
            lambda r:r['samplers'][1]['samples'][2].update(rgba=[0,0,0,48]),
            lambda r:r['samplers'][1]['samples'][2].update(rgba=[1,.5,0,48]),
            lambda r:r['samplers'][1]['samples'][2].update(rgba=[1,0,1,48]),
            lambda r:r['samplers'][1]['samples'][2].update(rgba=[1,0,0,49]),
            lambda r:r['samplers'][2]['samples'][0].update(rgba=[.006,.002,.004,7]),
            lambda r:r['samplers'][2]['samples'][0].update(rgba=[.001,.1,.001,15]),
            lambda r:r['samplers'][2]['samples'][2].update(rgba=[.006,.002,.004,8]),
            lambda r:r['samplers'][3]['samples'][0].update(rgba=[.2,.2,.2,1]),
            lambda r:r['samplers'][3]['samples'][0].update(rgba=[0,0,0,0])]
        for i,mutation in enumerate(mutations):
            with self.subTest(mutation=i),self.assertRaises(ValueError): self.invoke(mutate_raw=mutation)

    def test_preserves_fixed_order_binding_state_world_program_and_integer_guard(self):
        def duplicate(raw):
            for sampler in raw['samplers'][:4]:
                sampler['samples'][1].update(x=801,y=451)
        raw_mutations=[lambda r:r.update(packSha256='0'*64),lambda r:r.update(worldId='0'*36),
            lambda r:r.update(seed=True),lambda r:r.update(width=2560),lambda r:r.update(expectedProgram=33),
            lambda r:r.update(snapshotFrame=True),lambda r:r.update(scopeAuthorized=False),
            lambda r:r['stateAfter'].update(binding=999),lambda r:r['samplers'][0].update(type=5124),
            lambda r:r['samplers'][1].update(textureId=71),lambda r:r['samplers'][2].update(actualFormat=34842),
            lambda r:r['samplers'][0]['samples'][0].update(x=802),duplicate]
        for i,mutation in enumerate(raw_mutations):
            with self.subTest(raw=i),self.assertRaises(ValueError): self.invoke(mutate_raw=mutation)
        guard_mutations=[lambda g:g.update(packSha256='0'*64),lambda g:g.update(frameAfter=457),
            lambda g:g.update(programAfter=44),lambda g:g.update(benchmarkState='sampling'),
            lambda g:g['uniform'].update(value=0),lambda g:g['uniform'].update(type=5126),
            lambda g:g['uniform'].update(size=True),lambda g:g.update(supplierAuthorization=True)]
        for i,mutation in enumerate(guard_mutations):
            with self.subTest(guard=i),self.assertRaises(ValueError): self.invoke(mutate_guard=mutation)

    def test_preserves_source_member_hashes_and_rejects_stale_combined_hemisphere_policy(self):
        def metadata(files):
            name='WATER-RESIDUAL-SUN-REASONS.json';value=json.loads(files[name])
            value['reason_categories'].pop('9');value['reason_groups']['hemisphere']=[3]
            files[name]=json.dumps(value).encode()
        def changed_geometry(files): files['shaders/gbuffers_water.tes']+=b'// changed\n'
        def changed_store(files):
            name='shaders/gbuffers_water.fsh'
            files[name]=files[name].replace(b'gl_FragData[1]=WNS_reasons;',b'gl_FragData[1]=WR_coefficients;')
        for mutation in (metadata,changed_geometry,changed_store):
            with self.subTest(mutation=mutation),self.assertRaises(ValueError): self.invoke(mutate_files=mutation)


if __name__=='__main__': unittest.main(verbosity=2)
