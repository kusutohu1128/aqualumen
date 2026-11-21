"""CPU saved-data crosscheck. No GL, game, pack or frozen-file mutations.

Separate implementation of the boundary driver's declared local oracles. An
audit that consistently reproduces native RED is successful evidence retention,
not model acceptance. Coefficients are not physical energy/reciprocity proof.
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

SIZE = 257
EPS8 = 8 * 2**-23
C0_SCALE = .25
COEFF_TOL = 2e-5
SCATTER_TOL = 2e-5
PASSIVE_ABS, PASSIVE_REL, DEPTH_TOL = 5e-4, 2e-4, 2e-6
TAGS = (.25, .125, .0625)
CASES = ('zero-residual-same-mean', 'zero-wave-air-negative',
         'zero-wave-unknown-negative', 'nonzero-all-TIR',
         'invalid-covariance-input-contract')
CENTRAL = ((104,140), (152,116), (112,104), (144,152), (116,136), (136,108), (148,132))
RIGHT = ((237,128), (235,128), (239,128), (237,126), (237,130))


def f32(x: float) -> float:
    return struct.unpack('<f', struct.pack('<f', x))[0]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def remove(source: str, begin: str, end: str, unique: bool = True) -> str:
    if unique and (source.count(begin) != 1 or source.count(end) != 1):
        raise ValueError('missing/ambiguous source block')
    while begin in source:
        start = source.index(begin)
        finish = source.index(end, start) + len(end)
        source = source[:start] + source[finish:]
    return source


def without_hook(source: str) -> str:
    for role in ('HOOK', 'INCLUDE'):
        source = remove(source, f'// AQUALUMEN_RESIDUAL_{role}_BEGIN\n',
                        f'// AQUALUMEN_RESIDUAL_{role}_END\n')
    return source


def without_store(source: str) -> str:
    return remove(source, '\n// RESIDUAL_NATIVE_STORE_BEGIN\n',
                  '// RESIDUAL_NATIVE_STORE_END\n', False)


def comparison(a, b, absolute: float, relative: float = 0.0) -> dict:
    if len(a) != len(b) or not a:
        raise ValueError('comparison has missing/unequal samples')
    maximum = max(abs(float(x)-float(y)) for x,y in zip(a,b))
    failures = sum(abs(float(x)-float(y)) > absolute + relative*max(abs(float(x)),abs(float(y)))
                   for x,y in zip(a,b))
    return dict(samples=len(a), maximum_absolute=maximum, failures=failures,
                absolute=absolute, relative=relative, accepted=failures==0)


def expected_vertices(span: float, surface: float, opened: bool) -> bytes:
    positions = ((-span,-span),(-span,span),(span,span),(-span,-span),(span,span),(span,-span))
    values=[]
    for x,z in positions:
        values.extend((x,surface,z,0,1,0,.7,.8,.75,1,.5,.5,
                       0 if opened else .2,1 if opened else .8,10000))
    return struct.pack('<90f',*values)


def audit(run: Path) -> dict:
    if sys.byteorder != 'little':
        raise ValueError('native saved float bytes require explicit little-endian host')
    recorded=json.loads((run/'result.json').read_text())
    if recorded['size'] != SIZE or recorded['quadrature_order'] != 3:
        raise ValueError('wrong saved driver size/order')
    if [c['name'] for c in recorded['cases']] != list(CASES):
        raise ValueError('missing/reordered boundary fixtures')
    if recorded['policy'] != dict(arithmetic_absolute=EPS8, arithmetic_relative=EPS8,
        C0_reference_scale=C0_SCALE, coefficient_absolute=COEFF_TOL,
        scatter_C0_vector_absolute=SCATTER_TOL, passive_C0_absolute=PASSIVE_ABS,
        passive_C0_relative=PASSIVE_REL, passive_depth_absolute=DEPTH_TOL):
        # JSON numbers are printed with twelve significant digits, not all
        # exact binary64 digits. Check the declared serialization precision.
        expected=dict(arithmetic_absolute=EPS8, arithmetic_relative=EPS8,
            C0_reference_scale=C0_SCALE, coefficient_absolute=COEFF_TOL,
            scatter_C0_vector_absolute=SCATTER_TOL, passive_C0_absolute=PASSIVE_ABS,
            passive_C0_relative=PASSIVE_REL, passive_depth_absolute=DEPTH_TOL)
        if set(recorded['policy']) != set(expected) or any(not math.isclose(recorded['policy'][k],v,rel_tol=5e-12,abs_tol=0) for k,v in expected.items()):
            raise ValueError('saved policy differs from independently declared driver policy')
    manifests=[]; outputs=[]; all_qualified=True; all_pass=True; record_matches=True; tcs_hashes=[]
    for kind,name in enumerate(CASES):
        directory=run/name; cache={}
        def raw(file: str, count: int):
            if file not in cache:
                data=(directory/file).read_bytes()
                if len(data) != count*4:
                    raise ValueError(f'{name}/{file}: unexpected byte size')
                values=array.array('f');values.frombytes(data)
                if not all(math.isfinite(x) for x in values):
                    raise ValueError(f'{name}/{file}: nonfinite saved output')
                manifests.append(dict(path=f'{name}/{file}',bytes=len(data),sha256=digest(data),finite=True))
                cache[file]=values
            return cache[file]
        def image(label,slot): return raw(f'{label}-slot{slot}.rgba32f',SIZE*SIZE*4)
        def depth(label): return raw(f'{label}-depth.f32',SIZE*SIZE)
        source_data={p.name:p.read_bytes() for p in directory.glob('*.glsl')}
        source_data.update({p.name:p.read_bytes() for p in directory.glob('*.fsh')})
        for file,data in sorted(source_data.items()):manifests.append(dict(path=f'{name}/{file}',bytes=len(data),sha256=digest(data)))
        active=source_data['active-expanded.fsh'].decode(); inactive=source_data['inactive-expanded.fsh'].decode()
        source_checks=dict(disabled_recovery=without_hook(active)==inactive,
            active_observer_recovery=without_store(source_data['active-observed.fsh'].decode())==active,
            inactive_observer_recovery=without_store(source_data['inactive-observed.fsh'].decode())==inactive,
            phase120=all('#define frameTimeCounter 120.0\n' in source_data[file].decode() for file in ('geometry-stage0.glsl','geometry-stage2.glsl','active-expanded.fsh')))
        tcs=source_data['geometry-stage1.glsl'];tcs_hashes.append(digest(tcs));source_checks['TCS_inapplicable']=not any(token in tcs for token in (b'WAVE_HEIGHT',b'waveState',b'waveSurface',b'localWaveState'))
        if kind<4:
            desired=0 if kind<3 else .06
            source_checks['public_height']=all(len(re.findall(r'#define WAVE_HEIGHT ([^ \n]+)',source_data[file].decode()))==1 and float(re.findall(r'#define WAVE_HEIGHT ([^ \n]+)',source_data[file].decode())[0])==desired for file in ('geometry-stage0.glsl','geometry-stage2.glsl','active-expanded.fsh','inactive-expanded.fsh'))
        else: source_checks['invalid_literal_only']=active.count('WR_covariance=vec3(1e-8,2e-8,1e-8);')==1 and 'WR_covariance=waveResidualCovariance(effectiveFootprint,columnDepth);' not in active
        source_checks['four_stage_reflection']=all(p['linked'] and p['stage_types']==[35632,35633,36487,36488] and p['tess_layout']==[3,4,514,2305,0] for p in recorded['cases'][kind]['programs']) and len(recorded['cases'][kind]['programs'])==4
        # Actual immutable upload readbacks, including initial ordinary quad
        # and the subsequent explicitly open/full-sky quad used for drawing.
        surface=-3.25 if kind==1 else 3.25
        input_checks={}
        for file,span,opened in (('uploaded-water-vertices.f32',.9,False),('uploaded-open-water-vertices.f32',.9,True)):
            raw(file,90);input_checks[file]=(directory/file).read_bytes()==expected_vertices(span,surface,opened)
        if kind==3:
            raw('uploaded-wide-water-vertices.f32',90);input_checks['wide_vertices']=(directory/'uploaded-wide-water-vertices.f32').read_bytes()==expected_vertices(12,surface,True)
        expected_map=struct.pack('<4f',4,surface,0 if kind==2 else 1,0)*(64*64)
        raw('actual-bathymetry.rgba32f',64*64*4);input_checks['map_exact']=(directory/'actual-bathymetry.rgba32f').read_bytes()==expected_map
        expected_sky=b''.join(struct.pack('<4f',*(TAGS if row<31 else (0,0,0)),1) for row in range(32) for x in range(64))
        for file in ('actual-sky.rgba32f','actual-clear-sky.rgba32f'):
            raw(file,64*32*4);input_checks[file]=(directory/file).read_bytes()==expected_sky
        projection=raw('actual-projection.f32',16);focal=f32(1/math.tan(math.radians(70 if kind==3 else 30)));near=f32(.01);far=f32(128);denom=f32(far-near);a=f32(-f32(far+near)/denom);b=f32(f32(f32(-2*far)*near)/denom)
        input_checks['projection_exact']=list(projection)==[focal,0,0,0,0,focal,0,0,0,0,a,-1,0,0,b,0]
        comparisons={}
        def compare(label,a,b,absolute,relative=0):
            comparisons[label]=comparison(a,b,absolute,relative)
        for role in ('inactive','active'):
            compare(role+'-pure-C0-repeat',image(role+'-pure',0),image(role+'-pure-repeat',0),0)
            compare(role+'-pure-depth-repeat',depth(role+'-pure'),depth(role+'-pure-repeat'),0)
            compare(role+'-passive-C0',image(role+'-pure',0),image(role+'-observer',0),PASSIVE_ABS,PASSIVE_REL)
            compare(role+'-passive-depth',depth(role+'-pure'),depth(role+'-observer'),DEPTH_TOL)
            for slot in range(8):compare(role+f'-observer-slot{slot}-repeat',image(role+'-observer',slot),image(role+'-observer-repeat',slot),0)
            compare(role+'-observer-depth-repeat',depth(role+'-observer'),depth(role+'-observer-repeat'),0)
        compare('cross-depth-exact',depth('inactive-observer'),depth('active-observer'),0)
        compare('cross-flags-exact',image('inactive-observer',6),image('active-observer',6),0)
        if kind!=3:
            compare('matching-parent-C0-local-arithmetic',image('inactive-observer',0),image('active-observer',0),EPS8*C0_SCALE,EPS8)
            compare('matching-parent-normal-local-arithmetic',image('inactive-observer',1),image('active-observer',1),EPS8,EPS8)
        samples=[]
        for pixel in (RIGHT if kind==3 else CENTRAL):
            index=(pixel[1]*SIZE+pixel[0])*4
            fields={slot:list(image('active-observer',slot)[index:index+4]) for slot in range(8)}
            qualified=all(image(role+'-observer',6)[index:index+4]==array.array('f',(float(kind!=2),1,float(kind!=1),1)) and image(role+'-observer',1)[index+3]==1 and image(role+'-observer',2)[index+3]>=f32(.035) for role in ('inactive','active'))
            xx,xz,zz,_=fields[2];mass,R,T,TIR=fields[3];valid,applied,facing,violations=fields[4];Tsky,Rwater,Topaque,Ropaque=fields[5];cov_det=xx*zz-xz*xz;trace=xx+zz;sample_pass=True;scatter_error=0
            if kind==0:
                qualified &= fields[7][3]==1
                sample_pass=xx==xz==zz==0 and valid==applied==1 and facing>0 and violations==0 and abs(mass-1)<=COEFF_TOL and abs(R+T-mass)<=COEFF_TOL and R>=0 and T>=0 and TIR==0 and abs(Tsky-T)<=COEFF_TOL and abs(Rwater-R)<=COEFF_TOL and Topaque==Ropaque==0
            elif kind in (1,2):sample_pass=applied==0
            elif kind==3:
                qualified &= fields[7][3]==1 and trace>0 and xx>=0 and zz>=0 and cov_det>=-1e-7 and valid==applied==1 and facing>0 and violations==0 and abs(TIR-1)<=COEFF_TOL and T==0
                scatter_error=math.sqrt(sum((fields[0][c]-fields[7][c])**2 for c in range(3)))
                sample_pass=abs(mass-1)<=COEFF_TOL and abs(R-1)<=COEFF_TOL and T==0 and Tsky==0 and abs(Rwater-1)<=COEFF_TOL and Topaque==Ropaque==0 and scatter_error<=SCATTER_TOL
            else:
                qualified &= fields[7][3]==1 and (xx,xz,zz)==(f32(1e-8),f32(2e-8),f32(1e-8)) and cov_det<0
                sample_pass=valid==applied==0
            samples.append(dict(pixel=pixel,fixture_qualified=bool(qualified),oracle_accepted=bool(sample_pass),covariance=fields[2][:3],covariance_determinant=cov_det,coefficients=fields[3],status=fields[4],source_masses=fields[5],scatter_C0_vector_error=scatter_error))
        case_qualified=all(s['fixture_qualified'] for s in samples);case_pass=all(c['accepted'] for c in comparisons.values()) and all(s['oracle_accepted'] for s in samples)
        native=recorded['cases'][kind]
        record_matches &= case_qualified==native['fixture_qualified'] and [s['oracle_accepted'] for s in samples]==[s['accepted'] for s in native['samples']] and all(comparisons[c['name']]['accepted']==c['accepted'] for c in native['comparisons'])
        all_qualified &= case_qualified;all_pass &= case_pass
        outputs.append(dict(name=name,source_checks=source_checks,input_checks=input_checks,fixture_qualified=case_qualified,oracle_accepted=case_pass,comparisons=comparisons,samples=samples))
    tcs_identical=len(set(tcs_hashes))==1
    checks=all(all(c['source_checks'].values()) and all(c['input_checks'].values()) for c in outputs) and tcs_identical
    computed_accepted=all_qualified and all_pass
    record_matches &= recorded['all_fixtures_qualified']==all_qualified and recorded['accepted']==computed_accepted
    return dict(schema='aqualumen-saved-boundary-cpu-audit-v1',run=str(run),native_result_sha256=digest((run/'result.json').read_bytes()),native_record_matches_raw_oracles=bool(record_matches),source_and_input_checks=checks,TCS_sha256=tcs_hashes[0],TCS_identical_across_cases=tcs_identical,all_fixtures_qualified=bool(all_qualified),oracle_outcome=('INCONCLUSIVE' if not all_qualified else 'PASS' if all_pass else 'RED'),audit_consistent=bool(checks and record_matches),cases=outputs,manifest=manifests,scope='CPU saved-array/source crosscheck, not a GL rerun. Expected RED may be correctly retained. Local coefficient/constant-source identities are not calibrated radiance/flux, reciprocity, tails or quadrature-order convergence. Independent arithmetic implementation by the same harness author; not a third-party review.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--expect',choices=('PASS','RED','INCONCLUSIVE'));args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink():parser.error('NEW output path required')
    report=audit(args.run.resolve())
    if args.expect:report['expected_outcome_matches']=report['oracle_outcome']==args.expect
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as handle:json.dump(report,handle,indent=2,allow_nan=False);handle.write('\n')
    passed=report['audit_consistent'] and report.get('expected_outcome_matches',True)
    print(('PASS' if passed else 'FAIL')+' saved CPU audit; native oracle='+report['oracle_outcome']+'; '+str(args.output))
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
