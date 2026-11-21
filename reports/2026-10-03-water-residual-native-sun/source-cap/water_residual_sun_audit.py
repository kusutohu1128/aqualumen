"""NEW CPU saved native Sun audit; no GL/app actions or frozen edits."""
import math
import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path
import re
import struct
from water_residual_sun_integral import sun_integral,solar_beam
from water_residual_light_audit import _read,_compare,_pixel,_sha,erase_blocks,SIZE,ROI,FIXED

ABSOLUTE,RELATIVE,EPS8=2e-6,2e-4,8*2**-23
SUN_MATH_SHA='d58d86873b192f6015ce0ae50c2dbce4d0ac839d6feb603685ddde217df8de1e'
IO_SHA='537f0057149312c5974c1a89c873193f9f9c456c1c46fa523fdc5da5afb375f0'
RECEIPT_SHA='73e3a3fba566751ba5e4f9b608475712a4e4d89d47201773f68062b41ed5f8f0'
BASELINE_SHA='62837f5fe0cdfa21c509be48db408941164d7b5a96c853d57c5c4de0a09698b3'
ATMOSPHERE_SHA='89e1d66b88144e018e3d7b012a3e92319209070f38b6e1918c505f965b29ece4'
PROJECT=Path(__file__).resolve().parents[1]


@lru_cache(maxsize=50000)
def _unit_cap(normal,covariance,view,axis,radial=4,azimuth=12):
    # Exact pure linear scaling of the frozen public cap integral. Cache keys
    # retain every observed binary32 component; no field rounding/normalization.
    return sun_integral(dict(mean_normal=normal,covariance=covariance,view_to_eye=view),axis,
                        (1.,1.,1.),radial_order=radial,azimuth_order=azimuth)


def _reference(point,axis,beam,radial=4,azimuth=12):
    result=_unit_cap(tuple(point['mean_normal']),tuple(point['covariance']),tuple(point['view_to_eye']),tuple(axis),radial,azimuth)
    if not result['domain_qualified']:return result
    return dict(domain_qualified=True,source_difference_C0=[x*result['source_difference_C0'][0] for x in beam])


def central_source_response(positive_C0,zero_C0,legacy_R,positive_scatter,zero_scatter):
    vectors=(positive_C0,zero_C0,positive_scatter,zero_scatter)
    if any(len(x)!=3 or not all(math.isfinite(v) for v in x) for x in vectors) or not math.isfinite(legacy_R) or legacy_R<0:
        raise ValueError('finite C0/scatter RGB and nonnegative actual legacy R required')
    return [(a-b)-legacy_R*(c-d) for a,b,c,d in zip(*vectors)]


def _domain(point):
    for field,count in (('C0',3),('scatter',3),('mean_normal',3),('covariance',3),('view_to_eye',3),('coefficients',4),('WR_status',4),('flags',4)):
        if len(point[field])!=count or not all(math.isfinite(x) for x in point[field]):return False
    scalars=[point[x] for x in ('eligible','requested','applied','footprint')]
    if not all(math.isfinite(x) for x in scalars):return False
    xx,xz,zz=point['covariance'];a=point['coefficients'];status=point['WR_status']
    return (point['flags']==[1.,1.,1.,1.] and point['eligible']==1 and point['sky_qualified'] is True
        and status[:2]==[1.,1.] and status[2]>0 and status[3]==0
        and xx>0 and zz>0 and xx*zz-xz*xz>0 and xx+zz>1e-5 and point['footprint']>=.035
        and abs(a[0]-1)<=2e-5 and min(a[1:])>=0 and a[3]<=a[1]+2e-5
        and abs(a[1]+a[2]-a[0])<=2e-5 and point['requested'] in (0.,1.) and point['applied'] in (0.,1.))


