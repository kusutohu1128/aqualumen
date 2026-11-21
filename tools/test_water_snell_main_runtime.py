"""Synthetic saved-file CPU contracts; never runtime or shader evidence."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from water_snell_main_runtime import audit


def normal_record():
    return dict(x=801,y=451,mean_called=[0.,-1.,0.,1.],view_requested=[0.,-1.,0.,1.],
        covariance_flags=[0.006000000052154064,0.0020000000949949026,0.004000000189989805,15.],
        first_target_reason=[0.,1.,0.,4*64+1.])


ROOT=Path(__file__).resolve().parents[1]


def saved_fixture(directory,mode='old',mutate_raw=None,mutate_guard=None,mutate_files=None):
    from test_water_residual_runtime import fixture
    from water_residual_sun_iris_runtime import COORDINATES
    from water_snell_main_pack import build_pack
    pack=build_pack(ROOT,directory/'synthetic-main-inputs.zip',mode=mode,observe='inputs')
    if mutate_files:
        with ZipFile(pack) as archive: files={n:archive.read(n) for n in archive.namelist()}
        mutate_files(files)
        with ZipFile(pack,'w') as archive:
            for name,value in files.items(): archive.writestr(name,value)
    raw=fixture();raw.update(packName=pack.name,packSha256=hashlib.sha256(pack.read_bytes()).hexdigest(),
        tag='DEBUG-shore-sampler',
        seam='FinalPassRenderer.renderFinalPass before FullScreenQuadRenderer.renderQuad; after Program.use and CustomUniforms.push',
        rawReadPolicy='GL3.2 glGetTexImage level0, bounded reusable whole-target scratch; only selected texels exported',
        samplingInterpretation='unfiltered level-zero texels, not tone-mapped or reconstructed FINAL texture() values',
        texelCoordinateConvention='integer level-zero texture coordinates; bottom-left origin',
        maximumSelectedTexels=16,selectedTexelsFiniteOnly=True,timingAcceptanceExcluded=True)
    record=normal_record()
    for sampler,field in zip(raw['samplers'],('mean_called','view_requested','covariance_flags','first_target_reason')):
        for point,coordinate in zip(sampler['samples'],COORDINATES):
            point.update(x=coordinate[0],y=coordinate[1],rgba=record[field].copy())
    raw['samplers'].extend(dict(name='colortex'+str(i),active=False,reason='inactive_uniform') for i in (13,14,15))
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
        errorFlagConsumed=False,drawIssuedProven=False,fragmentFetchProven=False,WNSApplicationProven=False,
        pngSameFrameProven=False,allGLStateUnchangedProven=False)
    guard['pass']='TRANSLUCENT'
    for key in ('worldId','world','seed','dimension','packName','packSha256'): guard[key]=raw[key]
    if mutate_raw: mutate_raw(raw)
    if mutate_guard: mutate_guard(guard)
    raw_file=directory/'synthetic-raw.json';guard_file=directory/'synthetic-guard.json'
    raw_file.write_text(json.dumps(raw));guard_file.write_text(json.dumps(guard))
    return raw_file,pack,guard_file


class MainInputTests(unittest.TestCase):
    def invoke(self,mode='old',cli=False,**changes):
        with tempfile.TemporaryDirectory(prefix='snell-main-synthetic-cpu-') as temporary:
            directory=Path(temporary);paths=saved_fixture(directory,mode,**changes)
            before={p.name:p.read_bytes() for p in directory.iterdir()}
            try:
                if cli:
                    return subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('water_snell_main_runtime.py')),
                        *map(str,paths)],capture_output=True,text=True)
                return audit(*paths)
            finally: self.assertEqual(before,{p.name:p.read_bytes() for p in directory.iterdir()})
    def test_public_boundary_rejects_missing_capture(self):
        with tempfile.TemporaryDirectory(prefix='snell-main-cpu-') as temporary:
            path=Path(temporary)
            with self.assertRaises((ValueError,OSError)):
                audit(path/'missing.json',path/'missing.zip',path/'guard.json')

    def test_normal_supported_record_preserves_same_draw_reason_and_raw_bits(self):
        from water_snell_main_runtime import analyze_record
        report=analyze_record(normal_record())
        self.assertEqual(report['firstReason'],4)
        self.assertEqual(report['firstNodeIndex'],0)
        self.assertTrue(report['reference']['physical']['supported'])
        self.assertEqual(report['reference']['raw_v_bits'],['00000000','000080bf','00000000'])
        self.assertEqual(report['observedGateClassification'],'POSITIVE_SUPPORT_COMPOUND_GATE_REJECTION')
        self.assertFalse(report['GPUArithmeticCauseProven'])

    def test_supported_numeric_rejection_is_cpu_replay_not_gpu_cause(self):
        from water_snell_main_runtime import analyze_record
        from water_snell_boundary_reference import family
        ref=next(c['result'] for c in family()['cases'] if c['j']==13 and c['side']==-1)
        record=normal_record();record['view_requested']=[*ref['raw_v'],1.]
        record['first_target_reason']=[*ref['raw_t'],2*64+48.]
        report=analyze_record(record)
        self.assertEqual(report['firstNodeIndex'],47)
        self.assertEqual(report['arithmeticReplayClassification'],'POSITIVE_SUPPORTED_NUMERIC_REJECTION')
        self.assertFalse(report['reference']['old_binary32']['unfused']['accepted'])
        self.assertFalse(report['GPUArithmeticCauseProven'])

    def test_supported_absence_is_distinct_from_numerical_rejection(self):
        from water_snell_main_runtime import analyze_record
        from water_snell_boundary_reference import family
        ref=next(c['result'] for c in family()['cases'] if c['j']==13 and c['side']==1)
        record=normal_record();record['view_requested']=[*ref['raw_v'],1.]
        record['first_target_reason']=[*ref['raw_t'],2*64+1.]
        report=analyze_record(record)
        self.assertFalse(report['reference']['physical']['supported'])
        self.assertEqual(report['observedGateClassification'],'PHYSICALLY_UNSUPPORTED_AT_COMPOUND_GATE')

    def test_no_first_target_does_not_invent_support_or_application(self):
        from water_snell_main_runtime import analyze_record
        record=normal_record();record['first_target_reason']=[0.,0.,0.,0.]
        report=analyze_record(record)
        self.assertIsNone(report['reference'])
        self.assertEqual(report['observedGateClassification'],'NO_FIRST_FAILED_NODE_OBSERVED')
        self.assertIsNone(report['firstNodeIndex'])
        record['mean_called']=[0.,0.,0.,0.];record['view_requested']=[0.,0.,0.,0.]
        record['covariance_flags']=[0.,0.,0.,15.]
        report=analyze_record(record)
        self.assertEqual(report['observedGateClassification'],'HELPER_NOT_CALLED')

    def test_rejects_malformed_binary32_domain_or_encoding_without_dropping_record(self):
        from water_snell_main_runtime import analyze_record
        mutations=[lambda r:r['first_target_reason'].__setitem__(3,2*64),
            lambda r:r['first_target_reason'].__setitem__(3,9*64+49),
            lambda r:r['first_target_reason'].__setitem__(3,10*64+1),
            lambda r:r['first_target_reason'].__setitem__(3,129.5),
            lambda r:r['first_target_reason'].__setitem__(0,float('nan')),
            lambda r:r['view_requested'].__setitem__(0,.1),
            lambda r:r['view_requested'].__setitem__(3,True),
            lambda r:r['mean_called'].__setitem__(3,0.),
            lambda r:r['view_requested'].__setitem__(3,0.),
            lambda r:r['covariance_flags'].__setitem__(3,7.),
            lambda r:r['covariance_flags'].__setitem__(3,8.),
            lambda r:r['covariance_flags'].__setitem__(1,1.),
            lambda r:r.__setitem__('mean_called',[0.,0.,0.,1.])]
        for i,mutation in enumerate(mutations):
            record=normal_record();mutation(record)
            with self.subTest(i=i),self.assertRaises(ValueError): analyze_record(record)

    def test_recorded_zero_target_retains_invalid_classification_not_physical_absence(self):
        from water_snell_main_runtime import analyze_record
        record=normal_record();record['first_target_reason']=[0.,0.,0.,65.]
        report=analyze_record(record)
        self.assertEqual(report['reference']['classification'],'INVALID_INPUT')
        self.assertEqual(report['firstReason'],1)
        self.assertFalse(report['reference']['physical']['supported'])

    def test_public_saved_files_qualify_all_sixteen_input_records_without_old_tes_contract(self):
        report=self.invoke()
        self.assertTrue(report['readbackQualified'])
        self.assertTrue(report['inputEvidenceQualified'])
        self.assertTrue(report['guardUniformQualified'])
        self.assertEqual(report['selectedPoints'],16)
        self.assertEqual(report['firstReasonHistogram']['4'],16)
        self.assertTrue(all(p['firstNodeIndex']==0 for p in report['points']))
        self.assertFalse(report['TESObserved'])
        self.assertFalse(report['applicationObserved'])
        self.assertFalse(report['physicalAccepted'])
        self.assertFalse(report['sameFrameGuardAndReadbackProven'])

    def test_public_cli_qualifies_stable_inputs_but_never_operator_or_visual_acceptance(self):
        result=self.invoke(mode='stable',cli=True)
        self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual(report['mode'],'stable')
        self.assertEqual(report['selectedPoints'],16)
        self.assertTrue(report['sourceRecoveryQualified'])
        self.assertEqual(report['minimumApplicationGateUnchanged'],4)
        self.assertFalse(report['applicationObserved'])
        self.assertFalse(report['all48NodeCausesObserved'])
        self.assertFalse(report['physicalAccepted'])

    def test_missing_required_unaccepted_policy_fails_even_when_capture_hash_is_updated(self):
        def altered(files):
            name='WATER-SNELL-MAIN.json';metadata=json.loads(files[name])
            metadata.pop('runtime_accepted');files[name]=json.dumps(metadata).encode()
        with self.assertRaises(ValueError): self.invoke(mutate_files=altered)

    def test_rehashed_stale_roles_source_recovery_and_encoding_metadata_are_rejected(self):
        def alter(key,value):
            def mutate(files):
                name='WATER-SNELL-MAIN.json';metadata=json.loads(files[name]);metadata[key]=value
                files[name]=json.dumps(metadata).encode()
            return mutate
        mutations=[alter('observe','reasons'),alter('C12_is_TES',True),alter('helper_sha256','0'*64),
            alter('target_channels',{'9':['mass','R','T','TIR']}),
            alter('target_code',dict(base=64,node_index_range=[1,48],reason_range=[1,9],none=0,
                formula='indexOnly',same_draw_first_reason=True)),
            lambda f:f.__setitem__('shaders/lib/water_residual_sun.glsl',f['shaders/lib/water_residual_sun.glsl']+b'// extra\n'),
            lambda f:f.__setitem__('shaders/gbuffers_water.tes',f['shaders/gbuffers_water.tes']+b'// extra\n')]
        for i,mutation in enumerate(mutations):
            with self.subTest(i=i),self.assertRaises(ValueError): self.invoke(mutate_files=mutation)

    def test_public_saved_boundary_rejects_bad_identity_bindings_order_state_and_guard(self):
        def duplicate(raw):
            for sampler in raw['samplers'][:4]: sampler['samples'][1].update(x=801,y=451)
        mutations=[lambda r:r.update(worldId='0'*36),lambda r:r.update(seed=True),
            lambda r:r.update(packSha256='0'*64),lambda r:r.update(expectedProgram=99),
            lambda r:r['samplers'][0].update(type=5124),lambda r:r['samplers'][1].update(textureId=71),
            lambda r:r['samplers'][2].update(actualFormat=34842),lambda r:r['stateAfter'].update(binding=99),
            lambda r:r['samplers'][0]['samples'][0].update(rgba=[float('inf'),0,0,1]),duplicate,
            lambda r:r['samplers'][3]['samples'][0].update(rgba=[0,1,0,641])]
        for i,mutation in enumerate(mutations):
            with self.subTest(i=i),self.assertRaises(ValueError): self.invoke(mutate_raw=mutation)
        for mutation in (lambda g:g['uniform'].update(value=0),lambda g:g['uniform'].update(type=5126),
            lambda g:g.update(frameAfter=457),lambda g:g.update(benchmarkState='sampling')):
            with self.assertRaises(ValueError): self.invoke(mutate_guard=mutation)


if __name__=='__main__': unittest.main(verbosity=2)
