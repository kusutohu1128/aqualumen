"""Read-only CPU replay of four saved actual Iris support-policy captures."""
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import water_sun_support_runtime as public
from water_sun_support_pack import (MANIFEST,HELPER,WATER,CERTIFICATE,CERTIFICATE_SHA,
    PARENTS,FROZEN,recover_helper,recover_water,SUPPORT_STORE)
from water_sun_support_reference import classify,ETA
from water_snell_boundary_reference import diagnose
from water_residual_sun_iris_runtime import (IDENTITY,COORDINATES,json_file,zip_files,
    exact_fields,readback_points)
from report import check_png,metrics,validate_underwater_up
from test_thin_runtime_audit import read_intervals

PINS={
    'water_sun_support_runtime.py':'f7d37236671e4333ac12312dae32cd6cdec39023dee01622f12258d7bc680d31',
    'water_sun_support_pack.py':'c229872b2906003599181800ab6cf5ed8a61685a675ebb04fa06b9e3bfd81abb',
    'water_sun_support_reference.py':'90fa6e06cbef8b38cdcbc2471ba3f8b7bb4506c1216422253c84fd8b27b0bcff',
    'water_snell_boundary_reference.py':'511770d7c090a8ea5423cb7afd30dd655a2a09253c10f27ef0921215ba0bc9e0',
    'water_snell_main_runtime.py':'dc1fabf8706821f7f9a5e813bdfd45c2092a6317841ed09ffafd2237860f5ad8',
    'water_residual_sun_iris_runtime.py':'a18e8f7c9bfb4ace2b1e3d5ac5ddfabf4dc46ef115f4e0f334f21d90da91e977',
    'water_residual_sun_reason_runtime.py':'4782c027ee1f2a5683f702ed631cc73217bd178a7cc5a7597f102c0e92b2d84d'}
PACK_PINS={
    'reject-reasons':'681bd672fde78d6e7e9a89a873c2b29a3d0b64d81f473c245960bbc4cccbe0ff',
    'reject-inputs':'32589948e7b0773b857801d12a55730fb9135aff26e0f40775a33f9bc1bf757e',
    'zero-reasons':'7f15dbc05a68cc80be3ae0f6ea66ec5ae3c3f42785eb753d4e603f7089ba9048',
    'zero-inputs':'5a1dd986f95961c96d9175301b8ce432d65cde792e89f99e01935234abde70b0'}
MODES=('reject','zero');ROLES=('reasons','inputs')
STAGES=('gbuffers_water.vsh','gbuffers_water.tcs','gbuffers_water.tes')
LAB_PACKS=Path.home()/'.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft/shaderpacks'


def require(value,message):
    if not value: raise ValueError(message)


def sha(value): return hashlib.sha256(value).hexdigest()
def bits(values): return [struct.pack('<f',v).hex() for v in values]
def stamp(value): return datetime.fromisoformat(value.replace('Z','+00:00'))


def float32(values):
    require(type(values) is list and len(values)==4 and all(type(v) in (int,float)
        and math.isfinite(v) and struct.unpack('<f',struct.pack('<f',v))[0]==v for v in values),
        'Observation must preserve finite lossless binary32 vec4')


