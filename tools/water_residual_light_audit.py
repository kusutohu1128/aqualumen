"""NEW CPU saved native audit. No GL/app actions or frozen file mutation.

Synthetic tests exercise audit plumbing only. Actual result classification
requires all saved shader/input/domain qualifications before response gates.
"""
from __future__ import annotations
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys

from water_residual_light_integral import laguerre_rule, _prepare, _kernel

FROZEN_MATH_SHA = 'f5b6db7013907ab4baf6e28df0542a2f2066ddaef1c8cdb6e8a28fc4e352de92'
SIZE = 257
FIXED = ((128,128),(132,131),(123,127),(132,135),(132,127),(142,134))
ROI = tuple((x,y) for y in range(88,169) for x in range(88,169)
            if (x-128)**2+(y-128)**2 <= 40**2)
ABSOLUTE, RELATIVE, EPS8 = 2e-6, 2e-4, 8*2**-23


def classify(qualified, assertions):
    if not qualified:
        return 'INCONCLUSIVE'
    return 'PASS' if all(assertions) else 'RED'


def _read(path, count, manifest):
    raw = path.read_bytes()
    if sys.byteorder != 'little' or len(raw) != count*4:
        raise ValueError('saved float size/endianness mismatch: '+str(path))
    values = array.array('f');values.frombytes(raw)
    if not all(math.isfinite(x) for x in values):
        raise ValueError('nonfinite saved float: '+str(path))
    manifest[str(path)] = hashlib.sha256(raw).hexdigest()
    return values


def _pixel(values, pixel):
    x,y = pixel;offset = (y*SIZE+x)*4
    return list(values[offset:offset+4])


def _target_rule():
    sigma = .00465
    result = []
    for u,w in laguerre_rule(8):
        cosine,sine = 1-sigma*sigma*u,sigma*math.sqrt(u*(2-sigma*sigma*u))
        for j in range(16):
            phi=2*math.pi*(j+.5)/16
            result.append(((sine*math.cos(phi),cosine,sine*math.sin(phi)),
                           w*sigma*sigma*(2*math.pi/16)))
    return tuple(result)


TARGETS = _target_rule()


def source_reference(fixture):
    """Locally cached rule; hash-pinned private math dependency, not a rewrite.

    Prepare current saved raw inputs once per pixel. Entire new source rejects
    if any node fails; no partial sum, deleted nodes, or normalization.
    """
    context = _prepare(fixture)
    terms = []
    for direction, weight in TARGETS:
        terms.append(weight*_kernel(context,direction)['kernel'])
    transfer=math.fsum(terms)
    return [transfer*.25,transfer*.125,transfer*.0625]


def erase_blocks(source, begin, end, replacement=''):
    """Exact paired tagged byte-block recovery; no permissive regex matching."""
    count=0
    while begin in source:
        start=source.index(begin);finish=source.find(end,start+len(begin))
        if finish<0 or begin in source[start+len(begin):finish]:
            raise ValueError('malformed/nested source marker')
        source=source[:start]+replacement+source[finish+len(end):];count+=1
    if end in source:raise ValueError('orphan source marker end')
    return source,count


def _compare(a,b,absolute=0.,relative=0.):
    if len(a)!=len(b):raise ValueError('comparison arity differs')
    maximum=0.;failures=0
    for x,y in zip(a,b):
        error=abs(x-y);maximum=max(maximum,error)
        failures+=error>absolute+relative*max(abs(x),abs(y))
    return dict(accepted=failures==0,scalar_samples=len(a),failed_scalars=failures,
                maximum_absolute_delta=maximum,absolute_tolerance=absolute,relative_tolerance=relative)