def audit_sample(positive,zero,sun_direction,beam,enabled,refine=False):
    """Public actual-input numerical seam; controls never imply filtered-AA bug."""
    try:
        if enabled not in (0,1) or not _domain(positive) or not _domain(zero):
            return dict(status='INCONCLUSIVE',fixture_qualified=False,reason='Legacy/sky/source status domain invalid')
        if len(beam)!=3 or not all(math.isfinite(x) and x>=0 for x in beam) or sum(beam)<=0:
            return dict(status='INCONCLUSIVE',fixture_qualified=False,reason='Zero source cannot qualify as positive Sun response')
        for field in ('mean_normal','view_to_eye'):
            if any(abs(a-b)>EPS8*(1+max(abs(a),abs(b))) for a,b in zip(positive[field],zero[field])):
                return dict(status='INCONCLUSIVE',fixture_qualified=False,reason='Paired geometry input mismatch')
        if positive['covariance']!=zero['covariance'] or positive['footprint']!=zero['footprint'] or any(abs(a-b)>2e-5 for a,b in zip(positive['coefficients'],zero['coefficients'])):
            return dict(status='INCONCLUSIVE',fixture_qualified=False,reason='Paired covariance/footprint/legacy coefficient mismatch')
        reference=_reference(positive,sun_direction,beam)
        if not reference['domain_qualified']:return dict(status='INCONCLUSIVE',fixture_qualified=False,reason=reference['invalid_reason'])
        actual=central_source_response(positive['C0'],zero['C0'],positive['coefficients'][1],positive['scatter'],zero['scatter'])
        expected=reference['source_difference_C0'];errors=[abs(a-b) for a,b in zip(actual,expected)]
        bounds=[ABSOLUTE+RELATIVE*abs(x) for x in expected];numeric=all(e<=g for e,g in zip(errors,bounds))
        selected_quality=True;refinement={}
        if refine:
            high=_reference(positive,sun_direction,beam,8,24);highest=_reference(positive,sun_direction,beam,12,48)
            if not high['domain_qualified'] or not highest['domain_qualified']:
                return dict(status='INCONCLUSIVE',fixture_qualified=False,reason='Selected refined source domain invalid',refined8x24=high,refined12x48=highest)
            target=highest['source_difference_C0'];fine=high['source_difference_C0']
            convergence_errors=[abs(a-b) for a,b in zip(fine,target)]
            convergence_bounds=[2e-8+2e-6*max(abs(a),abs(b)) for a,b in zip(fine,target)]
            reference_bounds=[ABSOLUTE+RELATIVE*abs(x) for x in target]
            finite_errors=[abs(a-b) for a,b in zip(expected,target)]
            actual_errors=[abs(a-b) for a,b in zip(actual,target)]
            converged=all(e<=g for e,g in zip(convergence_errors,convergence_bounds))
            finite_quality=all(e<=g for e,g in zip(finite_errors,reference_bounds))
            actual_quality=all(e<=g for e,g in zip(actual_errors,reference_bounds))
            selected_quality=converged and finite_quality and actual_quality
            refinement=dict(refined8x24=high,refined12x48=highest,convergence_absolute_errors=convergence_errors,
                convergence_bounds=convergence_bounds,convergence_accepted=converged,
                selected_finite_to_refined_errors=finite_errors,selected_actual_to_refined_errors=actual_errors,
                selected_reference_bounds=reference_bounds,selected_finite_to_refined_accepted=finite_quality,
                selected_actual_to_refined_accepted=actual_quality,selected_quality_accepted=selected_quality)
        application=(positive['requested']==enabled and positive['applied']==enabled and zero['requested']==enabled and zero['applied']==0)
        return dict(status=('PASS' if numeric and application and selected_quality else 'RED') if enabled else ('CONTROL' if application else 'RED'),
            fixture_qualified=True,numeric_accepted=numeric,application_accepted=application,
            actual_source_response=actual,CPU_finite_cap_reference=expected,absolute_errors=errors,bounds=bounds,
            actual_legacy_R=positive['coefficients'][1],measured_scatter_delta=[a-b for a,b in zip(positive['scatter'],zero['scatter'])],
            centralsharp_negative_control=bool(not numeric) if not enabled else None,
            native_pixel_filter_equivalence_accepted=False,physical_accepted=False,Iris_accepted=False,visual_accepted=False,FPS_accepted=False,**refinement)
    except (ValueError,KeyError,TypeError) as error:
        return dict(status='INCONCLUSIVE',fixture_qualified=False,reason=str(error))