def source_contract(pack,key):
    """Check the NEW source chain independently of inherited optical legends."""
    require(sha(pack.read_bytes())==PACK_PINS[key],'Frozen diagnostic ZIP changed')
    files=zip_files(pack);meta=json.loads(files[MANIFEST]);mode,role=key.split('-')
    exact_fields(meta,dict(schema='aqualumen-water-sun-support-v1',mode=mode,observe=role,
        test_only=True,not_shipping=True,shipping_fix=False,geometry_factor=4,
        fixed_phase_seconds=120.0,source_kind_constant=0,minimum_qualified_applied_points=4,
        C12_is_TES=role=='reasons',countsNotCollected=mode=='reject' or role=='inputs',
        current_certificate_counts_observed=mode=='zero' and role=='reasons'),
        'Wrong authoritative NEW support policy')
    require(meta['fixed_texel_coordinates']==[list(p) for p in COORDINATES]
        and meta['declared_cap_rule']==[4,12],'Sampling/rule policy changed')
    require(meta['certificate_count_policy']['formula']=='zero+64*support+4096*unknown+262144*calls'
        and meta['certificate_count_policy']['class_sum_equals_calls'] is True,
        'Countword policy changed')
    filename,parent_pin=PARENTS[role];parent_path=ROOT/FROZEN/filename
    require(sha(parent_path.read_bytes())==parent_pin==meta['parent_pack_sha256'],'Frozen stable parent changed')
    parent=zip_files(parent_path)
    require(recover_helper(files[HELPER])==parent[HELPER] and recover_water(files[WATER],role)==parent[WATER],
        'Same-role exact source erasure failed')
    for name in STAGES:
        require(files['shaders/'+name]==parent['shaders/'+name],'Geometry stage changed')
    require(files['shaders/lib/atmosphere.glsl']==parent['shaders/lib/atmosphere.glsl']
        and files['shaders/lib/water_snell_inverse.glsl']==parent['shaders/lib/water_snell_inverse.glsl'],
        'Stock source or stable inverse changed')
    if mode=='zero':
        require(sha(files[CERTIFICATE])==CERTIFICATE_SHA==meta['certificate_sha256'],'Certificate pin changed')
        if role=='reasons': require(files[WATER].decode().count(SUPPORT_STORE)==1,'Missing actual packed STORE')
    else: require(files[HELPER]==parent[HELPER] and files[WATER]==parent[WATER], 'Reject control not byte exact')
    return files,meta


def stage_contract(stage,identity):
    exact_fields(stage,{**IDENTITY,'schema':'aqualumen-water-stage-observation-v1','available':True,
        'scope':'terrain-tessellation-stages','observerVersion':'0.1.0','expectedPack':identity['packName'],
        'expectedPackSha256':identity['packSha256'],'readOnly':True,'errorFlagConsumed':False,
        'localIntegratedSinglePlayer':True,'scopeAccepted':True,'currentPipelineMatches':True,
        'benchmarkState':'complete','afterSetupStateTail':True,'pass':'TRANSLUCENT',
        'constructorContainsTessellation':True,'usingTessellationAtAdmission':True,
        'sourceHashesRequested':True,'linkStatus':1,'attachedShaderCount':4,
        'tessControlOutputVertices':3,'patchVertices':3,'tesSourceMarkerPresent':True,
        'programAndFrameUnchanged':True},'Wrong attached-stage observation')
    require(stage['constructorProgram']==stage['programBefore']==stage['programAfter']>0
        and stage['frameBefore']==stage['frameAfter']>=0,'Stage program/frame changed')
    require(stage['versions']['aqualumen_benchmark']=='0.3.9' and stage['versions']['aqualumen_physics']=='0.3.0'
        and stage['capabilities']['GL_ARB_tessellation_shader'] is True
        and 'NVIDIA' in stage['capabilities']['renderer'],'Stage version/capability changed')
    stages=stage['stages']
    require(len(stages)==4 and sorted(s['type'] for s in stages)==[35632,35633,36487,36488]
        and len({s['shader'] for s in stages})==4 and all(type(s['sourceBytes']) is int
        and 0<s['sourceBytes']<=256*1024 and type(s['type']) is int and len(s['sourceSha256'])==64
        and all(c in '0123456789abcdef' for c in s['sourceSha256']) for s in stages),'Typed four-stage hashes required')
    for field in ('drawIssuedProven','tessInvocationCountProven','fragmentValueFetchProven',
                  'exclusiveWaterProgramProven','nativeOrNaturalAppearanceAccepted'):
        require(stage[field] is False,'Unobserved stage claim')
    return {str(s['type']):dict(bytes=s['sourceBytes'],sha256=s['sourceSha256']) for s in stages}