def _legacy_domain(slots,pixel):
    normal,cov,status,eye,flags=(_pixel(slots[s],pixel) for s in (1,2,4,5,6))
    determinant=cov[0]*cov[2]-cov[1]*cov[1]
    coefficients=_pixel(slots[3],pixel)
    return (flags==[1.,1.,1.,1.] and eye[3]==1
            and status[0]==1 and status[1]==1 and status[2]>0 and status[3]==0
            and cov[0]>=0 and cov[2]>=0 and determinant>=0 and cov[0]+cov[2]>1e-5
            and abs(coefficients[0]-1)<=2e-5 and min(coefficients[1:])>=0
            and coefficients[3]<=coefficients[1]+2e-5
            and abs(coefficients[1]+coefficients[2]-coefficients[0])<=2e-5)


def _fixture(slots,pixel):
    return dict(mean_normal=_pixel(slots[1],pixel)[:3],covariance=_pixel(slots[2],pixel)[:3],
                view_to_eye=_pixel(slots[5],pixel)[:3])


def _sha(path,manifest):
    raw=path.read_bytes();value=hashlib.sha256(raw).hexdigest();manifest[str(path)]=value
    return value


def controlled_source(kind):
    """Exact derivative-free native input seam, not a new lighting model."""
    if kind in (1,2):
        sigma={1:'0.0046499999999999996',2:'0.080000000000000002'}[kind]
        expression=('vec3(0.25,0.125,0.0625)*exp(-dot(normalize(ray)-vec3(0.0,1.0,0.0),'
                    'normalize(ray)-vec3(0.0,1.0,0.0))/(2.0*'+sigma+'*'+sigma+'))')
    else:expression={3:'vec3(0.25,0.125,0.0625)',4:'vec3(0.0)'}[kind]
    return '// ANGULAR_SOURCE_BEGIN\n    return sampleSky(lut,ray)+'+expression+';\n// ANGULAR_SOURCE_END\n'


