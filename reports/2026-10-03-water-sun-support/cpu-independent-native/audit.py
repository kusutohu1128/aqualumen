"""Read-only saved support-policy replay. Never executes GL or Minecraft."""
from array import array
import ast
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from water_residual_sun_iris_runtime import zip_files,json_file
from water_residual_sun_reason_pack import STORE,strip_reason_blocks
from water_sun_support_pack import (MANIFEST,HELPER,WATER,NODE,NODE_SHA,NODE_EXTENSION_GUARD,
    INPUT_STORE,SUPPORT_STORE,CERTIFICATE,CERTIFICATE_SHA,PARENT_HELPERS,PARENT_WATER,
    BODIES,QUALIFICATION,recover_helper,recover_water)
from water_snell_main_pack import INPUT_BODIES
from water_sun_support_runtime import analyze_reason_point,decode_counts

SHARED=ROOT/'reports/2026-10-03-water-residual-sun-reasons/cpu-independent-native/audit.py'
SHARED_SHA='b804d78c495a73c347379cbcc16a802b97941b8ad43cfc9943c4bac1e0adb362'
PACKS=ROOT/'reports/2026-10-03-water-sun-support/cpu-pack'
PACK_PINS={
    'reject-reasons':'681bd672fde78d6e7e9a89a873c2b29a3d0b64d81f473c245960bbc4cccbe0ff',
    'reject-inputs':'32589948e7b0773b857801d12a55730fb9135aff26e0f40775a33f9bc1bf757e',
    'zero-reasons':'7f15dbc05a68cc80be3ae0f6ea66ec5ae3c3f42785eb753d4e603f7089ba9048',
    'zero-inputs':'5a1dd986f95961c96d9175301b8ce432d65cde792e89f99e01935234abde70b0'}
SOURCE_SHA='f4c1b8b3d2dd9e7085bddd57ee1b9e848d2979558300d732e77d928752800f02'
BINARY_SHA='eb27deea1dc2aea3ddda1ea458bf31f2326e0e196316d8a8a0c10c549304ca52'
RUNTIME_SHA='f7d37236671e4333ac12312dae32cd6cdec39023dee01622f12258d7bc680d31'
BUILDER_SHA='c229872b2906003599181800ab6cf5ed8a61685a675ebb04fa06b9e3bfd81abb'
SIZE=257;PIXELS=SIZE*SIZE;MODES=('reject','zero');ROLES=('physical','reasons','inputs')
CASES=('central2-cachezero-guard0','central2-cachezero-guard1',
       'central2-cachepositive-guard0','central2-cachepositive-guard1',
       'wide60-cachepositive-guard1','wide90-cachepositive-guard1')
EPS8=8*2**-23
POLICY=dict(observer_C0_absolute=.0005,observer_C0_relative=.0002,depth_absolute=2e-6,
    cross_variant_C0_absolute=2e-6,cross_variant_C0_relative=.0002,
    cross_variant_mean_view_XYZ_absolute_relative=EPS8,repeat_absolute=0,
    reason_TES_absolute=0,ROI_center=[128,128],ROI_radius=40)


def sha(value): return hashlib.sha256(value).hexdigest()


def require(okay,message):
    if not okay: raise ValueError(message)


def utilities():
    """Load only pinned pure read/compare helpers, never old pack_policy/audit."""
    raw=SHARED.read_bytes();require(sha(raw)==SHARED_SHA,'Frozen read-only utilities changed')
    names={'typed','expand','read_bytes','floats','f32','stage','compare','input_snapshot'}
    tree=ast.parse(raw);functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    require({n.name for n in functions}==names,'Pinned read-only utility names differ')
    namespace=dict(array=array,hashlib=hashlib,json=json,math=math,Path=Path,re=re,
        struct=struct,sys=sys,json_file=json_file,require=require,sha=sha)
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(SHARED),'exec'),namespace)
    return SimpleNamespace(**{name:namespace[name] for name in names})


shared=utilities()


def erase(source,begin,end):
    require(source.count(begin)==source.count(end)==1,'Unique source tag required')
    start=source.index(begin);stop=source.index(end,start)+len(end)
    return source[:start]+source[stop:]


def restore_support(source):
    for name in BODIES:
        begin='// AQUALUMEN_SUN_SUPPORT_BEGIN:'+name+'\n';end='// AQUALUMEN_SUN_SUPPORT_END:'+name+'\n'
        position=source.index(begin);source=erase(source,begin,end)
        if name=='QUALIFICATION': source=source[:position]+QUALIFICATION+source[position:]
    require('AQUALUMEN_SUN_SUPPORT_' not in source,'Unknown support source tag')
    return source