def independent_raw(raw,role,mode):
    """Retain all16; first-target reference is not an all48 node oracle."""
    records=[]
    for i,(x,y) in enumerate(COORDINATES):
        maps=[s['samples'][i]['rgba'] for s in raw['samplers'][:4]]
        for values in maps: float32(values)
        require(all((s['samples'][i]['x'],s['samples'][i]['y'])==(x,y) for s in raw['samplers'][:4]),
            'Fixed selected coordinates changed')
        if role=='reasons':
            first,h,r,o=maps[0];requested,applied,encoded,rejected=maps[1]
            require(all(v==int(v) and 0<=v<=48 for v in (h,r,o,rejected))
                and first==int(first) and 0<=first<=9,'Malformed reason integer tuple')
            require(requested in (0,1) and applied in (0,1),'Malformed original request/application')
            remaining=int(encoded);require(encoded==remaining and 0<=remaining<2**24,'Malformed countword')
            counts=[]
            for _ in range(4): remaining,value=divmod(remaining,64);counts.append(value)
            zero,support,unknown,calls=counts
            require(remaining==0 and all(v<=48 for v in counts) and zero+support+unknown==calls,
                'Countword does not account actual calls')
            if mode=='reject': require(counts==[0,0,0,0],'Reject unexpectedly collected counts')
            else:
                require(unknown<=o and unknown<=rejected and h+r+o<=48-zero,'Unknown/zero rejection accounting contradicts')
                if applied: require(calls==48 and unknown==rejected==0,'Applied operator lacks complete known ledger')
            records.append(dict(x=x,y=y,reasonTuple=maps[0],status=maps[1],covarianceFlags=maps[2],
                TES=maps[3],certificateCounts=dict(zip(('zero','support','unknown','calls'),counts))))
        else:
            encoded=maps[3][3];require(encoded==int(encoded) and encoded>=0,'Malformed first-target code')
            if encoded:
                reason,index=divmod(int(encoded),64);require(1<=reason<=9 and 1<=index<=48,'Out-of-range first node')
                exact=classify(maps[1][:3],maps[3][:3],ETA);decimal=diagnose(maps[1][:3],maps[3][:3],ETA)
                require(decimal['precision_agreement'],'80/120-digit reference disagreement')
                require(exact['class']==(1 if decimal['physical']['supported'] else 0)
                    if decimal['classification'] in ('PHYSICALLY_UNSUPPORTED','SUPPORTED_REPLAY_ACCEPTED',
                        'POSITIVE_SUPPORTED_NUMERIC_REJECTION') else exact['class']==-1,
                    'Fraction and Decimal branch classifications disagree')
            else:
                require(maps[3][:3]==[0,0,0],'No observed first failure has nonzero target')
                reason=0;index=None;exact=decimal=None
            records.append(dict(x=x,y=y,meanCalled=maps[0],viewRequested=maps[1],covarianceFlags=maps[2],
                firstTarget=maps[3],firstReason=reason,firstNodeIndex=index,exactSupportReference=exact,
                decimalReference=decimal,observation='FIRST_FAILURE_OBSERVED' if encoded else 'NO_OBSERVED_FAIL'))
    return records


