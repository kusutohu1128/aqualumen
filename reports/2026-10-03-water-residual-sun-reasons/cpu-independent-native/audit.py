"""Read-only CPU verification of the frozen passive-reasons native packet."""
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from water_residual_sun_reason_runtime import pack_policy,qualify_point
from water_residual_sun_iris_runtime import zip_files,json_file
from water_residual_sun_reason_pack import STORE,strip_reason_blocks
from water_residual_sun_iris_pack import STORE as OLD_STORE

SOURCE_SHA='bca17bcc2c8cbe380c361d38f7df6b07e7b1639159cbde00572912e9796c1d4a'
BINARY_SHA='1756a6898e7b66ea07868fbbc75ce83878be21716e1dc8112029de43c1d327bc'
RESULT_SHA='4d9e977b0edac41b3b0d684c0abbb01506e9064e8a6e1453d95a1e5e51f88275'
ZIP_SHA='61e76a7ea00265eab85614858a8dd3560dde8e3d21f1dfa4f9f6a711d0898aa4'
SIZE=257;PIXELS=SIZE*SIZE
ROLES=('original-physical','original-coefficient-observer','reason-observer')
CASES=('central2-cachezero-guard0','central2-cachezero-guard1',
       'central2-cachepositive-guard0','central2-cachepositive-guard1','wide60-cachepositive-guard1')
POLICY=dict(C0_absolute=.0005,C0_relative=.0002,depth_absolute=2e-6,C12_absolute=0,
            repeat_absolute=0,coefficient_absolute=2e-5)


def require(value,message):
    if not value: raise ValueError(message)


def sha(value): return hashlib.sha256(value).hexdigest()


def typed(value,expected):
    require(type(value) is dict and set(value)==set(expected) and all(type(value[k]) is type(v)
        and value[k]==v for k,v in expected.items()),'Typed exact observation differs')


def expand(files,name,level=0):
    require(level<=32,'Include recursion bound')
    output=[]
    for line in files[name].decode().splitlines():
        if line.startswith('#include'):
            found=re.match(r'#include\s+"([^\"]+)"',line)
            require(found is not None,'Malformed source include')
            member='shaders/'+found[1].lstrip('/')
            require('..' not in Path(member).parts,'Unsafe source member')
            output.append(expand(files,member,level+1))
        else: output.append(line+'\n')
    return ''.join(output)


def sources(packet,pack,result,manifest):
    metadata=pack_policy(pack);files=zip_files(pack)
    parent=zip_files(ROOT/'reports/2026-10-03-water-residual-sun-iris/cpu-pack/Aqualumen-ShoreProbe-world-native-sun-iris-enabled1-v1.zip')
    expected={'original-helper.glsl':parent['shaders/lib/water_residual_sun.glsl'],
        'reason-helper.glsl':files['shaders/lib/water_residual_sun.glsl'],
        'reason-metadata.json':files['WATER-RESIDUAL-SUN-REASONS.json']}
    for n in range(3): expected[f'geometry-stage{n}.glsl']=expand(files,'shaders/gbuffers_water.'+('vsh','tcs','tes')[n]).encode()
    expected['original-physical-expanded.fsh']=expand(parent,'PARENT-SUN-IRIS-physical.fsh').encode()
    expected['original-coefficient-observer-expanded.fsh']=expand(parent,'shaders/gbuffers_water.fsh').encode()
    expected['reason-observer-expanded.fsh']=expand(files,'shaders/gbuffers_water.fsh').encode()
    for name,value in expected.items(): require(read_bytes(packet/name,manifest)==value,'Expanded source/archive differs: '+name)
    original=expected['original-physical-expanded.fsh'].decode()
    require(expected['original-coefficient-observer-expanded.fsh'].decode().replace(OLD_STORE,'')==original,
            'Original observer STORE recovery')
    require(strip_reason_blocks(expected['reason-observer-expanded.fsh'].decode().replace(STORE,''))==original,
            'Reason STORE/helper expanded recovery')
    require(result['reason_metadata_sha256']==sha(expected['reason-metadata.json']) and
        result['original_helper_sha256']==sha(expected['original-helper.glsl']) and
        result['reason_helper_sha256']==sha(expected['reason-helper.glsl']),'Recorded source hashes differ')
    return expected,metadata