def expected_sources():
    """Public exact source contract from four fixed NEW policy packs."""
    expected={};pins={}
    for mode in MODES:
        for role in ROLES[1:]:
            key=mode+'-'+role;pack=PACKS/('Aqualumen-ShoreProbe-world-sun-support-'+key+'-v1.zip')
            require(sha(pack.read_bytes())==PACK_PINS[key],'Frozen support ZIP differs')
            pins[pack.name]=PACK_PINS[key];files=zip_files(pack);meta=json.loads(files[MANIFEST])
            require((meta['schema'],meta['mode'],meta['observe'])==('aqualumen-water-sun-support-v1',mode,role),
                'Authoritative policy role differs')
            require(meta['shipping_accepted'] is False and meta['physical_accepted'] is False,
                'CPU packet overclaims model acceptance')
            require(recover_helper(files[HELPER])==files['PARENT-SUN-SUPPORT-helper.glsl']
                and recover_water(files[WATER],role)==files['PARENT-SUN-SUPPORT-water.fsh'],
                'Same-role parent source recovery differs')
            require(sha(files['PARENT-SUN-SUPPORT-helper.glsl'])==PARENT_HELPERS[role]
                and sha(files['PARENT-SUN-SUPPORT-water.fsh'])==PARENT_WATER[role],'Stable source pins')
            original=files['PARENT-SNELL-MAIN-node.glsl']
            require(sha(original)==NODE_SHA and original.count(NODE_EXTENSION_GUARD.encode())==1
                and files[NODE]==original.replace(NODE_EXTENSION_GUARD.encode(),b'',1),'Adapted inverse module exact')
            if mode=='zero': require(sha(files[CERTIFICATE])==CERTIFICATE_SHA,'Literal Q24 certificate differs')
            expanded=shared.expand(files,WATER);expected[key+'-expanded.fsh']=expanded.encode()
            store=SUPPORT_STORE if mode=='zero' and role=='reasons' else INPUT_STORE if role=='inputs' else STORE
            require(expanded.count(store)==1,'Actual observer STORE differs')
            physical=expanded.replace(store,'')
            if role=='inputs':
                for name in INPUT_BODIES:
                    physical=erase(physical,'// AQUALUMEN_SNELL_INPUT_BEGIN:'+name+'\n',
                        '// AQUALUMEN_SNELL_INPUT_END:'+name+'\n')
            physical=strip_reason_blocks(physical);name=mode+'-physical-expanded.fsh'
            require(name not in expected or expected[name]==physical.encode(),'Physical source differs across observer roles')
            expected[name]=physical.encode();expected[key+'-metadata.json']=files[MANIFEST]
            for index,stage in enumerate(('vsh','tcs','tes')):
                name='geometry-stage'+str(index)+'.glsl';value=shared.expand(files,'shaders/gbuffers_water.'+stage).encode()
                require(name not in expected or expected[name]==value,'Geometry source changed')
                expected[name]=value
    require(restore_support(expected['zero-physical-expanded.fsh'].decode()).encode()==expected['reject-physical-expanded.fsh'],
        'Expanded policy removal differs from exact reject')
    return expected,pins


def check_raw_pair(first,second,count,absolute=0,relative=0,require_bit_identity=False):
    """Public saved-map comparison; caller must separately qualify fixture/domain."""
    raw=[Path(path).read_bytes() for path in (first,second)]
    require(type(count) is int and count>0 and all(len(value)==4*count for value in raw),'Exact binary32 arity required')
    values=[]
    for encoded in raw:
        decoded=array('f');decoded.frombytes(encoded)
        if sys.byteorder!='little': decoded.byteswap()
        require(all(math.isfinite(v) for v in decoded),'Nonfinite saved map')
        values.append(decoded)
    identical=raw[0]==raw[1]
    require(not require_bit_identity or identical,'Whole raw repeat bits differ')
    maximum=0.0
    for a,b in zip(*values):
        delta=abs(a-b);maximum=max(maximum,delta)
        require(delta<=absolute+relative*max(abs(a),abs(b)),'Saved numeric comparison failed')
    return dict(samples=count,max_absolute_delta=maximum,bit_identical=identical)


