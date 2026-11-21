"""CPU saved first-failed cap-node inputs; not optical or rendering acceptance."""
import math
import struct
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import BadZipFile
from collections import Counter
from water_residual_sun_iris_runtime import (json_file,zip_files,exact_fields,guard_observation,
    readback_points,IDENTITY,COORDINATES)
from water_residual_sun_reason_runtime import metadata_object
from water_snell_main_pack import (PARENT,PARENT_SHA,HELPER,HELPER_SHA,WATER,MANIFEST,NODE,NODE_SHA,
    EXTENSION,NODE_EXTENSION_GUARD,INPUT_STORE,recover_helper,recover_inputs)
from water_residual_sun_reason_pack import STORE
from water_snell_boundary_reference import diagnose,ETA
from water_tessellation_runtime import require

CHANNELS={'9':['meanNormalX','meanNormalY','meanNormalZ','helperCalled'],
    '10':['viewX','viewY','viewZ','requested'],'11':['Cxx','Cxz','Czz','productionFlags'],
    '12':['firstFailedTargetX','firstFailedTargetY','firstFailedTargetZ','encodedFirstReasonAndNode']}
INPUT_PINS={
    'old':('e287f2fe2caeb922f249f49c0025c24631fd64a8bec055e04d18429c1760d1d8',
           '31c03cbd1df0cf15c0c0cf069b0fa9f07447a127337a3c40310196987bf5226a'),
    'stable':('0d62d7b6d9067934c62787677070eb7aa923c7b4eff67ec3250a218d0af3579e',
              '2163974162c8656811b18a595f0fa950279db3cdebff431204f07bcbdee430a9')}
REFERENCE_SHA='511770d7c090a8ea5423cb7afd30dd655a2a09253c10f27ef0921215ba0bc9e0'


def sha(value): return hashlib.sha256(value).hexdigest()