def _source_checks(run,recorded,manifest):
    original=(run/'source-original-expanded.fsh').read_text()
    baseline=(run/'guard-baseline-expanded.fsh').read_text()
    resolved=(run/'resolved-parent-expanded.fsh').read_text()
    pin='62837f5fe0cdfa21c509be48db408941164d7b5a96c853d57c5c4de0a09698b3'
    if _sha(run/'guard-baseline-expanded.fsh',manifest)!=pin or recorded['baselineSHA256']!=pin:
        raise ValueError('physical baseline pin mismatch')
    if _sha(run/'source-original-expanded.fsh',manifest)!=recorded['activeExpandedSHA256']:
        raise ValueError('active expanded source hash mismatch')
    oracle_sha=_sha(run/'frozen-continuous-oracle.json',manifest)
    if oracle_sha!='f8ec3ab6a5e330abdad8e493d913e54f2481a308dc1612fdf1c5106987d9d2c5' or oracle_sha!=recorded['oracleSHA256']:
        raise ValueError('frozen continuous reference changed')
    _sha(run/'resolved-parent-expanded.fsh',manifest)
    for i in range(3):_sha(run/f'geometry-stage{i}.glsl',manifest)
    recovered=original
    for tag in ('INCLUDE','RESTORE_ENV','CALL_BEGIN_ALIAS','CALL_END_ALIAS'):
        recovered,count=erase_blocks(recovered,f'// AQUALUMEN_LIGHT_{tag}_BEGIN\n',f'// AQUALUMEN_LIGHT_{tag}_END\n')
        if count!=1:raise ValueError('missing/duplicate inner light seam')
    if recovered!=baseline:raise ValueError('inner erasure does not recover physical baseline')
    for tag in ('HOOK','INCLUDE'):
        recovered,count=erase_blocks(recovered,f'// AQUALUMEN_RESIDUAL_{tag}_BEGIN\n',f'// AQUALUMEN_RESIDUAL_{tag}_END\n')
        if count!=1:raise ValueError('missing/duplicate outer residual seam')
    if recovered!=resolved:raise ValueError('outer erasure does not recover resolved parent')
    for case in recorded['cases']:
        kind=('narrow','broad','constant','dark').index(case['source'])+1
        if case['source_kind']!=kind or case['light_enabled']!=int(case['path'].endswith('-candidate')) or case['path']!=case['source']+('-candidate' if case['light_enabled'] else '-control'):
            raise ValueError('source/configuration matrix differs')
        directory=run/case['path'];pure=(directory/'pure-expanded.fsh').read_text();observer=(directory/'observer-expanded.fsh').read_text()
        for name,key in (('pure-expanded.fsh','pureSourceSHA256'),('observer-expanded.fsh','observerSourceSHA256')):
            if _sha(directory/name,manifest)!=case[key]:raise ValueError('compiled source digest mismatch')
        recovered,count=erase_blocks(observer,'\n// RESIDUAL_NATIVE_STORE_BEGIN\n','// RESIDUAL_NATIVE_STORE_END\n')
        if count<1 or recovered!=pure:raise ValueError('observer erasure must recover compiled pure exactly')
        start=pure.index('// LIGHT_NATIVE_CONFIG_BEGIN\n');finish=pure.index('// LIGHT_NATIVE_CONFIG_END\n',start)
        config=pure[start:finish]
        if re.findall(r'^#define WLS_LIGHT_ENABLED ([01])$',config,re.M)!=[str(case['light_enabled'])] or re.findall(r'^#define WLS_SOURCE_KIND ([1-4])$',config,re.M)!=[str(case['source_kind'])]:
            raise ValueError('compiled source configuration differs')
        recovered,count=erase_blocks(pure,'// LIGHT_NATIVE_CONFIG_BEGIN\n','// LIGHT_NATIVE_CONFIG_END\n')
        if count!=1:raise ValueError('configuration seam count differs')
        if recovered.count(controlled_source(kind))!=1:raise ValueError('controlled radiance/width source seam differs')
        recovered,count=erase_blocks(recovered,'// ANGULAR_SOURCE_BEGIN\n','// ANGULAR_SOURCE_END\n',
            '    return sampleSky(lut,ray)+sunDisk(ray,sunDirection(),lut)+moonDisk(ray,sunDirection());\n')
        if count!=1 or recovered!=original:raise ValueError('source/configuration erasure must recover active template')
        for program in case['programs']:
            if not program['linked'] or sorted(program['stage_types'])!=[35632,35633,36487,36488] or program['tess_layout'][:4]!=[3,4,514,2305]:
                raise ValueError('actual four-stage linked/reflection contract differs')
    return dict(inner_physical_recovery_exact=True,outer_resolved_recovery_exact=True,
                all_compiled_source_config_observer_recovery_exact=True,controlled_source_seams_exact=True,attached_four_stages=True)


def _inputs(directory,manifest):
    path=directory/'actual-inputs.json';_sha(path,manifest);meta=json.loads(path.read_text())
    if not meta['bindingRestored'] or meta['currentProgramBefore']!=meta['program'] or meta['currentProgramAfter']!=meta['program'] or meta['activeTextureBefore']!=meta['activeTextureAfter'] or meta['textureBindingBefore']!=meta['textureBindingAfter']:
        raise ValueError('actual input query state not restored')
    if meta['fixedFunctionProjection']!=meta['matrices']['gbufferProjection'] or meta['fixedFunctionModelView']!=meta['matrices']['gbufferModelView']:
        raise ValueError('actual fixed/uniform matrices disagree')
    if len(meta['samplers'])!=8 or len(meta['targets'])!=8:
        raise ValueError('sampler/target arity differs')
    digests={};sampler_meta=[]
    for sampler in meta['samplers']:
        values=_read(directory/sampler['file'],sampler['width']*sampler['height']*sampler['components'],manifest)
        digests[sampler['file']]=manifest[str(directory/sampler['file'])]
        sampler_meta.append({k:v for k,v in sampler.items() if k!='texture'})
        if sampler['unit'] in (2,7) and any(value!=(1. if i%4==3 else 0.) for i,value in enumerate(values)):
            raise ValueError('declared black sky/solar cache input changed')
    for target in meta['targets']:
        if (target['width'],target['height'],target['internalFormat'])!=(SIZE,SIZE,34836):
            raise ValueError('RGBA32F target storage differs')
    if (meta['depth']['width'],meta['depth']['height'],meta['depth']['internalFormat'])!=(SIZE,SIZE,36012):
        raise ValueError('depth32F storage differs')
    for name in ('uploaded-open-water-vertices.f32','uploaded-water-vertices.f32','actual-bathymetry.rgba32f'):
        digests[name]=_sha(directory/name,manifest)
    return dict(matrices=meta['matrices'],samplers=sampler_meta,
                fixed_projection=meta['fixedFunctionProjection'],fixed_modelview=meta['fixedFunctionModelView'],
                raw_input_digests=digests)