def audit(packet):
    """Public complete saved-packet replay; countword does not prove continuum zero."""
    packet=Path(packet).resolve();manifest={};totals=Counter();comparison_maxima={}
    require((packet/'result.json').is_file(),'Complete saved result required')
    require(sha((ROOT/'tools/water_sun_support_runtime.py').read_bytes())==RUNTIME_SHA
        and sha((ROOT/'tools/water_sun_support_pack.py').read_bytes())==BUILDER_SHA,'Frozen NEW public policy source differs')
    receipt=json_file(ROOT/'reports/2026-10-03-water-sun-support/cpu-native/HANDOFF.json')
    require(receipt['source']['sha256']==SOURCE_SHA and receipt['binary']['sha256']==BINARY_SHA,
        'Native receipt pins differ')
    require(sha((ROOT/receipt['source']['path']).read_bytes())==SOURCE_SHA
        and sha((ROOT/receipt['binary']['path']).read_bytes())==BINARY_SHA,'Native source/binary differs')
    dependencies=json_file(ROOT/'reports/2026-10-03-water-sun-support/cpu-native/include-dependencies.json')
    for dependency in dependencies['dependencies']:
        raw=(ROOT/dependency['path']).read_bytes()
        require(len(raw)==dependency['bytes'] and sha(raw)==dependency['sha256'],'Inherited source differs')
    result=json_file(packet/'result.json');shared.read_bytes(packet/'result.json',manifest)
    require(result['schema']=='aqualumen-water-sun-support-native-v1' and result['size']==SIZE
        and result['phase_seconds']==120 and result['patch_arity']==3
        and result['rawFormat']=='little-endian binary32 bottom-left origin' and result['policy']==POLICY
        and result['input_C12_is_TES'] is False and result['same_draw_input_payload'] is True
        and result['actual_shader_output_slots']==[0,1,2,3,4] and result['inactive_cleared_slots']==[5,6,7]
        and 'RTX 3080 Ti' in result['renderer'] and 'NVIDIA' in result['GL'],'Fixed native schema/fixture/policy')
    expected,pins=expected_sources()
    for name,value in expected.items(): require(shared.read_bytes(packet/name,manifest)==value,'Native source differs: '+name)
    names=[m+'-'+r for m in MODES for r in ROLES]
    require([p['name'] for p in result['programs']]==names and all(p['linked'] is True
        and sorted(p['stage_types'])==[35632,35633,36487,36488] and p['tess_layout']==[3,4,514,2305,0]
        for p in result['programs']),'Six linked four-stage programs required')
    require(result['case_count']==6 and [c['path'] for c in result['cases']]==list(CASES),'No native case subset')
    reports=[];zero_nodes=0
    for index,case in enumerate(result['cases']):
        print('CPU saved replay '+case['path'],file=sys.stderr,flush=True)
        wide=index>=4;positive=wide or index>=2;guard=1 if wide else index%2
        directory=packet/case['path'];programs={}
        require(case['guard']==guard and case['positive_cache'] is positive
            and case['aperture_degrees']==(60 if index==4 else 90 if index==5 else 2)
            and case['central_acceptance_case'] is (not wide),'Native fixture role differs')
        require(len(case['queried_program_sources'])==4,'Complete attached-source pairs')
        for pair,(mode,role) in zip(case['queried_program_sources'],((m,r) for m in MODES for r in ROLES[1:])):
            require(len(pair)==2,'Two attached program queries')
            for query,current_role in zip(pair,('physical',role)):
                key=mode+'-'+current_role;program=query['program']
                require(type(program) is int and program>0 and query['currentProgramBefore']==query['currentProgramAfter'],
                    'Attached-source state/identity differs')
                require(key not in programs or programs[key]==program,'Program identity changed across queries')
                programs[key]=program
                require(len(query['stages'])==4 and sorted(s['type'] for s in query['stages'])==[35632,35633,36487,36488],
                    'Four actual attached stages')
                for stage in query['stages']:
                    name=key+'-expanded.fsh' if stage['type']==35632 else 'geometry-stage'+str((35633,36488,36487).index(stage['type']))+'.glsl'
                    require(stage['bytes']==len(expected[name]) and stage['sha256']==sha(expected[name]),'Actual stage source digest differs')
                    totals['attachedStageDigests']+=1
        require(len(set(programs.values()))==6,'Aliased programs')
        frames={};inputs=[];ledger={}
        for mode in MODES:
            for role in ROLES:
                key=mode+'-'+role
                frames[key]=[shared.floats(directory/(key+'-slot'+str(s)+'.rgba32f'),PIXELS*4,manifest) for s in range(8)]
                frames[key].append(shared.floats(directory/(key+'-depth.f32'),PIXELS,manifest))
                for slot,values in enumerate(frames[key]):
                    suffix='slot'+str(slot)+'.rgba32f' if slot<8 else 'depth.f32'
                    repeat=shared.floats(directory/(key+'-repeat-'+suffix),len(values),manifest)
                    require(values.tobytes()==repeat.tobytes(),'Raw binary32 repeat differs')
                    ledger[key+'-'+('slot'+str(slot) if slot<8 else 'depth')+'-repeat']=(values,repeat,0,0)
                    totals['exactRepeatPairs']+=1;totals['finiteRawMaps']+=2
                    if 5<=slot<8: require(all(v==0 for v in values),'Inactive storage not cleared zero')
                for label,folder in ((key,directory),(key+'-repeat',directory),('actual-inputs',directory/(key+'-actual-inputs'))):
                    path=folder/(label+'-guard.json');g=json_file(path);shared.read_bytes(path,manifest)
                    shared.typed(g,dict(schema='aqualumen-native-sun-iris-guard-input-v1',program=programs[key],
                        currentProgramBefore=programs[key],currentProgramAfter=programs[key],
                        name='aqualumenSunTestAuthorized',type=5124,size=1,value=guard))
                    totals['typedScalarGuardQueries']+=1
                inputs.append(shared.input_snapshot(directory/(key+'-actual-inputs'),case,programs[key],manifest))
                totals['actualInputSnapshots']+=1;totals['finiteInputTextureMaps']+=8
        require(all(value==inputs[0] for value in inputs),'Matrices/textures differ across actual programs')
        vertices=shared.floats(directory/'uploaded-open-water-vertices.f32',90,manifest)
        require(all(vertices[p+12:p+15]==array('f',[0,1,10000]) for p in range(0,90,15)),'Uploaded material/lightmap differs')
        for mode in MODES:
            physical=frames[mode+'-physical']
            for role in ROLES[1:]:
                key=mode+'-'+role
                for slot,label,absolute,relative in ((0,'C0',.0005,.0002),(8,'depth',2e-6,0)):
                    ledger[key+'-'+label+'-passive']=(physical[slot],frames[key][slot],absolute,relative)
                if role=='reasons': ledger[key+'-C12-TES-exact']=(physical[4],frames[key][4],0,0)
            ledger[mode+'-reason-input-covariance-flags-exact']=(frames[mode+'-reasons'][3],frames[mode+'-inputs'][3],0,0)
        reject,zero=frames['reject-inputs'],frames['zero-inputs']
        for slot in (1,2):
            for alpha,label,absolute in ((False,'XYZ-EPS8',EPS8),(True,'alpha-exact',0)):
                channels=lambda values:array('f',(v for i,v in enumerate(values) if (i%4==3) is alpha))
                ledger['cross-mode-input-slot'+str(slot)+'-'+label]=(channels(reject[slot]),channels(zero[slot]),absolute,absolute)
        for slot,label in ((3,'input-covariance-flags'),(8,'physical-depth'),(4,'physical-TES')):
            a,b=(reject,zero) if slot==3 else (frames['reject-physical'],frames['zero-physical'])
            ledger['cross-mode-'+label+'-exact']=(a[slot],b[slot],0,0)
        if not wide:
            regression=not guard or not positive;a,b=frames['reject-physical'][0],frames['zero-physical'][0]
            def central(values):
                return array('f',(values[(y*SIZE+x)*4+c] for y in range(SIZE) for x in range(SIZE)
                    if (x-128)**2+(y-128)**2<=1600 for c in range(4)))
            ledger['reject-zero-C0-'+('regression' if regression else 'central-comparison')]=(a if regression else central(a),b if regression else central(b),2e-6,.0002)
        require(len(case['comparisons'])==len(ledger) and len({r['name'] for r in case['comparisons']})==len(ledger),'Complete comparison ledger')
        for row in case['comparisons']:
            a,b,absolute,relative=ledger.pop(row['name']);delta=shared.compare(a,b,absolute,relative)
            require(row==dict(name=row['name'],accepted=True,samples=len(a),max_absolute_delta=delta,
                absolute_tolerance=absolute,relative_tolerance=relative),'Recorded comparison differs from raw replay')
            comparison_maxima[case['path']+'/'+row['name']]=delta;totals['comparisonGatesRecomputed']+=1
        require(not ledger,'Unreplayed comparison')
        mode_reports=[];wide_delta=0.0
        for mode in MODES:
            physical,reasons,observed=(frames[mode+'-'+role] for role in ROLES)
            counts=Counter();classes=Counter();histogram=[0]*10
            for y in range(SIZE):
                for x in range(SIZE):
                    if not wide and (x-128)**2+(y-128)**2>1600: continue
                    p=(y*SIZE+x)*4;tes=list(physical[4][p:p+4]);cov=list(reasons[3][p:p+4])
                    if wide and tes[3]==0: counts['nonwater']+=1;continue
                    if wide and cov[3]!=15: counts['unadmitted']+=1;continue
                    counts['inspected']+=1
                    require(cov[3]==15 and shared.stage(tes) and shared.stage(reasons[4][p:p+4])
                        and all(frame[0][p+3]==1 for frame in (physical,reasons,observed)),'Actual raster domain')
                    require((cov[0]>0 and cov[2]>0 and cov[0]*cov[2]-cov[1]**2>0 and cov[0]+cov[2]>1e-5)
                        if guard else cov[:3]==[0,0,0],'Covariance domain')
                    payload=list(reasons[1][p:p+4]);status=list(reasons[2][p:p+4])
                    point=analyze_reason_point(dict(reasonTuple=payload,sun_status=status,covariance_flags=cov,
                        stage=list(reasons[4][p:p+4])),mode)
                    require(status[0]==guard and (positive or status[1:]==[0,0,0]),'Request/source negative control')
                    if not wide: require([status[0],status[1],status[3]]==[guard,int(guard and positive),0],
                        'Fixed central request/application/rejection status')
                    mean=list(observed[1][p:p+4]);view=list(observed[2][p:p+4]);target=list(observed[4][p:p+4])
                    require(mean[3]==guard and view[3]==status[0] and list(observed[3][p:p+4])==cov,'Same-draw input attribution')
                    if guard: require(all(abs(sum(v*v for v in values[:3])-1)<=8*EPS8 for values in (mean,view)),
                        'Raw mean/view norm domain')
                    else: require(mean==view==target==[0,0,0,0],'Uncalled helper defaults')
                    encoded=target[3];require(encoded==int(encoded),'First target packed integer')
                    if encoded:
                        first,node=divmod(int(encoded),64)
                        require(1<=first<=9 and 1<=node<=48 and first==payload[0] and sum(payload[1:])>0
                            and guard==1 and status[0]==1 and abs(sum(v*v for v in target[:3])-1)<=8*EPS8,
                            'Same-draw first target/reason/index domain')
                        counts['recordedFirstTargets']+=1
                    else: require(target==[0,0,0,0] and payload==[0,0,0,0],'Absent target is NOT classified support zero')
                    outcome=point['certificateCounts'];classes.update(outcome)
                    counts['complete48']+=mode=='zero' and outcome['calls']==48
                    counts['zeroBranchPoints']+=mode=='zero' and outcome['zero']>0
                    require(sum(payload[1:])<=48-outcome['zero'],'Rejected certified-zero node')
                    counts['applied']+=status[1]==1;histogram[int(payload[0])]+=1
                    for name,value in zip(('hemisphere','receiver','other'),payload[1:]): counts[name]+=int(value)
                    if wide and mode=='reject':
                        for channel in range(3): wide_delta=max(wide_delta,abs(physical[0][p+channel]-frames['zero-physical'][0][p+channel]))
            position=MODES.index(mode)
            for key,value in (('inspected_points_reject_zero',counts['inspected']),('domain_qualified_points_reject_zero',counts['inspected']),
                ('input_count_accounted_points_reject_zero',counts['inspected']),('applied_points_reject_zero',counts['applied']),
                ('first_failed_target_points_reject_zero',counts['recordedFirstTargets']),('nonwater_points_reject_zero',counts['nonwater']),
                ('unadmitted_points_reject_zero',counts['unadmitted']),('complete48_certificate_ledger_points_reject_zero',counts['complete48']),
                ('observed_zero_branch_points_reject_zero',counts['zeroBranchPoints'])):
                require(case[key][position]==value,'Saved all-point total differs: '+key)
            require(case['first_reason_histograms_reject_zero'][position]==histogram
                and case['certificate_class_totals_reject_zero'][position]==[classes[k] for k in ('zero','support','unknown','calls')],
                'Saved reason/certificate totals differ')
            require(counts['inspected']>0 and (wide or counts['inspected']==5025),'Fixed ROI shrank')
            if wide: require(counts['inspected']+counts['nonwater']+counts['unadmitted']==PIXELS,'Wide canvas accounting incomplete')
            if mode=='zero': zero_nodes+=classes['zero']
            mode_reports.append(dict(mode=mode,counts=dict(counts),firstReasonHistogram=histogram,
                certificateCounts=dict(classes),certificateCountsCollected=mode=='zero'))
        require(case['wide_C0_max_delta_descriptive_only']==wide_delta,'Wide descriptive C0 statistic differs')
        require(case['fixture_qualified'] is True and case['passivity_accounting_regression_accepted'] is True,'Native case terminal gates')
        require(len(case['fixed_six_samples'])==6,'Fixed sample count')
        for sample in case['fixed_six_samples']:
            x,y=sample['pixel'];p=(y*SIZE+x)*4;require(len(sample['variants'])==2,'Fixed variants')
            for saved,mode in zip(sample['variants'],MODES):
                status=list(frames[mode+'-reasons'][2][p:p+4]);counts=decode_counts(status[2])
                require(saved==dict(mode=mode,physical_C0=list(frames[mode+'-physical'][0][p:p+4]),
                    reason_C9=list(frames[mode+'-reasons'][1][p:p+4]),WNS_requested_applied_countword_rejected=status,
                    certificate_counts_collected=mode=='zero',counts_zero_support_unknown_calls=[counts[k] for k in ('zero','support','unknown','calls')],
                    inputs=[list(frames[mode+'-inputs'][s][p:p+4]) for s in range(1,5)]),'Fixed sample/raw mismatch')
                totals['fixedSampleVariantsRecomputed']+=1
        reports.append(dict(path=case['path'],variants=mode_reports,wideC0MaximumDescriptiveOnly=wide_delta))
    require(result['actual_observed_zero_nodes']==zero_nodes and result['zero_branch_observed'] is (zero_nodes>0),
        'Exporter zero-branch observation differs')
    require(result['status']=='PASS' and result['fixture_qualified'] is True and result['accepted'] is True,'Exporter terminal gates differ')
    return dict(schema='aqualumen-independent-sun-support-native-audit-v1',status='PASS_SAVED_NATIVE_REPLAY',
        sourceSHA256=SOURCE_SHA,binarySHA256=BINARY_SHA,resultSHA256=manifest[str(packet/'result.json')],
        publicRuntimeSHA256=RUNTIME_SHA,builderSHA256=BUILDER_SHA,
        pinnedReadOnlyUtilitiesSHA256=SHARED_SHA,packSHA256=pins,counts=dict(totals),cases=reports,
        comparisonMaxima=comparison_maxima,actualZeroNodes=zero_nodes,zeroBranchObserved=zero_nodes>0,
        zeroBranchExecutionWitnessQualified=zero_nodes>0,sourceRecoveryQualified=True,wholeCanvasPassivityQualified=True,
        empiricalCentralRegressionQualified=True,inputC12IsTES=False,reasonC12IsTES=True,
        all48PhysicalClassificationsProven=False,continuousZeroProven=False,GPUArithmeticCauseProven=False,
        physicsAccepted=False,pixelAAAccepted=False,IrisAccepted=False,visualAccepted=False,motionAccepted=False,
        FPSAccepted=False,energyAccepted=False,reciprocityAccepted=False,shippingAccepted=False,
        manifest={str(Path(path).relative_to(packet)):value for path,value in manifest.items()},
        scope='Saved root-owned native source/input/binding/repeat/passivity/regression/count replay only. '
            'Wide60/90 C0 differences are descriptive, no optical equality gate. Count48 classifies discrete quadrature targets, '
            'not continuum zero or integral correctness. Zero observed nodes is explicitly no new zero-branch main proof. '
            'Input C12 is first target, never TES. No target means NOT_EVALUATED, not support zero. '
            'Inactive5–7 are cleared storage. Source/binary bytes do not independently attest process lifecycle.')


if __name__=='__main__':
    require(len(sys.argv)==2,'usage: audit.py SAVED_NATIVE_PACKET')
    print(json.dumps(audit(sys.argv[1]),indent=2,sort_keys=True,allow_nan=False))