def read_bytes(path,manifest):
    require(path.stat().st_size<=2*1024*1024,'Bounded native artifact')
    value=path.read_bytes();manifest[str(path)]=sha(value);return value


def floats(path,count,manifest):
    encoded=read_bytes(path,manifest);require(len(encoded)==count*4,'Truncated/wrong raw size')
    values=array('f');values.frombytes(encoded)
    if sys.byteorder!='little': values.byteswap()
    require(all(math.isfinite(v) for v in values),'Nonfinite native map')
    return values


def f32(v): return struct.unpack('<f',struct.pack('<f',v))[0]


def stage(s):
    return abs(s[3]-1)<=8*2**-23 and abs(sum(s[:3])-1)<=2e-5 and all(-2e-5<=v<=1+2e-5 for v in s[:3])


def compare(a,b,absolute=0,relative=0):
    require(len(a)==len(b),'Comparison arity')
    if a==b: return 0.0
    maximum=0.0
    for x,y in zip(a,b):
        delta=abs(x-y);maximum=max(maximum,delta)
        require(delta<=absolute+relative*max(abs(x),abs(y)),'Native comparison failed')
    return maximum


def input_snapshot(directory,case,program,manifest):
    meta=json_file(directory/'actual-inputs.json');read_bytes(directory/'actual-inputs.json',manifest)
    require(meta['schema']=='aqualumen-native-residual-sun-inputs-v1' and meta['stateRestored'] is True
        and meta['program']==meta['currentProgramBefore']==meta['currentProgramAfter']==program
        and meta['activeTextureBefore']==meta['activeTextureAfter']
        and meta['textureBindingBefore']==meta['textureBindingAfter'],'Input query state/program')
    matrix=meta['matrices'];focal=f32(1/math.tan(case['aperture_degrees']*math.pi/360))
    require(meta['fixedFunctionProjection']==matrix['gbufferProjection'] and
        meta['fixedFunctionModelView']==matrix['gbufferModelView'] and
        matrix['gbufferProjection'][0]==matrix['gbufferProjection'][5]==focal and
        meta['aperture_degrees']==case['aperture_degrees'],'Actual projection')
    require(len(matrix)==4 and all(len(m)==16 and all(math.isfinite(v) and f32(v)==v for v in m) for m in matrix.values()),'Actual binary32 matrices')
    uniforms={u['name']:u for u in meta['uniforms']}
    for name,kind,values in (('sunPosition',35665,[0,0,-1]),('rainStrength',5126,[0]),
        ('viewWidth',5126,[257]),('viewHeight',5126,[257]),('isEyeInWater',5124,[1]),('aqualumenDimension',5124,[0])):
        require(uniforms[name]==dict(name=name,type=kind,size=1,values=values),'Typed actual uniform')
    inv=matrix['gbufferModelViewInverse'];raw_sun=uniforms['sunPosition']['values']
    axis=[sum(inv[c*4+r]*raw_sun[c] for c in range(3)) for r in range(3)]
    require(axis==meta['sunDirectionDerivedFromActualUniforms']==[0,1,0],'Actual-input derived Sun axis')
    names=('gtexture','colortex4','colortex6','depthtex1','shadowtex0','colortex8','aqualumenBathymetry','colortex7')
    sizes=((1,1,34836),(257,257,34836),(64,32,34836),(257,257,36012),(1,1,36012),(1,1,34842),(64,64,34836),(64,32,34836))
    samplers=meta['samplers'];require(len(samplers)==8 and [s['unit'] for s in samplers]==list(range(8)),'Input sampler order')
    require(len({s['texture'] for s in samplers})==8,'Aliased input textures')
    identity=[];cache=[.5,.625,.75] if case['positive_cache'] else [0,0,0]
    for unit,s in enumerate(samplers):
        w,h,fmt=sizes[unit];components=1 if unit in (3,4) else 4
        require(all(type(v) is int for k,v in s.items() if k not in ('name','file')),'Integer sampler/storage fields')
        require((s['name'],s['uniformType'],s['uniformSize'],s['uniformUnit'],s['width'],s['height'],s['internalFormat'],s['components'])==
            (names[unit],35682 if unit==4 else 35678,1,unit,w,h,fmt,components),'Actual sampler/storage identity')
        require(s['texture']>0 and s['sampler']==0 and s['minFilter']==s['magFilter']==9728
            and s['wrapS']==s['wrapT']==33071 and s['compareMode']==(34894 if unit==4 else 0),'Input sampler state')
        name=f'input-sampler{unit}'+('.f32' if components==1 else '.rgba32f')
        require(s['file']==name,'Unexpected raw filename')
        data=floats(directory/name,w*h*components,manifest)
        if unit in (2,7):
            for p in range(0,len(data),4): require(list(data[p:p+3])==(cache if unit==2 and p==31*64*4 else [0,0,0]) and data[p+3]==1,'Actual cache/sky')
        if unit==3: require(all(v==1 for v in data),'Opaque depth open fixture')
        identity.append(manifest[str(directory/name)])
    require(meta['solarCacheRGB']==cache and meta['SOLAR']==[18,17.6,17] and
        meta['solarRadius']==.00465 and meta['weatherFactor']==1,'Stock source/cache/weather')
    targets=meta['targets'];require(len(targets)==8 and [t['slot'] for t in targets]==list(range(8))
        and all((t['width'],t['height'],t['internalFormat'])==(257,257,34836) for t in targets)
        and (meta['depth']['width'],meta['depth']['height'],meta['depth']['internalFormat'])==(257,257,36012),'Actual MRT/depth storage')
    return matrix,identity