def audit(run):
    math_sha=hashlib.sha256(Path(__file__).with_name('water_residual_light_integral.py').read_bytes()).hexdigest()
    if math_sha!=FROZEN_MATH_SHA:raise ValueError('frozen CPU math dependency changed')
    manifest={};_sha(run/'result.json',manifest);recorded=json.loads((run/'result.json').read_text())
    if recorded['schema']!='aqualumen-native-residual-light-v1' or recorded['size']!=SIZE or recorded['phase_seconds']!=120 or recorded['quadrature_order']!=3:
        raise ValueError('native schema/size/phase/rule differs')
    labels={source+'-'+role for source in ('narrow','broad','constant','dark') for role in ('control','candidate')}
    if len(recorded['cases'])!=8 or {case['path'] for case in recorded['cases']}!=labels:
        raise ValueError('case matrix missing/duplicated')
    policy=dict(numeric_absolute=ABSOLUTE,numeric_relative=RELATIVE,passive_C0_absolute=5e-4,
                passive_C0_relative=2e-4,passive_depth_absolute=2e-6,coefficient_absolute=2e-5,
                common_xyz_absolute_relative=EPS8,ROI_center=[128,128],ROI_integer_radius=40)
    if recorded['policy']!=policy:raise ValueError('predeclared native policy changed')
    frozen=json.loads((run/'frozen-continuous-oracle.json').read_text())
    targets={tuple(item['pixel']):item for item in frozen['dense_references'] if item['source']=='narrow'}
    if set(targets)!=set(FIXED) or not all(item['reference']['reference_qualified'] for item in targets.values()):
        raise ValueError('six qualified frozen narrow targets differ')
    sources=_source_checks(run,recorded,manifest);frames={};telemetry=[];case_domains=[];baseline_frame=None;baseline_inputs=None
    for case in recorded['cases']:
        name=case['path'];directory=run/name;captures={}
        for label in ('pure','observer'):
            slots={slot:_read(directory/f'{label}-slot{slot}.rgba32f',SIZE*SIZE*4,manifest) for slot in range(8)}
            depth=_read(directory/f'{label}-depth.f32',SIZE*SIZE,manifest)
            for slot in range(8):
                repeat=_read(directory/f'{label}-repeat-slot{slot}.rgba32f',SIZE*SIZE*4,manifest)
                telemetry.append(dict(case=name,comparison=f'{label}-slot{slot}-repeat',**_compare(slots[slot],repeat)))
            repeat=_read(directory/f'{label}-repeat-depth.f32',SIZE*SIZE,manifest)
            telemetry.append(dict(case=name,comparison=f'{label}-depth-repeat',**_compare(depth,repeat)))
            captures[label]=dict(slots=slots,depth=depth)
        pure,observer=captures['pure'],captures['observer'];slots=observer['slots']
        telemetry.append(dict(case=name,comparison='observer-C0-passive',**_compare(pure['slots'][0],slots[0],5e-4,2e-4)))
        telemetry.append(dict(case=name,comparison='observer-depth-passive',**_compare(pure['depth'],observer['depth'],2e-6)))
        inputs=_inputs(directory,manifest)
        if baseline_inputs is None:baseline_inputs=inputs
        elif inputs!=baseline_inputs:raise ValueError('actual textures/map/VBO/matrices differ between cases')
        if baseline_frame is not None:
            for slot in (1,5,7):
                telemetry.append(dict(case=name,comparison=f'common-slot{slot}-xyz',**_compare(
                    [x for i,x in enumerate(baseline_frame['slots'][slot]) if i%4!=3],
                    [x for i,x in enumerate(slots[slot]) if i%4!=3],EPS8,EPS8)))
                if slot!=7:telemetry.append(dict(case=name,comparison=f'common-slot{slot}-alpha',**_compare(baseline_frame['slots'][slot][3::4],slots[slot][3::4])))
            for slot in (2,6):telemetry.append(dict(case=name,comparison=f'common-slot{slot}-exact',**_compare(baseline_frame['slots'][slot],slots[slot])))
            telemetry.append(dict(case=name,comparison='common-depth-exact',**_compare(baseline_frame['depth'],observer['depth'])))
            telemetry.append(dict(case=name,comparison='common-coefficients',**_compare(baseline_frame['slots'][3],slots[3],2e-5)))
        else:baseline_frame=observer
        expected_apply=1 if name=='narrow-candidate' else 0
        legacy=sum(_legacy_domain(slots,pixel) for pixel in ROI)
        applied=sum(_pixel(slots[7],pixel)[3]==expected_apply for pixel in ROI)
        pins=True
        for pixel,item in targets.items():
            target=item['actual_fixture'];current=_fixture(slots,pixel)
            for field in ('mean_normal','view_to_eye'):
                pins=pins and all(abs(a-b)<=EPS8*(1+abs(b)) for a,b in zip(current[field],target[field]))
            pins=pins and current['covariance']==target['covariance'] and _pixel(slots[1],pixel)[3]==1 and _pixel(slots[2],pixel)[3]==struct.unpack('<f',struct.pack('<f',.035))[0]
        case_domains.append(dict(case=name,ROI_points=len(ROI),legacy_qualified_pixels=legacy,
                                 fixed_six_inputs_qualified=pins,expected_feature_application=expected_apply,matching_feature_pixels=applied))
        frames[name]=captures
    for source in ('broad','constant','dark'):
        for mode in ('pure','observer'):
            telemetry.append(dict(case=source,comparison=f'non-narrow-{mode}-old-output',**_compare(
                frames[source+'-control'][mode]['slots'][0],frames[source+'-candidate'][mode]['slots'][0],EPS8,EPS8)))
    fixed_continuous=[]
    for role in ('control','candidate'):
        for mode in ('pure','observer'):
            narrow=frames['narrow-'+role][mode]['slots'][0];dark=frames['dark-control'][mode]['slots'][0]
            for pixel in FIXED:
                expected=targets[pixel]['reference']['source_difference_C0']
                actual=[a-b for a,b in zip(_pixel(narrow,pixel)[:3],_pixel(dark,pixel)[:3])]
                errors=[abs(a-b) for a,b in zip(actual,expected)];bounds=[ABSOLUTE+RELATIVE*abs(b) for b in expected]
                fixed_continuous.append(dict(role=role,observation=mode,pixel=pixel,actual_source_delta=actual,
                    frozen_continuous_source_delta=expected,absolute_errors=errors,bounds=bounds,accepted=all(a<=b for a,b in zip(errors,bounds))))
    alias_miss=any(not item['accepted'] for item in fixed_continuous if item['role']=='control')
    fixed_candidate_pass=all(item['accepted'] for item in fixed_continuous if item['role']=='candidate')
    fresh=[];oracle_failures=[];maximum=0.;numeric_accepted=0;fixed=[]
    candidate=frames['narrow-candidate']['observer']['slots']
    pure=frames['narrow-candidate']['pure']['slots'][0];dark=frames['dark-control']['pure']['slots'][0]
    for pixel in ROI:
        fixture=_fixture(candidate,pixel);actual=[x-y for x,y in zip(_pixel(pure,pixel)[:3],_pixel(dark,pixel)[:3])]
        try:expected=source_reference(fixture)
        except ValueError as error:
            oracle_failures.append(dict(pixel=pixel,reason=str(error)));continue
        errors=[abs(x-y) for x,y in zip(actual,expected)];gates=[ABSOLUTE+RELATIVE*abs(x) for x in expected]
        accepted=all(x<=y for x,y in zip(errors,gates));numeric_accepted+=accepted;maximum=max(maximum,*errors)
        point=dict(pixel=pixel,actual_fixture=fixture,actual_source_delta=actual,CPU_light_reference=expected,
                   absolute_errors=errors,bounds=gates,accepted=accepted)
        fresh.append(point)
        if pixel in FIXED:fixed.append(point)
    qualified=all(item['accepted'] for item in telemetry) and all(case['legacy_qualified_pixels']==len(ROI) and case['fixed_six_inputs_qualified'] for case in case_domains) and not oracle_failures
    assertions=[all(case['matching_feature_pixels']==len(ROI) for case in case_domains),numeric_accepted==len(ROI),fixed_candidate_pass,alias_miss]
    status=classify(qualified,assertions)
    return dict(schema='aqualumen-saved-native-light-independent-cpu-audit-v1',run=str(run.resolve()),
        recorded_native_status=recorded['status'],audit_status=status,
        recorded_status_agrees=recorded['status']==status,fixture_qualified=qualified,
        sources=sources,frozen_math_sha256=math_sha,math_dependency='Hash-pinned private _prepare/_kernel used without monkeypatch; radial/light nodes cached in NEW auditor only.',
        scalar_numeric_absolute=ABSOLUTE,scalar_numeric_relative_expected=RELATIVE,
        cases=case_domains,telemetry_comparisons=telemetry,ROI_points=len(ROI),CPU_evaluated_pixels=len(fresh),
        CPU_node_evaluations=len(fresh)*len(TARGETS),ROI_numeric_accepted_pixels=numeric_accepted,
        maximum_C0_component_absolute_error=maximum,fixed_six=fixed,ROI_fresh_inputs_and_comparisons=fresh,
        fixed_continuous_checks=fixed_continuous,fixed_candidate_continuous_accepted=fixed_candidate_pass,
        old_alias_negative_control_observed=alias_miss,
        oracle_domain_failures=oracle_failures,raw_source_input_sha256_manifest=manifest,
        scope='Saved full predeclared5025 ROI/source/application and CPU arithmetic audit only. No calibrated Sun, global tails/receivers, singular limits, shader/GL execution by auditor, native solar filtering, natural Iris, appearance/motion/FPS, energy, reciprocity or shipping acceptance.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--expect',choices=('RED','PASS','INCONCLUSIVE'),required=True);args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink():parser.error('NEW output required')
    try:report=audit(args.run)
    except (OSError,ValueError,KeyError,TypeError) as error:
        report=dict(schema='aqualumen-saved-native-light-independent-cpu-audit-v1',run=str(args.run),
                    audit_status='INCONCLUSIVE',fixture_qualified=False,error=str(error))
    consistent=report['audit_status']==args.expect and report.get('recorded_status_agrees',False)
    report.update(expected_status=args.expect,audit_consistent=consistent)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    print(('CONSISTENT' if consistent else 'INCONCLUSIVE/MISMATCH')+' saved '+report['audit_status']+'; '+str(args.output))
    return 0 if consistent else 2


if __name__=='__main__':raise SystemExit(main())