def audit(packet):
    packet=Path(packet).resolve()
    for filename,pin in PINS.items(): require(sha((ROOT/'tools'/filename).read_bytes())==pin,'Frozen public/reference source changed')
    records={};points={};archives={};manifest={}
    for mode in MODES:
        for role in ROLES:
            key=mode+'-'+role;directory=packet/('iris-'+key)
            pack_name='Aqualumen-ShoreProbe-world-sun-support-'+key+'-v1.zip'
            pack=packet/'cpu-pack'/pack_name;installed=LAB_PACKS/pack_name
            require(installed.read_bytes()==pack.read_bytes(),'Retained actual installed ZIP differs from frozen export')
            files,meta=source_contract(pack,key);archives[key]=files
            recalculated=public.audit(directory/'final-raw.json',pack,directory/'guard-raw.json')
            canonical=(json.dumps(recalculated,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
            require((directory/('reason-audit.json' if role=='reasons' else 'input-audit.json')).read_bytes()==canonical,
                'Public saved-file replay differs from root result')
            require(recalculated['selectedPoints']==16,'Selected corpus changed')
            if role=='reasons':
                require(recalculated['minimumQualifiedAppliedPoints']==4
                    and recalculated['operatorActiveQualified']==(recalculated['qualifiedAppliedPoints']>=4),
                    'Minimum application gate changed')
            raw=json_file(directory/'final-raw.json');guard=json_file(directory/'guard-raw.json');stage=json_file(directory/'stage-raw.json')
            identity={**IDENTITY,'packName':pack_name,'packSha256':PACK_PINS[key]}
            readback_points(raw,identity);points[key]=independent_raw(raw,role,mode)
            stages=stage_contract(stage,identity);geometry={k:v for k,v in stages.items() if k!='35632'}
            require(stage['constructorProgram']==guard['constructorProgram'],'Prepared guard/stage program differs')
            if records: require(geometry==records['reject-reasons']['actualGeometryStageHashes'],'Actual rewritten geometry hashes changed')
            run_dir=directory/'run';run=json_file(run_dir/'run.json');complete=json_file(run_dir/'complete.json');scene=json_file(run_dir/'underwater-up-near.json')
            exact_fields(run,dict(world_id=IDENTITY['worldId'],seed=IDENTITY['seed'],world_generator='minecraft:noise/overworld',
                scenarios=['underwater-up-near'],warmup_seconds=10.0,sample_seconds=5.0,frame_limit=120,
                vsync=False,render_chunks=12,simulation_chunks=6),'Changed world or warmed-view controls')
            for value in (run,scene): exact_fields(value,dict(world_id=IDENTITY['worldId'],pack_name=pack_name,
                pack_sha256=PACK_PINS[key],shader_active=True,shader_fallback=False,resolution=[1600,900],
                framebuffer_resolution=[1600,900],player_dimension='minecraft:overworld'),'Wrong actual pack/scene identity')
            require(run['mods']['aqualumen_benchmark']=='0.3.9' and run['mods']['aqualumen_physics']=='0.3.0',
                'Wrong benchmark/physics versions')
            require('NVIDIA' in run['gl_renderer'] and '3080 Ti' in run['gl_renderer'],'Wrong recorded renderer')
            properties={}
            for line in run['iris_configuration'].splitlines():
                if line and not line.startswith('#') and '=' in line:
                    name,value=line.split('=',1);require(name not in properties,'Duplicate Iris property');properties[name]=value
            require(properties.get('enableShaders')=='true' and properties.get('shaderPack')==pack_name,
                'Recorded Iris selection differs from actual diagnostic identity')
            exact_fields(complete,dict(status='complete',scenarios=['underwater-up-near'],fixture_cleanup_complete=True),
                'Incomplete measurement or cleanup')
            require(run['run_id']==scene['run_id']==complete['run_id'] and scene['window_focused'] is True
                and scene['camera_follows_local_player'] is True and scene['physics_active_seen'] is True,'Wrong run/focus/local actor')
            validate_underwater_up(scene,'underwater-up-near');check_png(run_dir/'underwater-up-near.png',(1600,900))
            ns,ms=read_intervals(run_dir/'underwater-up-near.csv');calculated=metrics(ms)
            for field,value in calculated.items(): require(scene[field]==value if type(value) is int else
                math.isclose(scene[field],value,rel_tol=1e-12,abs_tol=1e-9),'Raw integer-ns metric differs: '+field)
            require(stamp(complete['utc'])<stamp(raw['utc']) and stamp(complete['utc'])<stamp(guard['capturedUtc'])
                and stamp(complete['utc'])<stamp(stage['capturedUtc']),'Observer captured before measurement completed')
            require(raw['unshiftedCameraPosition']==scene['actual_camera_position'],'Held camera pose differs')
            records[key]=dict(publicAuditSha256=sha(canonical),packSha256=PACK_PINS[key],selectedPoints=16,
                actualGeometryStageHashes=geometry,actualFragmentStageHash=stages['35632'],
                applicationVerdict=recalculated.get('applicationVerdict','NOT_OBSERVED_INPUT_ROLE'),
                qualifiedAppliedPoints=recalculated.get('qualifiedAppliedPoints'),certificateCounts=recalculated.get('certificateCounts'),
                complete48CertificateLoopPoints=recalculated.get('complete48CertificateLoopPoints'),
                firstReasonHistogram=recalculated['firstReasonHistogram'],metrics=calculated,rawNanosecondsTotal=sum(ns),
                rawFrameIntervals=len(ns),cameraPosition=raw['unshiftedCameraPosition'],actualEyeDepth=scene['underwater_up']['actual_eye_depth'],
                guardFrame=guard['frameBefore'],stageFrame=stage['frameBefore'],finalFrame=raw['snapshotFrame'],
                frameTimeCounter=raw['frameTimeCounter'],observations=points[key])
            for path in directory.rglob('*'):
                if path.is_file(): manifest[str(path.relative_to(packet))]=sha(path.read_bytes())
    comparisons=[]
    for i,(reject,zero) in enumerate(zip(points['reject-inputs'],points['zero-inputs'])):
        equal={field:bits(reject[field])==bits(zero[field]) for field in ('meanCalled','viewRequested','covarianceFlags')}
        for mode,current in (('reject',reject),('zero',zero)):
            counterpart=points[mode+'-reasons'][i]
            require(bits(counterpart['covarianceFlags'])==bits(current['covarianceFlags']), 'Cross-role covariance/flags changed')
        both=reject['firstNodeIndex'] is not None and zero['firstNodeIndex'] is not None
        comparisons.append(dict(x=reject['x'],y=reject['y'],inputFieldBitsEqual=equal,
            crossCaptureInputWitnessQualified=all(equal.values()),bothFirstTargetsObserved=both,
            targetBitsEqual=bits(reject['firstTarget'][:3])==bits(zero['firstTarget'][:3]) if both else None,
            firstNodeIndexEqual=reject['firstNodeIndex']==zero['firstNodeIndex'] if both else None,
            rejectReason=reject['firstReason'],zeroReason=zero['firstReason'],
            rejectIndex=reject['firstNodeIndex'],zeroIndex=zero['firstNodeIndex'],
            rejectExactClass=reject['exactSupportReference']['class'] if reject['exactSupportReference'] else None,
            zeroExactClass=zero['exactSupportReference']['class'] if zero['exactSupportReference'] else None,
            firstFailureNoLongerObserved=reject['firstNodeIndex'] is not None and zero['firstNodeIndex'] is None,
            disappearanceProvesZero=False,GPUArithmeticCauseProven=False))
    for name in STAGES:
        require(len({archives[key]['shaders/'+name] for key in archives})==1,'Archive geometry differs across roles/policies')
    return dict(schema='aqualumen-independent-water-sun-support-iris-v1',evidenceReplay='PASS',
        minimumQualifiedAppliedPoints=4,publicSourceSHA256=PINS,records=records,crossCapturePoints=comparisons,
        crossCaptureInputWitnessQualifiedPoints=sum(p['crossCaptureInputWitnessQualified'] for p in comparisons),
        manifest=manifest,sameFrameProven=False,all48PhysicalClassificationsProven=False,continuousCapZeroProven=False,
        FresnelOrTIRZeroProven=False,actualGPUArithmeticCauseProven=False,actualSunUniformObserved=False,
        drawIssuedProven=False,fragmentFetchProven=False,naturalAppearanceAccepted=False,pixelAAAccepted=False,
        energyAccepted=False,reciprocityAccepted=False,FPSFloorAccepted=False,shippingAccepted=False,
        scope='Four separate warmed1600x900/120-cap captures; full PNG and integer-ns audit, exact NEW pack/source '
            'construction, fixed16 selected readback and minimum4 application gate. Prepared guard, linked-stage '
            'hashes, FINAL, inputs and PNG are separate captures. First-target exact Fraction/Decimal80/120 replay '
            'does not classify every node or prove GPU rounding. Countword proves sampled classifications only; '
            'input code0 means no observed first failure, never continuum or Fresnel zero. No natural appearance, '
            '1440p, motion, native pixel-AA, energy, FPS floor or shipping adoption claim.')


if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('usage: audit.py SAVED_SUPPORT_PACKET')
    print(json.dumps(audit(sys.argv[1]),indent=2,sort_keys=True,allow_nan=False))