def _receipt(path,manifest):
    if _sha(path,manifest)!=RECEIPT_SHA:raise ValueError('frozen native probe receipt differs')
    receipt=json.loads(path.read_text())
    if receipt['schema']!='aqualumen-native-residual-sun-probe-receipt-v1' or receipt['status']!='CPU_READY_FROZEN':raise ValueError('probe receipt not frozen READY')
    for field in ('source','binary'):
        item=receipt[field]
        if _sha(PROJECT/item['path'],manifest)!=item['sha256']:raise ValueError('frozen native '+field+' hash differs')
    for name,digest in receipt['dependency_sha256'].items():
        if _sha(PROJECT/receipt['dependency_snapshot_directory']/name,manifest)!=digest:raise ValueError('frozen native inherited dependency differs')
    return dict(source=receipt['source'],binary=receipt['binary'],dependencies=receipt['dependency_sha256'],receipt_sha256=RECEIPT_SHA,
                provenance='Frozen build/export receipt plus root-owned execution; CPU auditor does not attest a live process executable.')


def _sources(run,recorded,manifest):
    original=(run/'source-original-expanded.fsh').read_text();baseline=(run/'guard-baseline-expanded.fsh').read_text()
    resolved=(run/'resolved-parent-expanded.fsh').read_text()
    if _sha(run/'guard-baseline-expanded.fsh',manifest)!=BASELINE_SHA or recorded['baselineSHA256']!=BASELINE_SHA:raise ValueError('physical baseline pin differs')
    if _sha(run/'native-atmosphere.glsl',manifest)!=ATMOSPHERE_SHA or recorded['atmosphereSHA256']!=ATMOSPHERE_SHA:raise ValueError('stock native atmosphere differs')
    if _sha(run/'source-original-expanded.fsh',manifest)!=recorded['activeExpandedSHA256']:raise ValueError('active FS digest differs')
    _sha(run/'resolved-parent-expanded.fsh',manifest);geometry=[run/f'geometry-stage{i}.glsl' for i in range(3)]
    geometry_digests={kind:_sha(path,manifest) for kind,path in zip((35633,36488,36487),geometry)}
    geometry_sizes={kind:len(path.read_bytes()) for kind,path in zip((35633,36488,36487),geometry)}
    recovered=original
    for tag in ('INCLUDE','RESTORE_ENV','CALL_BEGIN_ALIAS','CALL_END_ALIAS'):
        recovered,count=erase_blocks(recovered,f'// AQUALUMEN_SUN_{tag}_BEGIN\n',f'// AQUALUMEN_SUN_{tag}_END\n')
        if count!=1:raise ValueError('inner Sun marker missing/duplicated')
    if recovered!=baseline:raise ValueError('Sun erasure must recover guard FS exactly')
    for tag in ('HOOK','INCLUDE'):
        recovered,count=erase_blocks(recovered,f'// AQUALUMEN_RESIDUAL_{tag}_BEGIN\n',f'// AQUALUMEN_RESIDUAL_{tag}_END\n')
        if count!=1:raise ValueError('outer residual marker missing/duplicated')
    if recovered!=resolved:raise ValueError('outer erasure must recover resolved parent exactly')
    if '// ANGULAR_SOURCE_BEGIN' in original or original.count('    return sampleSky(lut,ray)+sunDisk(ray,sunDirection(),lut)+moonDisk(ray,sunDirection());\n')!=1:raise ValueError('native environment return was replaced')
    for case in recorded['cases']:
        directory=run/case['path'];pure=(directory/'pure-expanded.fsh').read_text();observer=(directory/'observer-expanded.fsh').read_text()
        for filename,field in (('pure-expanded.fsh','pureSourceSHA256'),('observer-expanded.fsh','observerSourceSHA256')):
            if _sha(directory/filename,manifest)!=case[field]:raise ValueError('compiled exported FS digest differs')
        recovered,count=erase_blocks(observer,'\n// RESIDUAL_NATIVE_STORE_BEGIN\n','// RESIDUAL_NATIVE_STORE_END\n')
        if count<1 or recovered!=pure:raise ValueError('observer STORE erasure not exact')
        if observer.count('    gl_FragData[1]=vec4(n,WNS_status.x);\n')!=1 or observer.count('    gl_FragData[7]=vec4(scatter,WNS_status.y);\n')!=1:raise ValueError('actual requested/application observer semantics differ')
        start=pure.index('// SUN_NATIVE_CONFIG_BEGIN\n');end=pure.index('// SUN_NATIVE_CONFIG_END\n',start)
        if re.findall(r'^#define NATIVE_SUN_ENABLED ([01])$',pure[start:end],re.M)!=[str(case['enabled'])]:raise ValueError('compiled native enabled setting differs')
        recovered,count=erase_blocks(pure,'// SUN_NATIVE_CONFIG_BEGIN\n','// SUN_NATIVE_CONFIG_END\n')
        if count!=1 or recovered!=original:raise ValueError('native config erasure not exact')
        if len(case['programs'])!=2 or len(case['queriedProgramSources'])!=2:raise ValueError('two actual linked/source-query programs required')
        for index,program in enumerate(case['programs']):
            if not program['linked'] or sorted(program['stage_types'])!=[35632,35633,36487,36488] or program['tess_layout']!=[3,4,514,2305,0]:raise ValueError('actual four-stage link/reflection differs')
            query=case['queriedProgramSources'][index]
            if query['program']!=case['program_ids'][index] or query['currentProgramBefore']!=query['currentProgramAfter']:raise ValueError('actual compiled source query state differs')
            stages=query['stages']
            if len(stages)!=4 or {s['type'] for s in stages}!={35632,35633,36487,36488}:raise ValueError('queried actual stage arity differs')
            fs_source=observer if index else pure;fs_digest=case['observerSourceSHA256'] if index else case['pureSourceSHA256']
            for stage in stages:
                digest=fs_digest if stage['type']==35632 else geometry_digests[stage['type']]
                size=len(fs_source.encode()) if stage['type']==35632 else geometry_sizes[stage['type']]
                if stage['sha256']!=digest or stage['bytes']!=size:raise ValueError('glGetShaderSource bytes/hash not matching actual exported source')
    return dict(native_atmosphere_and_source_unchanged=True,Sun_guard_and_outer_recovery_exact=True,
                config_observer_recovery_exact=True,actual_attached_four_stage_source_queries_match=True)