def pack_policy(pack):
    files=zip_files(pack);metadata=metadata_object(files[MANIFEST])
    mode=metadata.get('mode');require(type(mode) is str and mode in INPUT_PINS,'Unknown math variant')
    exact_fields(metadata,dict(schema='aqualumen-water-snell-main-v1',observe='inputs',test_only=True,
        not_shipping=True,shipping_fix=False,parent_pack_sha256=PARENT_SHA,parent_helper_sha256=HELPER_SHA,
        geometry_factor=4,fixed_phase_seconds=120.0,old_shader_bytes_exact=False,
        C12_is_TES=False,FINAL_inherited_display_is_authoritative=False,passive_assignments_only=True,
        actual_GL_neutrality_verified=False,runtime_accepted=False,physics_accepted=False,
        visual_accepted=False,shipping_accepted=False),'Wrong authoritative input policy')
    require(metadata.get('target_channels')==CHANNELS and metadata.get('declared_cap_rule')==[4,12],
        'Inputs are not coefficients, reasons or TES')
    exact_fields(metadata.get('target_code'),dict(base=64,node_index_range=[1,48],reason_range=[1,9],
        none=0,formula='(r*12+j+1)+64*firstReason',same_draw_first_reason=True),'Wrong target encoding')
    exact_fields(metadata.get('guard_uniform'),dict(name='aqualumenSunTestAuthorized',glsl_type='int',
        required_value=1,default_if_mod_absent=0),'Wrong caller guard declaration')
    require(metadata.get('status0_policy')==metadata.get('statusMinus1_policy')=='Unchanged whole replacement rejection',
        'Support zero/unknown must not replace legacy admission')
    require(all(v is False for k,v in metadata.items() if k.endswith('_accepted')),'Unobserved acceptance')
    parent_path=Path(__file__).resolve().parents[1]/PARENT
    require(sha(parent_path.read_bytes())==PARENT_SHA,'Frozen reason parent changed')
    parent=zip_files(parent_path)
    additions={MANIFEST,'PARENT-SNELL-MAIN-reason-helper.glsl','PARENT-SNELL-MAIN-reason-water.fsh',
        'PARENT-SNELL-MAIN-physical.fsh','SNELL-MAIN-physical.fsh','SNELL-MAIN-reason-helper.glsl',
        'SNELL-MAIN-reason-water.fsh'}
    if mode=='stable': additions|={NODE,'PARENT-SNELL-MAIN-node.glsl'}
    require(set(files)==set(parent)|additions,'Unapproved archive members')
    for name,value in parent.items():
        if name not in (HELPER,WATER): require(files[name]==value,'Parent geometry/source/provenance changed')
    for archived,name in (('PARENT-SNELL-MAIN-reason-helper.glsl',HELPER),
        ('PARENT-SNELL-MAIN-reason-water.fsh',WATER),('PARENT-SNELL-MAIN-physical.fsh','PARENT-SUN-REASONS-physical.fsh')):
        require(files[archived]==parent[name],'Archived original differs')
    helper,water=files[HELPER],files[WATER]
    require((sha(helper),sha(water))==INPUT_PINS[mode],'Input assignments/source differ from pinned variant')
    reason_helper=files['SNELL-MAIN-reason-helper.glsl']
    require(recover_inputs(helper)==reason_helper,'Input removal fails same-variant recovery')
    require((recover_helper(reason_helper) if mode=='stable' else reason_helper)==parent[HELPER],
        'Math removal fails exact old helper recovery')
    reason_water=files['SNELL-MAIN-reason-water.fsh']
    require(water.decode().count(INPUT_STORE)==1 and water.decode().replace(INPUT_STORE,STORE).encode()==reason_water,
        'Input STORE removal differs')
    original_water=reason_water.replace(EXTENSION.encode(),b'',1) if mode=='stable' else reason_water
    require(original_water==parent[WATER] and (mode=='old' or reason_water.startswith(
        b'#version 330 compatibility\n'+EXTENSION.encode())),'Only stable extension may differ in main')
    physical=files['SNELL-MAIN-physical.fsh']
    require(water.decode().replace(INPUT_STORE,'').encode()==physical,'Physical main recovery differs')
    for fields,member in ((('helper_sha256','input_helper_sha256'),HELPER),
        (('observer_water_fs_sha256',),WATER),(('physical_water_fs_sha256',),'SNELL-MAIN-physical.fsh'),
        (('reason_helper_sha256',),'SNELL-MAIN-reason-helper.glsl'),
        (('reason_water_fs_sha256',),'SNELL-MAIN-reason-water.fsh')):
        require(all(metadata.get(k)==sha(files[member]) for k in fields),'Stale member digest')
    exact_fields(metadata,dict(input_helper_member=HELPER,physical_water_fs_member='SNELL-MAIN-physical.fsh',
        reason_helper_member='SNELL-MAIN-reason-helper.glsl',reason_water_fs_member='SNELL-MAIN-reason-water.fsh'),
        'Wrong current source members')
    if mode=='stable':
        original=files['PARENT-SNELL-MAIN-node.glsl'];adapted=files[NODE]
        require(sha(original)==NODE_SHA and original.count(NODE_EXTENSION_GUARD.encode())==1
            and adapted==original.replace(NODE_EXTENSION_GUARD.encode(),b'',1),'Stable module adaptation changed math')
        exact_fields(metadata,dict(node_original_member='PARENT-SNELL-MAIN-node.glsl',node_original_sha256=NODE_SHA,
            node_adapted_member=NODE,node_adapted_sha256=sha(adapted)),'Wrong stable module identity')
    inherited=metadata_object(parent['WATER-RESIDUAL-SUN-REASONS.json'])
    require(inherited['fixed_texel_coordinates']==[list(p) for p in COORDINATES]
        and inherited['minimum_qualified_applied_points']==4,'Inherited fixed sampling policy changed')
    return metadata