def audit(packetnativeout,newreasonzip,probeBIN):
    packet=Path(packetnativeout);manifest={};pack=Path(newreasonzip);binary=Path(probeBIN)
    require(sha(binary.read_bytes())==BINARY_SHA and sha((ROOT/'tools/water_residual_sun_reason_probe.cpp').read_bytes())==SOURCE_SHA,'Frozen native source/binary')
    require(sha(pack.read_bytes())==ZIP_SHA,'Frozen reason ZIP')
    result=json_file(packet/'result.json');require(sha(read_bytes(packet/'result.json',manifest))==RESULT_SHA,'Frozen result bytes')
    require(result['schema']=='aqualumen-native-sun-reasons-passivity-v1' and result['size']==257 and
        result['phase_seconds']==120 and result['actual_patch_arity']==3 and result['culling_enabled'] is False
        and 'NVIDIA' in result['renderer'] and result['policy']==POLICY,'Fixed native scope/policy')
    expected,metadata=sources(packet,pack,result,manifest)
    require([p['name'] for p in result['programs']]==list(ROLES) and all(p['linked'] is True and
        sorted(p['stage_types'])==[35632,35633,36487,36488] and p['tess_layout']==[3,4,514,2305,0] for p in result['programs']),'Three actual linked programs')
    require(result['case_count']==5 and [c['path'] for c in result['cases']]==list(CASES),'Fixed complete five cases')
    case_reports=[];map_count=guard_count=stage_queries=0;comparison_count=0;maximum=0.0
    for index,case in enumerate(result['cases']):
        wide=index==4;positive=wide or index>=2;guard=1 if wide else index%2;directory=packet/case['path']
        require(case['guard']==guard and case['positive_cache'] is positive and case['aperture_degrees']==(60 if wide else 2)
            and case['central_acceptance_case'] is (not wide),'Case declaration')
        programs={}
        for key,roles in (('queriedProgramSourcesOriginal',ROLES[:2]),('queriedProgramSourcesReason',(ROLES[0],ROLES[2]))):
            require(len(case[key])==2,'Attached-source queries')
            for query,role in zip(case[key],roles):
                require(query['currentProgramBefore']==query['currentProgramAfter'],'Source query state')
                programs[role]=query['program'];items=query['stages']
                require(len(items)==4 and sorted(s['type'] for s in items)==[35632,35633,36487,36488],'Actual stage types')
                for s in items:
                    name=(role+'-expanded.fsh') if s['type']==35632 else f'geometry-stage{(35633,36488,36487).index(s["type"])}.glsl'
                    require(s['bytes']==len(expected[name]) and s['sha256']==sha(expected[name]),'Actual glGetShaderSource digest');stage_queries+=1
        frames={};inputs=[]
        for role in ROLES:
            frames[role]=[floats(directory/f'{role}-slot{s}.rgba32f',PIXELS*4,manifest) for s in range(8)]
            depth=floats(directory/f'{role}-depth.f32',PIXELS,manifest);frames[role].append(depth)
            for s in range(9):
                suffix=f'slot{s}.rgba32f' if s<8 else 'depth.f32'
                repeat=floats(directory/f'{role}-repeat-{suffix}',PIXELS*(4 if s<8 else 1),manifest)
                require(frames[role][s].tobytes()==repeat.tobytes(),'Whole raw repeat exact');comparison_count+=1;map_count+=2
            for label,d in ((role,directory),(role+'-repeat',directory),('actual-inputs',directory/(role+'-inputs'))):
                g=json_file(d/(label+'-guard.json'));read_bytes(d/(label+'-guard.json'),manifest)
                typed(g,dict(schema='aqualumen-native-sun-iris-guard-input-v1',program=programs[role],currentProgramBefore=programs[role],currentProgramAfter=programs[role],name='aqualumenSunTestAuthorized',type=5124,size=1,value=guard));guard_count+=1
            inputs.append(input_snapshot(directory/(role+'-inputs'),case,programs[role],manifest))
        require(inputs[0]==inputs[1]==inputs[2],'Physical/coefficient/reason inputs differ')
        vertices=floats(directory/'uploaded-open-water-vertices.f32',90,manifest)
        require(all(vertices[p+12:p+15]==array('f',[0,1,10000]) for p in range(0,90,15)),'Actual vertex lightmap/material')
        pure,original,reason=(frames[r] for r in ROLES)
        for other in (original,reason):
            for slot,ab,rel in ((0,.0005,.0002),(8,2e-6,0),(4,0,0)):
                maximum=max(maximum,compare(pure[slot],other[slot],ab,rel));comparison_count+=1
        for slot in (2,3): compare(original[slot],reason[slot]);comparison_count+=1
        require(len(case['comparisons'])==35 and all(c['accepted'] is True for c in case['comparisons']),'Recorded complete comparison ledger')
        counts=dict(inspected_points=0,qualified_points=0,reason_accounting_points=0,status_expected_points=0,
            wide_stage_water_points=0,wide_nonwater_points=0,wide_unadmitted_points=0,rejected_points=0,loop_rejected_points=0)
        histogram=[0]*10;groups=[0]*3
        for y in range(257):
            for x in range(257):
                if not wide and (x-128)**2+(y-128)**2>1600: continue
                p=(y*257+x)*4;s=pure[4][p:p+4];cov=list(original[3][p:p+4]);rcov=list(reason[3][p:p+4])
                if wide and s[3]==0: counts['wide_nonwater_points']+=1;continue
                if wide:
                    counts['wide_stage_water_points']+=1
                    require(stage(s) and cov[3]==int(cov[3]) and 0<=cov[3]<=15,'Wide stage/flag')
                    if cov[3]!=15: counts['wide_unadmitted_points']+=1;continue
                counts['inspected_points']+=1
                status=list(reason[2][p:p+4]);payload=list(reason[1][p:p+4]);co=list(original[1][p:p+4]);os=list(original[2][p:p+4])
                require(cov[3]==rcov[3]==15 and all(f[0][p+3]==1 and stage(f[4][p:p+4]) for f in (pure,original,reason)),'Whole-domain alpha/TES')
                if guard:
                    require(cov[0]>0 and cov[2]>0 and cov[0]*cov[2]-cov[1]**2>0 and cov[0]+cov[2]>1e-5,'Actual covariance')
                    if not wide: require(abs(co[0]-1)<=2e-5 and min(co[1:])>=0 and co[3]<=co[1]+2e-5 and abs(co[1]+co[2]-co[0])<=2e-5 and os[3]==status[3]==0,'Central coefficients/status domain')
                else: require(co==os==[0]*4 and cov[:3]==rcov[:3]==[0]*3,'Guard0 defaults')
                point=dict(reasonTuple=payload,sun_status=status,covariance_flags=rcov,stage=list(reason[4][p:p+4]));qualify_point(point)
                require(status[0]==guard and (positive or status[1:]==[0,0,0]),'Native requested/source status')
                if not wide: require(status==[guard,int(guard and positive),0,0],'Central application status')
                counts['qualified_points']+=1;counts['reason_accounting_points']+=1;counts['status_expected_points']+=1
                histogram[int(payload[0])]+=1
                for j in range(3): groups[j]+=int(payload[j+1])
                counts['rejected_points']+=status[3]>0;counts['loop_rejected_points']+=sum(payload[1:])>0
        for key,value in counts.items(): require(case[key]==value,'Recorded count disagrees: '+key)
        require(histogram==case['first_reason_histogram_0_to_9'] and groups==case['grouped_failed_node_totals'],'Recorded reason totals differ')
        require(counts['inspected_points']>0 and (wide or counts['inspected_points']==5025),'No central subset shrink')
        if wide: require(counts['wide_nonwater_points']+counts['wide_unadmitted_points']+counts['inspected_points']==PIXELS,'Wide complete canvas accounting')
        case_reports.append(dict(path=case['path'],**counts,firstReasonHistogram0To9=histogram,groupedRejectedNodes=groups))
    relative_manifest={str(Path(p).relative_to(packet)):d for p,d in manifest.items()}
    return dict(schema='aqualumen-independent-native-sun-reasons-audit-v1',status='PASS',
        sourceSHA256=SOURCE_SHA,binarySHA256=BINARY_SHA,resultSHA256=RESULT_SHA,reasonZipSHA256=ZIP_SHA,
        cases=case_reports,rawMapsFinite=map_count,exactRepeatPairs=135,comparisonsRecomputed=comparison_count,
        maximumPassiveDelta=maximum,typedGuardQueries=guard_count,attachedStageDigestsChecked=stage_queries,
        actualInputSnapshots=15,sourceRecoveryQualified=True,wholeCanvasPassivityQualified=True,
        manifest=relative_manifest,physicalAccepted=False,pixelAAAccepted=False,IrisAccepted=False,
        visualAccepted=False,motionAccepted=False,FPSAccepted=False,shippingAccepted=False,
        scope='Saved native passive reason proof only. Four central full5025 corpora; wide canvas coverage/exclusions explicit. Group3/9 counts are not specific reason3 counts; inactive slots5–7 storage is not shader output proof. Root-owned executable identity/lifecycle is not independently attested by saved bytes.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('packet');parser.add_argument('reason_zip');parser.add_argument('probe_binary')
    args=parser.parse_args()
    print(json.dumps(audit(args.packet,args.reason_zip,args.probe_binary),indent=2,sort_keys=True))