def _f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]


def _inputs(directory,case,manifest):
    path=directory/'actual-inputs.json';_sha(path,manifest);meta=json.loads(path.read_text())
    if meta['schema']!='aqualumen-native-residual-sun-inputs-v1' or not meta['stateRestored'] or meta['currentProgramBefore']!=meta['program'] or meta['currentProgramAfter']!=meta['program'] or meta['activeTextureBefore']!=meta['activeTextureAfter'] or meta['textureBindingBefore']!=meta['textureBindingAfter']:raise ValueError('actual input query/state differs')
    matrices=meta['matrices']
    if meta['fixedFunctionProjection']!=matrices['gbufferProjection'] or meta['fixedFunctionModelView']!=matrices['gbufferModelView']:raise ValueError('actual fixed/uniform matrices mismatch')
    focal=_f32(1/math.tan(case['aperture_degrees']*math.pi/360))
    if matrices['gbufferProjection'][0]!=focal or matrices['gbufferProjection'][5]!=focal or meta['aperture_degrees']!=case['aperture_degrees']:raise ValueError('fixed predeclared aperture differs')
    uniforms={item['name']:item for item in meta['uniforms']}
    for name,kind,values in (('sunPosition',35665,[0,0,-1]),('rainStrength',5126,[case['rainStrength']]),('viewWidth',5126,[257]),('viewHeight',5126,[257]),('isEyeInWater',5124,[1]),('aqualumenDimension',5124,[0])):
        item=uniforms[name]
        if item['type']!=kind or item['size']!=1 or item['values']!=values:raise ValueError('typed actual native uniform differs: '+name)
    raw_sun=uniforms['sunPosition']['values'];inverse=matrices['gbufferModelViewInverse']
    world=[math.fsum(inverse[c*4+r]*raw_sun[c] for c in range(3)) for r in range(3)];norm=math.sqrt(math.fsum(x*x for x in world))
    axis=[x/norm for x in world]
    if axis!=meta['sunDirectionDerivedFromActualUniforms'] or axis!=[0.,1.,0.]:raise ValueError('actual derived Sun axis differs')
    if len(meta['samplers'])!=8 or {x['unit'] for x in meta['samplers']}!=set(range(8)):raise ValueError('actual sampler arity differs')
    digests={};sampler_meta=[];cache=[.5,.625,.75] if case['positive_cache'] else [0.,0.,0.]
    names=('gtexture','colortex4','colortex6','depthtex1','shadowtex0','colortex8','aqualumenBathymetry','colortex7')
    dimensions=((1,1,34836),(257,257,34836),(64,32,34836),(257,257,36012),(1,1,36012),(1,1,34842),(64,64,34836),(64,32,34836))
    for sampler in meta['samplers']:
        unit=sampler['unit'];components=1 if unit in (3,4) else 4
        if (sampler['width'],sampler['height'],sampler['internalFormat'])!=dimensions[unit] or sampler['name']!=names[unit] or sampler['components']!=components or sampler['uniformType']!=(35682 if unit==4 else 35678) or sampler['uniformSize']!=1 or sampler['uniformUnit']!=unit or sampler['sampler']!=0 or sampler['minFilter']!=9728 or sampler['magFilter']!=9728 or sampler['wrapS']!=33071 or sampler['wrapT']!=33071 or sampler['compareMode']!=(34894 if unit==4 else 0):raise ValueError('actual sampler type/storage/filter differs')
        values=_read(directory/sampler['file'],sampler['width']*sampler['height']*components,manifest)
        digests[unit]=manifest[str(directory/sampler['file'])];sampler_meta.append({k:v for k,v in sampler.items() if k!='texture'})
        if unit in (2,7):
            for offset in range(0,len(values),4):
                expected=cache if unit==2 and offset==31*64*4 else [0.,0.,0.]
                if list(values[offset:offset+3])!=expected or values[offset+3]!=1:raise ValueError('actual native cache/sky row differs')
        if unit==3 and any(value!=1 for value in values):raise ValueError('opaque depth is not open sky1')
    if cache!=meta['solarCacheRGB'] or meta['SOLAR']!=[18,17.6,17] or meta['solarRadius']!=.00465 or meta['weatherFactor']!=1-.85*case['rainStrength']:raise ValueError('actual source cache/weather/units differ')
    for target in meta['targets']:
        if (target['width'],target['height'],target['internalFormat'])!=(257,257,34836):raise ValueError('RGBA32F target differs')
    if len(meta['targets'])!=8 or {t['slot'] for t in meta['targets']}!=set(range(8)) or (meta['depth']['width'],meta['depth']['height'],meta['depth']['internalFormat'])!=(257,257,36012):raise ValueError('eight-MRT/depth storage differs')
    vertices=_read(directory/'uploaded-open-water-vertices.f32',90,manifest)
    if any(vertices[p+12]!=0 or vertices[p+13]!=1 or vertices[p+14]!=10000 for p in range(0,90,15)):raise ValueError('actual immutable VBO lightmap/material differs')
    for name in ('uploaded-water-vertices.f32','actual-bathymetry.rgba32f'):_sha(directory/name,manifest)
    stable=dict(matrices=matrices,samplers=sampler_meta,non_solar_inputs={k:v for k,v in digests.items() if k!=2},
                open_vbo=manifest[str(directory/'uploaded-open-water-vertices.f32')],
                vbo=manifest[str(directory/'uploaded-water-vertices.f32')],bathymetry=manifest[str(directory/'actual-bathymetry.rgba32f')])
    return dict(stable=stable,axis=axis,beam=solar_beam(cache,case['rainStrength']),cache=cache,
                source_uniforms=uniforms,sky_qualified=True,sky_weight_proof='Formula1: actual VBO lightmap.y1, pinned smoothstep saturation .85, actual open depth1, legacy noopaque; NOT direct light-node readback.')


