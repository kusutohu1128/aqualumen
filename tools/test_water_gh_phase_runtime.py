"""Public selected GH phase observation tests; not a live capture."""
import unittest
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
import shutil
import struct
import subprocess
import sys
import tempfile

from water_gh_phase_runtime import qualify_points, compare_points


def samples():
    return [dict(x=801+i, y=451,
        reasons=[0.0,0.0,0.0,0.0],
        sun_status=[1.0,1.0,12585984.0,0.0],
        outer_state=[15.0,1.0,2.0,-1.0],
        stage=[0.2+i*0.01,0.3,0.5-i*0.01,1.0],
        full_wr=[1.0,1.0,0.95,0.0],
        base_wr=[1.0,1.0,0.95,0.0],
        c0_called=[0.25,0.5,0.75,1.0]) for i in range(16)]


def saved_fixture(directory, phase=0):
    """Explicit synthetic boundary files; frozen real ZIP is source only."""
    from test_water_residual_runtime import fixture
    from water_residual_sun_iris_runtime import COORDINATES
    root=Path(__file__).resolve().parents[1]
    name=f'Aqualumen-ShoreProbe-world-gh-phase-{phase}-diagnostic-v1.zip'
    pack=directory/name
    shutil.copyfile(root/'reports/2026-10-03-water-gh-phase/cpu-pack'/name,pack)
    digest=hashlib.sha256(pack.read_bytes()).hexdigest()
    raw=fixture()
    raw.update(packName=name,packSha256=digest,tag='DEBUG-shore-sampler',
        seam='FinalPassRenderer.renderFinalPass before FullScreenQuadRenderer.renderQuad; after Program.use and CustomUniforms.push',
        rawReadPolicy='GL3.2 glGetTexImage level0, bounded reusable whole-target scratch; only selected texels exported',
        samplingInterpretation='unfiltered level-zero texels, not tone-mapped or reconstructed FINAL texture() values',
        texelCoordinateConvention='integer level-zero texture coordinates; bottom-left origin',
        maximumSelectedTexels=16,selectedTexelsFiniteOnly=True,timingAcceptanceExcluded=True)
    template=raw['samplers'][0]
    raw['samplers']=[];raw['samplerMetadata']=[]
    points=samples()
    for field,i in zip(('reasons','sun_status','outer_state','stage','full_wr','base_wr','c0_called'),range(7)):
        sampler=deepcopy(template)
        sampler.update(name='colortex'+str(9+i),unit=i,textureId=71+i)
        sampler['samples']=[dict(x=x,y=y,rgba=[struct.unpack('<f',struct.pack('<f',v))[0] for v in p[field]])
            for (x,y),p in zip(COORDINATES,points)]
        raw['samplers'].append(sampler)
        raw['samplerMetadata'].append(dict(unit=i,textureId=71+i,
            wholeTargetReadbackBytes=1600*900*16,exportedTexelCount=16))
    guard=dict(schema='aqualumen-sun-guard-observation-v1',available=True,readOnly=True,
        scope='prepared-current-translucent-int-uniform',scopeAuthorized=True,
        worldId=raw['worldId'],world=raw['world'],seed=raw['seed'],dimension=raw['dimension'],
        observerVersion='0.1.0',packName=name,packSha256=digest,
        localIntegratedSinglePlayer=True,currentPipelineMatches=True,containsTessellation=True,
        benchmarkState='complete',supplierAuthorization=1,constructorProgram=43,programBefore=43,
        programAfter=43,frameBefore=456,frameAfter=456,programAndFrameUnchanged=True,
        seam='SodiumShader.updateUniforms TAIL',
        registrationPath='CommonUniforms.addDynamicUniforms TAIL uniform1i PER_FRAME',
        supplierPath='SunAuthorization.value(runtime(game)) fresh each invocation; no cache/latch',
        versions=dict(aqualumen_water_sun_test='0.1.0',aqualumen_benchmark='0.3.9',
            aqualumen_physics='0.3.0',iris='1.8.8+mc1.21.1',sodium='0.6.9+mc1.21.1',minecraft='1.21.1'),
        uniform=dict(name='aqualumenSunTestAuthorized',active=True,location=5,type=5124,size=1,value=1),
        errorFlagConsumed=False,drawIssuedProven=False,fragmentFetchProven=False,
        WNSApplicationProven=False,pngSameFrameProven=False,allGLStateUnchangedProven=False)
    guard['pass']='TRANSLUCENT'
    return raw,pack,guard