def analyze_record(record):
    """Public same-draw first-node input interpretation; never all-node cause."""
    for field in ('mean_called','view_requested','covariance_flags','first_target_reason'):
        values=record[field]
        require(type(values) is list and len(values)==4 and all(type(v) in (float,int)
            and math.isfinite(v) and struct.unpack('<f',struct.pack('<f',v))[0]==v for v in values),
            'Finite lossless binary32 vec4 required')
    called=record['mean_called'][3];requested=record['view_requested'][3]
    require(called in (0,1) and requested in (0,1),'Invalid called/requested flags')
    xx,xz,zz,flags=record['covariance_flags']
    require(flags==int(flags) and 0<=flags<=15 and (not int(flags)&8 or int(flags)&7==7),
            'Invalid original production flagword')
    require(not requested or called==1 and flags==15,'Request lacks actual helper/water domain')
    if called:
        require(all(abs(sum(x*x for x in record[name][:3])-1)<=2e-5
            for name in ('mean_called','view_requested')),'Called helper lacks raw approximately-unit vectors')
    else:
        require(record['mean_called'][:3]==record['view_requested'][:3]==[0,0,0]
            and [xx,xz,zz]==[0,0,0] and requested==0,'Uncalled helper contains stale inputs')
    encoded=record['first_target_reason'][3]
    require(encoded==int(encoded),'First reason/index must be integer')
    if encoded==0:
        require(record['first_target_reason'][:3]==[0,0,0],'Absent first target is not zero')
        return dict(**record,helperCalled=bool(called),requested=bool(requested),firstReason=0,
            firstNodeIndex=None,reference=None,arithmeticReplayClassification='NOT_EVALUATED',
            observedGateClassification='NO_FIRST_FAILED_NODE_OBSERVED' if called else 'HELPER_NOT_CALLED',
            GPUArithmeticCauseProven=False)
    reason,index=divmod(int(encoded),64)
    require(1<=reason<=9 and 1<=index<=48,'First failed node encoding outside declared loop')
    require(called==requested==1 and flags==15 and xx>0 and zz>0 and xx*zz-xz*xz>0,
        'First node lacks admitted input domain')
    ref=diagnose(record['view_requested'][:3],record['first_target_reason'][:3],ETA)
    return dict(**record,helperCalled=bool(called),requested=bool(requested),firstReason=reason,
        firstNodeIndex=index-1,reference=ref,arithmeticReplayClassification=ref['classification'],
        observedGateClassification=('POSITIVE_SUPPORT_COMPOUND_GATE_REJECTION'
            if ref['physical']['supported'] and reason in (2,4) else
            'PHYSICALLY_UNSUPPORTED_AT_COMPOUND_GATE' if ref['classification']=='PHYSICALLY_UNSUPPORTED'
            and reason in (2,4) else ref['classification']),
        GPUArithmeticCauseProven=False)


def audit(raw_file,pack,guard_raw):
    """Read-only public saved-file seam."""
    require(sha(Path(__file__).with_name('water_snell_boundary_reference.py').read_bytes())==REFERENCE_SHA,
        'Independent reference changed')
    pack=Path(pack);metadata=pack_policy(pack)
    identity={**IDENTITY,'packName':pack.name,'packSha256':sha(pack.read_bytes())}
    guard=json_file(guard_raw);guard_observation(guard,identity)
    raw=json_file(raw_file)
    # Shared readback_points checks only finite storage/bindings/state. Override
    # historical labels BEFORE any coefficient or simplex qualification.
    records=[dict(x=p['x'],y=p['y'],mean_called=p['coefficients'],view_requested=p['sun_status'],
        covariance_flags=p['covariance_flags'],first_target_reason=p['stage'])
        for p in readback_points(raw,identity)]
    points=[analyze_record(record) for record in records]
    histogram={str(k):sum(p['firstReason']==k for p in points) for k in range(10)}
    return dict(schema='aqualumen-snell-main-input-audit-v1',mode=metadata['mode'],selectedPoints=len(points),
        inputEvidenceQualified=True,readbackQualified=True,guardUniformQualified=True,sourceRecoveryQualified=True,
        firstReasonHistogram=histogram,referenceClassifications=dict(Counter(p['arithmeticReplayClassification'] for p in points)),
        helperCalledPoints=sum(p['helperCalled'] for p in points),requestedPoints=sum(p['requested'] for p in points),
        recordedFirstTargets=sum(p['firstNodeIndex'] is not None for p in points),points=points,
        packSha256=identity['packSha256'],sourceSha256=dict(helper=metadata['helper_sha256'],
            waterFS=metadata['observer_water_fs_sha256'],reference=REFERENCE_SHA),
        guardFrame=guard['frameBefore'],finalSnapshotFrame=raw['snapshotFrame'],minimumApplicationGateUnchanged=4,
        targetAndFirstReasonStoredTogether=True,TESObserved=False,applicationObserved=False,
        legacyFullBaseAdmissionDirectlyObserved=False,actualSunUniformObserved=False,
        sameFrameGuardAndReadbackProven=False,all48NodeCausesObserved=False,GPUArithmeticCauseProven=False,
        physicalAccepted=False,visualAccepted=False,pixelAAAccepted=False,performanceAccepted=False,
        energyAccepted=False,reciprocityAccepted=False,shippingAccepted=False,
        scope='Same-draw first-target/reason input tuple only; prepared guard is separate-frame. No TES/coefficients/application, exact GPU arithmetic cause, all48 classification or rendered appearance proof.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw',type=Path);parser.add_argument('pack',type=Path);parser.add_argument('guard_raw',type=Path)
    args=parser.parse_args()
    try: result=audit(args.raw,args.pack,args.guard_raw)
    except (OSError,ValueError,TypeError,KeyError,BadZipFile,RuntimeError,OverflowError,UnicodeError) as failure:
        parser.exit(1,'Rejected Snell main input observation: '+type(failure).__name__+'\n')
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))


if __name__=='__main__': main()