def _point(frame,pixel,inputs,mode):
    slots=frame['observer']['slots'];n,c,a,status,v,flags,scatter=(_pixel(slots[x],pixel) for x in (1,2,3,4,5,6,7))
    return dict(C0=_pixel(frame[mode]['slots'][0],pixel)[:3],scatter=scatter[:3],mean_normal=n[:3],covariance=c[:3],
                view_to_eye=v[:3],coefficients=a,WR_status=status,flags=flags,eligible=v[3],requested=n[3],applied=scatter[3],
                footprint=c[3],sky_qualified=inputs['sky_qualified'])


def audit(run,receipt_path):
    manifest={}
    for filename,pin in (('water_residual_sun_integral.py',SUN_MATH_SHA),('water_residual_light_audit.py',IO_SHA)):
        if _sha(Path(__file__).with_name(filename),manifest)!=pin:raise ValueError('frozen math/IO dependency differs')
    receipt=_receipt(receipt_path,manifest);_sha(run/'result.json',manifest);recorded=json.loads((run/'result.json').read_text())
    if recorded['schema']!='aqualumen-native-residual-sun-v1' or recorded['size']!=257 or recorded['phase_seconds']!=120 or recorded['source_kind']!=0 or recorded['case_count']!=16:raise ValueError('export schema/phase/kind/count differs')
    labels={f'fov{fov}-rain{rain}-cache{cache}-enabled{enabled}' for fov in (2,1) for rain in ('0','0_5') for cache in ('positive','zero') for enabled in (0,1)}
    if len(recorded['cases'])!=16 or {c['path'] for c in recorded['cases']}!=labels:raise ValueError('16 fixed case matrix differs')
    policy=dict(passive_C0_absolute=5e-4,passive_C0_relative=2e-4,passive_depth_absolute=2e-6,coefficient_absolute=2e-5,
                common_xyz_absolute_relative=EPS8,ROI_center=[128,128],ROI_integer_radius=40)
    if recorded['policy']!=policy:raise ValueError('predeclared telemetry policy differs')
    sources=_sources(run,recorded,manifest);frames={};inputs={};telemetry=[];case_domains=[];bases={};input_bases={}
    for case in recorded['cases']:
        name=case['path'];directory=run/name
        if case['aperture_degrees'] not in (2,1) or case['rainStrength'] not in (0,.5) or case['enabled'] not in (0,1):raise ValueError('case fixture value differs')
        expected=f"fov{case['aperture_degrees']}-rain{'0' if case['rainStrength']==0 else '0_5'}-cache{'positive' if case['positive_cache'] else 'zero'}-enabled{case['enabled']}"
        if expected!=name:raise ValueError('case path differs from actual setting')
        frame={}
        for mode in ('pure','observer'):
            slots={i:_read(directory/f'{mode}-slot{i}.rgba32f',257*257*4,manifest) for i in range(8)}
            depth=_read(directory/f'{mode}-depth.f32',257*257,manifest)
            for i in range(8):
                repeat=_read(directory/f'{mode}-repeat-slot{i}.rgba32f',257*257*4,manifest)
                telemetry.append(dict(case=name,comparison=f'{mode}-slot{i}-repeat',**_compare(slots[i],repeat)))
            repeat=_read(directory/f'{mode}-repeat-depth.f32',257*257,manifest)
            telemetry.append(dict(case=name,comparison=f'{mode}-depth-repeat',**_compare(depth,repeat)))
            frame[mode]=dict(slots=slots,depth=depth)
        telemetry.append(dict(case=name,comparison='observer-C0-passive',**_compare(frame['pure']['slots'][0],frame['observer']['slots'][0],5e-4,2e-4)))
        telemetry.append(dict(case=name,comparison='observer-depth-passive',**_compare(frame['pure']['depth'],frame['observer']['depth'],2e-6)))
        actual=_inputs(directory,case,manifest);fov=case['aperture_degrees'];slots=frame['observer']['slots']
        if fov not in bases:bases[fov]=frame['observer'];input_bases[fov]=actual['stable']
        else:
            if input_bases[fov]!=actual['stable']:raise ValueError('non-Sun input/matrix/VBO/map changed within fixed aperture')
            base=bases[fov]
            for i in (1,5):telemetry.append(dict(case=name,comparison=f'common-slot{i}-xyz',**_compare([v for p,v in enumerate(base['slots'][i]) if p%4!=3],[v for p,v in enumerate(slots[i]) if p%4!=3],EPS8,EPS8)))
            telemetry.append(dict(case=name,comparison='common-eligibility-exact',**_compare(base['slots'][5][3::4],slots[5][3::4])))
            for i in (2,6):telemetry.append(dict(case=name,comparison=f'common-slot{i}-exact',**_compare(base['slots'][i],slots[i])))
            for i in (3,4):telemetry.append(dict(case=name,comparison=f'common-WR-slot{i}',**_compare(base['slots'][i],slots[i],2e-5)))
            telemetry.append(dict(case=name,comparison='common-depth-exact',**_compare(base['depth'],frame['observer']['depth'])))
        domain=requested=applied=0;expected_apply=int(case['positive_cache'] and case['enabled'])
        for pixel in ROI:
            point=_point(frame,pixel,actual,'observer');domain+=_domain(point) and point['mean_normal'][1]<-.5 and point['view_to_eye'][1]<0 and point['footprint']==_f32(.035)
            requested+=point['requested']==case['enabled'];applied+=point['applied']==expected_apply
        case_domains.append(dict(case=name,legacy_qualified_pixels=domain,requested_matching_pixels=requested,
                                 expected_application=expected_apply,application_matching_pixels=applied,ROI_points=len(ROI)))
        frames[name]=frame;inputs[name]=actual
    for fov in (2,1):
        for weather in ('0','0_5'):
            a=f'fov{fov}-rain{weather}-cachezero-enabled0';b=f'fov{fov}-rain{weather}-cachezero-enabled1'
            for mode in ('pure','observer'):telemetry.append(dict(case=b,comparison=f'zero-cache-{mode}-inactive-legacy',**_compare(frames[a][mode]['slots'][0],frames[b][mode]['slots'][0],EPS8,EPS8)))
            telemetry.append(dict(case=b,comparison='zero-scatter-equality',**_compare([v for p,v in enumerate(frames[a]['observer']['slots'][7]) if p%4!=3],[v for p,v in enumerate(frames[b]['observer']['slots'][7]) if p%4!=3],EPS8,EPS8)))
    pair_reports=[];fixed=[];domain_failures=[];maximum=0.;candidate_passes=candidate_count=0;refinement_passes=refinement_count=0
    selected_finite_passes=selected_actual_passes=selected_actual_count=0
    for case in recorded['cases']:
        if not case['positive_cache']:continue
        name=case['path'];zero_name=name.replace('cachepositive','cachezero');frame=frames[name];zero=frames[zero_name];actual_inputs=inputs[name]
        for mode in ('pure','observer'):
            accepted_count=qualified_count=negative_count=0;points=[]
            for pixel in ROI:
                positive=_point(frame,pixel,actual_inputs,mode);negative=_point(zero,pixel,inputs[zero_name],mode)
                report=audit_sample(positive,negative,actual_inputs['axis'],actual_inputs['beam'],case['enabled'],refine=pixel in FIXED);report.update(pixel=pixel)
                qualified_count+=report.get('fixture_qualified',False);accepted_count+=report['status']=='PASS';negative_count+=bool(report.get('centralsharp_negative_control'))
                if report['status']=='INCONCLUSIVE':domain_failures.append(dict(case=name,mode=mode,pixel=pixel,reason=report.get('reason')))
                if case['enabled']:
                    candidate_count+=1;candidate_passes+=report['status']=='PASS'
                    if report.get('absolute_errors'):maximum=max(maximum,*report['absolute_errors'])
                if pixel in FIXED:
                    refinement_count+=1;refinement_passes+=bool(report.get('convergence_accepted'))
                    selected_finite_passes+=bool(report.get('selected_finite_to_refined_accepted'))
                    if case['enabled']:
                        selected_actual_count+=1;selected_actual_passes+=bool(report.get('selected_actual_to_refined_accepted'))
                    fixed.append(dict(case=name,mode=mode,pixel=pixel,actual_fixture=positive,finite_cap=report))
                points.append(report)
            pair_reports.append(dict(case=name,mode=mode,paired_zero=zero_name,qualified_pixels=qualified_count,
                                     candidate_accepted_pixels=accepted_count,centralsharp_negative_control_pixels=negative_count,points=points))
    qualified=(recorded['status']=='COMPLETE' and recorded['exportComplete'] and all(t['accepted'] for t in telemetry)
               and all(c['legacy_qualified_pixels']==len(ROI) and c['requested_matching_pixels']==len(ROI) for c in case_domains) and not domain_failures)
    accepted=(qualified and all(c['application_matching_pixels']==len(ROI) for c in case_domains)
        and candidate_passes==candidate_count and refinement_passes==refinement_count
        and selected_finite_passes==refinement_count and selected_actual_passes==selected_actual_count)
    return dict(schema='aqualumen-saved-native-sun-independent-cpu-audit-v1',run=str(run.resolve()),audit_status='INCONCLUSIVE' if not qualified else 'PASS' if accepted else 'RED',
        recorded_export_status=recorded['status'],fixture_qualified=qualified,probe_receipt=receipt,sources=sources,
        actual_cases=case_domains,telemetry=telemetry,pairs=pair_reports,fixed_six=fixed,domain_failures=domain_failures,
        candidate_numeric_and_application_accepted=candidate_passes,candidate_points=candidate_count,
        selected_refinement_accepted=refinement_passes,selected_refinement_count=refinement_count,maximum_candidate_C0_error=maximum,
        selected_finite_to_refined_accepted=selected_finite_passes,selected_finite_to_refined_count=refinement_count,
        selected_candidate_actual_to_refined_accepted=selected_actual_passes,selected_candidate_actual_to_refined_count=selected_actual_count,
        main_absolute=ABSOLUTE,main_relative_to_reference=RELATIVE,refinement_absolute=2e-8,refinement_relative=2e-6,
        frozen_sun_math_sha256=SUN_MATH_SHA,frozen_IO_sha256=IO_SHA,raw_source_input_sha256_manifest=manifest,
        all_ROI_finite_rule_checked=True,all_ROI_convergence_accepted=False,selected_convergence_only=True,
        skyWeight_scope='Formula-derived1 from actual VBO/open depth/legacy admission; no per-node weight readback.',
        native_pixel_filter_equivalence_accepted=False,native_filtered_bug_proven=False,physical_accepted=False,energy_accepted=False,
        Iris_accepted=False,visual_accepted=False,motion_accepted=False,FPS_accepted=False,shipping_accepted=False,
        scope='Saved central physical sharp-Sun response only: original-main actual C0/scatter and raw n/v/C/cache/Sun/rain, finite whole5025 per positive pair and selected six refinements. COMPLETE export distinct from this CPU result; legacy mismatch is only centralsharpnegativecontrol, not an exact native filtered-Sun bug. No live GL/app, arbitrary receiver/critical/global physical model, pixel-AA equivalence, Iris, motion/FPS or adoption.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--probe-receipt',type=Path,required=True);parser.add_argument('--expect',choices=('RED','PASS','INCONCLUSIVE'),required=True);args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink():parser.error('NEW output required')
    try:report=audit(args.run,args.probe_receipt)
    except (OSError,ValueError,KeyError,TypeError,ZeroDivisionError) as error:report=dict(schema='aqualumen-saved-native-sun-independent-cpu-audit-v1',audit_status='INCONCLUSIVE',fixture_qualified=False,error=str(error))
    consistent=report['audit_status']==args.expect;report.update(expected_status=args.expect,audit_consistent=consistent)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    print(('CONSISTENT' if consistent else 'MISMATCH')+' saved centralsharp '+report['audit_status']+'; '+str(args.output))
    return 0 if consistent else 2


if __name__=='__main__':raise SystemExit(main())