class GHRuntime(unittest.TestCase):
    def saved_audit(self,mutate_raw=None,mutate_guard=None,mutate_pack=None):
        from water_gh_phase_runtime import audit
        with tempfile.TemporaryDirectory(prefix='gh-contract-synthetic-') as temporary:
            directory=Path(temporary)
            raw,pack,guard=saved_fixture(directory)
            if mutate_pack:
                with ZipFile(pack) as archive:
                    files={n:archive.read(n) for n in archive.namelist()}
                mutate_pack(files)
                with ZipFile(pack,'w') as archive:
                    for name,value in files.items(): archive.writestr(name,value)
                raw['packSha256']=guard['packSha256']=hashlib.sha256(pack.read_bytes()).hexdigest()
            if mutate_raw: mutate_raw(raw)
            if mutate_guard: mutate_guard(guard)
            raw_file=directory/'synthetic-final.json';guard_file=directory/'synthetic-guard.json'
            raw_file.write_text(json.dumps(raw));guard_file.write_text(json.dumps(guard))
            before={p.name:p.read_bytes() for p in directory.iterdir()}
            try: return audit(raw_file,pack,guard_file)
            finally: self.assertEqual(before,{p.name:p.read_bytes() for p in directory.iterdir()})

    def test_full_base_and_color_are_qualified_as_new_roles_not_covariance_aliases(self):
        value=qualify_points(samples(), authorized=1)
        self.assertEqual(value['selectedPoints'],16)
        self.assertEqual(value['qualifiedAppliedPoints'],16)
        self.assertEqual(value['fullAppliedPoints'],16)
        self.assertEqual(value['baseAppliedPoints'],16)
        self.assertEqual(value['certificateCounts'],dict(zero=0,support=768,unknown=0,calls=768))
        self.assertFalse(value['covarianceObserved'])
        self.assertFalse(value['visualAccepted'])

    def test_color_changes_with_and_without_admission_changes_are_separate_evidence(self):
        before=samples();after=deepcopy(before)
        after[0]['c0_called'][0]=0.5
        after[1]['c0_called'][0]=0.5
        after[1]['full_wr']=[0.0,0.0,0.5,0.0]
        after[1]['base_wr']=[0.0,0.0,0.5,0.0]
        after[1]['sun_status']=[1.0,0.0,0.0,1.0]
        value=compare_points(before,after)
        self.assertEqual(value['changedColorPoints'],2)
        self.assertEqual(value['changedLegacyAdmissionPoints'],1)
        self.assertEqual(value['changedColorWithStableLegacyAdmissionPoints'],1)
        self.assertEqual(value['changedColorWithChangedLegacyAdmissionPoints'],1)
        self.assertFalse(value['finiteQuadratureCauseProven'])

    def test_valid_eligible_legacy_snapshot_cannot_claim_no_application(self):
        value=samples()
        value[0]['full_wr'][1]=0.0
        value[0]['sun_status']=[1.0,0.0,0.0,1.0]
        with self.assertRaises(ValueError):
            qualify_points(value)

    def test_public_file_audit_qualifies_all_seven_new_roles_and_exact_source(self):
        from water_gh_phase_runtime import audit
        with tempfile.TemporaryDirectory(prefix='gh-file-synthetic-') as temporary:
            directory=Path(temporary)
            raw,pack,guard=saved_fixture(directory)
            raw_file=directory/'synthetic-final.json';guard_file=directory/'synthetic-guard.json'
            raw_file.write_text(json.dumps(raw));guard_file.write_text(json.dumps(guard))
            before={p.name:p.read_bytes() for p in directory.iterdir()}
            result=audit(raw_file,pack,guard_file)
            self.assertEqual(before,{p.name:p.read_bytes() for p in directory.iterdir()})
            self.assertEqual(result['selectedPoints'],16)
            self.assertEqual(result['qualifiedAppliedPoints'],16)
            self.assertTrue(result['actualSevenRoleBindingsQualified'])
            self.assertTrue(result['sourceRecoveryQualified'])
            self.assertEqual(result['phase_degrees'],0)
            self.assertFalse(result['covarianceObserved'])
            self.assertFalse(result['sameFrameProven'])
            self.assertFalse(result['visualAccepted'])

    def test_public_cli_accepts_phase45_but_keeps_less_than_four_applied_negative(self):
        with tempfile.TemporaryDirectory(prefix='gh-cli-synthetic-') as temporary:
            directory=Path(temporary)
            raw,pack,guard=saved_fixture(directory,phase=45)
            raw_file=directory/'synthetic-final.json';guard_file=directory/'synthetic-guard.json'
            guard_file.write_text(json.dumps(guard))
            command=[sys.executable,'-B',str(Path(__file__).with_name('water_gh_phase_runtime.py')),
                     str(raw_file),str(pack),str(guard_file)]
            for count in (16,3,0):
                for i,p in enumerate(raw['samplers'][1]['samples']):
                    p['rgba']=[1,1,12585984,0] if i<count else [1,0,0,0]
                raw_file.write_text(json.dumps(raw))
                before={p.name:p.read_bytes() for p in directory.iterdir()}
                process=subprocess.run(command,capture_output=True,text=True,check=False)
                self.assertEqual(process.returncode,0 if count>=4 else 1,process.stderr)
                result=json.loads(process.stdout)
                self.assertEqual(result['phase_degrees'],45)
                self.assertEqual(result['qualifiedAppliedPoints'],count)
                self.assertEqual(result['operatorActiveQualified'],count>=4)
                self.assertTrue(result['readbackQualified'])
                if count<4:
                    self.assertEqual(result['applicationVerdict'],'NEGATIVE_INSUFFICIENT_APPLICATION')
                self.assertEqual(before,{p.name:p.read_bytes() for p in directory.iterdir()})

    def test_public_file_rejects_contradictory_first_reason_group_or_loop_accounting(self):
        for reason,status in (([3,0,1,0],[1,0,0,1]),([0,1,0,0],[1,0,0,1]),
                              ([3,1,0,0],[1,0,0,2]),([3,0,0,0],[1,0,0,1])):
            def mutation(raw):
                raw['samplers'][0]['samples'][0]['rgba']=reason
                raw['samplers'][1]['samples'][0]['rgba']=status
            with self.subTest(reason=reason,status=status),self.assertRaises(ValueError):
                self.saved_audit(mutate_raw=mutation)

    def test_public_file_requires_seven_active_distinct_typed_bindings_and_fixed_order(self):
        mutations=[lambda r:r['samplers'][4].update(active=False),
            lambda r:r['samplers'][6].update(type=35679),
            lambda r:r['samplers'][5].update(size=True),
            lambda r:r['samplers'][4].update(actualFormat=34842),
            lambda r:r['samplers'][4].update(width=1024),
            lambda r:r['samplers'][6].update(textureId=71),
            lambda r:r['samplers'][5].update(unit=0),
            lambda r:r['samplers'].pop(),
            lambda r:r['samplers'].reverse(),
            lambda r:r['samplers'][6]['samples'][0].update(x=802),
            lambda r:r['samplers'][0]['samples'][1].update(x=801,y=451),
            lambda r:r['samplerMetadata'][6].update(exportedTexelCount=True)]
        for i,mutation in enumerate(mutations):
            with self.subTest(case=i),self.assertRaises(ValueError):
                self.saved_audit(mutate_raw=mutation)

    def test_public_file_preserves_guard_world_state_finite_and_tes_gates(self):
        def stale_state(raw): raw['stateAfter']['binding']+=1
        def bool_state(raw): raw['stateBefore']['skipRows']=raw['stateAfter']['skipRows']=False
        def constant_stage(raw):
            for p in raw['samplers'][3]['samples']: p['rgba']=[.2,.3,.5,1]
        def nonfinite(raw): raw['samplers'][6]['samples'][0]['rgba'][0]=float('nan')
        for mutation in (stale_state,bool_state,constant_stage,nonfinite,
                         lambda r:r.update(worldId='unapproved'),lambda r:r.update(seed=True),
                         lambda r:r.update(snapshotFrame=True),lambda r:r.update(program=0),
                         lambda r:r['samplers'][2]['samples'][0].update(rgba=[.006,.002,.006,15])):
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                self.saved_audit(mutate_raw=mutation)
        for mutation in (lambda g:g['uniform'].update(type=5126),lambda g:g['uniform'].update(value=0),
                         lambda g:g.update(frameAfter=457),lambda g:g.update(benchmarkState='sampling'),
                         lambda g:g.update(packSha256='0'*64)):
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                self.saved_audit(mutate_guard=mutation)

    def test_public_file_rejects_rehashed_source_parent_or_authoritative_policy_tampering(self):
        def helper(files):
            name='shaders/lib/water_residual.glsl'
            files[name]+=b'// synthetic tamper\n'
            policy=json.loads(files['WATER-GH-PHASE.json'])
            policy['current_sha256'][name]=hashlib.sha256(files[name]).hexdigest()
            files['WATER-GH-PHASE.json']=json.dumps(policy).encode()
        def manifest(files):
            policy=json.loads(files['WATER-GH-PHASE.json']);policy['visual_accepted']=True
            files['WATER-GH-PHASE.json']=json.dumps(policy).encode()
        def physical(files):
            policy=json.loads(files['WATER-GH-PHASE.json']);policy['role']='physical'
            files['WATER-GH-PHASE.json']=json.dumps(policy).encode()
        for mutation in (helper,manifest,physical,
            lambda f:f.update({'GH-PHASE-original/parent.zip':b'synthetic wrong parent'}),
            lambda f:f.update({'shaders/gbuffers_water.tes':b'synthetic changed stage'}),
            lambda f:f.update({'unapproved.txt':b'synthetic extra'})):
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                self.saved_audit(mutate_pack=mutation)


if __name__=='__main__':
    unittest.main(verbosity=2)
