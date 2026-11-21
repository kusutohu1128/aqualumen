"""CPU saved reason-observation audit; never rendering/model acceptance."""
import hashlib
import json
import argparse
from pathlib import Path
from zipfile import BadZipFile

from water_residual_sun_iris_runtime import (IDENTITY,exact_fields,json_file,
    guard_observation,readback_points,zip_files,COORDINATES)
from water_residual_sun_reason_pack import (PARENT_RELATIVE,SUN_MEMBER,STORE,PANELS,
    PARENT_STORE,PARENT_PANELS,instrument_helper,strip_reason_blocks)
from water_residual_sun_iris_pack import FLAGS
from water_tessellation_runtime import require

MANIFEST='WATER-RESIDUAL-SUN-REASONS.json'
PARENT_SHA='34387253bd9de9bef2e306eb45b8d3c412861f7b324e03f81a4056f60e675f2c'
SUN_SHA='a0708a5d59dfb126473bf51c033f7f76b7d7edcdcf258303f35593f3a91196c3'
INSTRUMENTED_SHA='3a39ab9442d4ad37a7d21110f44b8b94eb3689313bdaa7602ea9f5f1722f407c'
CHANNELS={'9':['firstReason','hemisphereRejectedNodes','receiverRejectedNodes','otherRejectedNodes'],
          '10':['requested','featureApplied','sourceKind','rejectionCount'],
          '11':['Cxx','Cxz','Czz','productionFlags'],
          '12':['barycentricX','barycentricY','barycentricZ','stagePresent']}
GROUPS=dict(hemisphere=[3,9],receiver=[6,7],other=[1,2,4,5,8])
CATEGORIES={'1':'target_or_axis','2':'facet_or_critical','3':'reflected_hemisphere',
    '4':'reconstruction_or_finite','5':'kernel','6':'transmission_opaque',
    '7':'reflection_alpha_rejection','8':'sky_or_nonfinite_receiver','9':'transmission_hemisphere'}


def digest(value): return hashlib.sha256(value).hexdigest()


def metadata_object(encoded):
    require(len(encoded)<=32768,'Oversized reason metadata')
    def unique(pairs):
        value={}
        for key,item in pairs:
            require(key not in value,'Duplicate metadata key');value[key]=item
        return value
    result=json.loads(encoded,object_pairs_hook=unique)
    require(type(result) is dict,'Metadata object required')
    return result


def pack_policy(pack):
    files=zip_files(pack)
    metadata=metadata_object(files[MANIFEST])
    exact_fields(metadata,dict(schema='aqualumen-water-residual-sun-reasons-v1',
        mode='guarded-native-sun-reason-observe',test_only=True,not_shipping=True,enabled=1,
        geometry_factor=4,fixed_phase_seconds=120.0,loop_only=True,
        pre_or_post_loop_rejection_categorized=False,minimum_qualified_applied_points=4),
        'Wrong authoritative reason policy')
    require(metadata.get('target_channels')==CHANNELS,'C9 must declare reasons, not coefficients')
    require(metadata.get('fixed_texel_coordinates')==[list(p) for p in COORDINATES]
        and metadata.get('declared_cap_rule')==[4,12] and metadata.get('reason_groups')==GROUPS
        and metadata.get('reason_categories')==CATEGORIES,'Wrong fixed reason/category/point policy')
    exact_fields(metadata.get('production_flags'),dict(known=1,upper=2,underwater=4,residualEligible=8),'Wrong typed masks')
    require(metadata.get('production_flags_expression')==FLAGS and metadata.get('production_flags_range')==[0,15],
        'Changed production flagword')
    exact_fields(metadata.get('guard_uniform'),dict(name='aqualumenSunTestAuthorized',glsl_type='int',
        required_value=1,default_if_mod_absent=0),'Wrong authorization declaration')
    require(metadata.get('guard_call_expression')=='if (aqualumenSunTestAuthorized==1)',
        'Missing explicit caller authorization')
    exact_fields(metadata,dict(world_guard_requires_mod=True,shader_authorization_gate_present=True,
        source_instrumentation_present=True),'Missing TEST/source scope')
    for key in ('shipping_fix','runtime_accepted','GL_neutrality_verified','physics_accepted',
        'pixel_AA_equivalence_accepted','energy_accepted','reciprocity_accepted','visual_accepted',
        'performance_accepted','motion_accepted','generated_geometry_accepted',
        'actual_shader_node_count_qualified','pack_enforces_world_guard','actual_guard_runtime_verified',
        'inherited_metadata_is_current_atlas_policy','inherited_metadata_is_current_optical_policy',
        'coefficient_telemetry_current','predicate_arithmetic_control_flow_changed','normalization_changed',
        'geometry_source_changed','atmosphere_source_changed','scatter_policy_changed','scalar_units_changed',
        'FS_C0_source_observation_changed'):
        require(metadata.get(key) is False,'Unobserved or changed boundary cannot be accepted')
    parent_path=Path(__file__).resolve().parents[1]/PARENT_RELATIVE
    require(digest(parent_path.read_bytes())==PARENT_SHA,'Frozen guarded parent changed')
    parent=zip_files(parent_path)
    additions={'PARENT-SUN-REASONS-helper.glsl','PARENT-SUN-REASONS-physical.fsh',
        'PARENT-SUN-REASONS-final.fsh',MANIFEST,'WATER-RESIDUAL-SUN-REASONS.txt'}
    require(set(files)==set(parent)|additions,'Unexpected/missing archive members')
    for name,content in parent.items():
        if name not in (SUN_MEMBER,'shaders/gbuffers_water.fsh','shaders/final.fsh'):
            require(files[name]==content,'Changed parent/provenance/geometry/helper member')
    parent_metadata=parent['WATER-RESIDUAL-SUN-IRIS.json']
    exact_fields(metadata,dict(parent_guarded_pack_sha256=PARENT_SHA,
        parent_guarded_metadata_member='WATER-RESIDUAL-SUN-IRIS.json',
        parent_guarded_metadata_sha256=digest(parent_metadata)),'Wrong pinned source chain')
    parent_policy=metadata_object(parent_metadata)
    require(metadata.get('original_sha256')==parent_policy['original_sha256'],'Original provenance differs')
    helper=files[SUN_MEMBER]
    require(digest(parent[SUN_MEMBER])==SUN_SHA and digest(helper)==INSTRUMENTED_SHA
        and helper==instrument_helper(parent[SUN_MEMBER])
        and strip_reason_blocks(helper.decode()).encode()==parent[SUN_MEMBER],
        'Reason instrumentation differs or changes physical helper')
    require(metadata.get('helper_sha256')=={**parent_policy['helper_sha256'],SUN_MEMBER:digest(helper)},
        'Helper declarations differ')
    for name,sha in metadata['helper_sha256'].items(): require(digest(files[name])==sha,'Helper digest differs')
    for archived,source in (('PARENT-SUN-REASONS-helper.glsl',SUN_MEMBER),
        ('PARENT-SUN-REASONS-physical.fsh','PARENT-SUN-IRIS-physical.fsh'),
        ('PARENT-SUN-REASONS-final.fsh','shaders/final.fsh')):
        require(files[archived]==parent[source],'Archived parent bytes differ')
    water=files['shaders/gbuffers_water.fsh'].decode()
    require(water==parent['shaders/gbuffers_water.fsh'].decode().replace(PARENT_STORE,STORE)
        and water.count(STORE)==1 and water.replace(STORE,'').encode()==files['PARENT-SUN-REASONS-physical.fsh'],
        'Reason STORE differs or fails physical recovery')
    require(files['shaders/final.fsh']==parent['shaders/final.fsh'].decode().replace(PARENT_PANELS,PANELS).encode(),
        'FINAL role display differs')
    for member_key,hash_key,member in (
        ('instrumented_helper_member','instrumented_helper_sha256',SUN_MEMBER),
        ('physical_helper_member','physical_helper_sha256','PARENT-SUN-REASONS-helper.glsl'),
        ('physical_water_fs_member','physical_water_fs_sha256','PARENT-SUN-REASONS-physical.fsh'),
        ('parent_final_member','parent_final_sha256','PARENT-SUN-REASONS-final.fsh')):
        exact_fields(metadata,{member_key:member,hash_key:digest(files[member])},'Wrong source member/hash')
    require(metadata.get('observer_water_fs_sha256')==digest(files['shaders/gbuffers_water.fsh']),
        'Observer FS hash differs')
    return metadata


def integer(value,limit,message):
    require(type(value) in (int,float) and value==int(value) and 0<=value<=limit,message)
    return int(value)


def qualify_point(point):
    first,hemisphere,receiver,other=point['reasonTuple']
    first=integer(first,9,'Invalid first node reason')
    counts=[integer(v,48,'Invalid failed-node count') for v in (hemisphere,receiver,other)]
    total=sum(counts);require(total<=48,'More rejected nodes than declared loop')
    requested,applied,kind,rejected=point['sun_status']
    require(requested in (0,1) and applied in (0,1) and kind==0,'Malformed native Sun status')
    rejected=integer(rejected,48,'Invalid native rejection count')
    require(not applied or requested==1 and rejected==0,'Applied output lacks request or has rejection')
    flags=integer(point['covariance_flags'][3],15,'Invalid production flagword')
    require(not flags&8 or flags&7==7,'Eligibility lacks original water domain')
    require(not requested or flags==15,'Requested source lacks original eligibility')
    if total:
        require(requested==1 and applied==0 and rejected==total and first>0,
                'Loop reason accounting contradicts native status')
        group=0 if first in (3,9) else 1 if first in (6,7) else 2
        require(counts[group]>0,'First category has no positive group count')
        point['reasonClassification']='CLASSIFIED_LOOP_REJECTION'
    else:
        require(first==0 and rejected in (0,1),'Unclassified fallback must not masquerade as counted loop')
        require(requested==1 or applied==rejected==0,'Unrequested source claims rejection/application')
        point['reasonClassification']=('UNCLASSIFIED_PRE_OR_POST_LOOP_REJECTION' if rejected else
            'APPLIED' if applied else 'NO_COUNTED_REJECTION')
    stage=point['stage']
    if stage==[0,0,0,0]:
        require(flags==0 and point['sun_status']==[0,0,0,0] and point['reasonTuple']==[0,0,0,0],
                'Nonwater texel claims domain/status/reason')
    else:
        require(abs(stage[3]-1)<=8*2**-23 and all(-2e-5<=x<=1+2e-5 for x in stage[:3])
            and abs(sum(stage[:3])-1)<=2e-5,'Invalid TES marker/simplex')
    if applied:
        xx,xz,zz,_=point['covariance_flags']
        require(xx>0 and zz>0 and xx*zz-xz*xz>0 and stage!=[0,0,0,0],
                'Applied source lacks strict covariance or TES')


def audit(raw_file, newreasonpack, guard_raw):
    """Read-only public saved-file boundary; C9 is NOT coefficients."""
    pack=Path(newreasonpack);metadata=pack_policy(pack)
    identity={**IDENTITY,'packName':pack.name,'packSha256':hashlib.sha256(pack.read_bytes()).hexdigest()}
    guard=json_file(guard_raw);guard_observation(guard,identity)
    raw=json_file(raw_file);points=readback_points(raw,identity)
    # This shared routine qualifies only scalar bindings/finite raw texels.
    # Rename its historical C9 label immediately; no coefficient validator.
    for point in points: point['reasonTuple']=point.pop('coefficients')
    triples=set();requested=applied=loop_rejected=unclassified=0
    first_histogram={str(k):0 for k in range(1,10)}
    groups=dict(hemisphere=0,receiver=0,other=0)
    for point in points:
        qualify_point(point)
        reason=point['reasonTuple'];status=point['sun_status']
        first,hemisphere,receiver,other=reason
        if first: first_histogram[str(int(first))]+=1
        requested+=status[0]==1;applied+=status[1]==1
        if sum(reason[1:])>0:
            loop_rejected+=1
            for name,count in zip(groups,(hemisphere,receiver,other)): groups[name]+=count
        elif status[3]>0: unclassified+=1
        stage=point['stage']
        if stage[3]!=0: triples.add(tuple(round(v,4) for v in stage[:3]))
    require(sum(p['stage'][3]!=0 for p in points)>=4 and len(triples)>=2,'Vacuous/constant TES output')
    verdict='QUALIFIED_SELECTED_APPLICATION' if applied>=4 else 'NEGATIVE_INSUFFICIENT_APPLICATION'
    return dict(selectedPoints=len(points),qualifiedAppliedPoints=applied,requestedPoints=requested,
        loopRejectedPoints=loop_rejected,unclassifiedRejectedPoints=unclassified,
        firstReasonHistogram=first_histogram,firstReasonCategories=CATEGORIES,
        groupedRejectedNodes=groups,reasonEvidenceQualified=True,readbackQualified=True,
        perCategoryNodeCountsObserved=False,sunUniformObserved=False,receiverGroupIsOpaqueProof=False,
        reasonCountsScope='Histogram counts first failed category per selected texel; hemisphere node total combines3/9, receiver combines6/7. Later individual node categories are not exported.',
        guardUniformQualified=True,reasonGate='QUALIFIED_SELECTED_NODE_REASON_ACCOUNTING',
        operatorActiveQualified=applied>=4,applicationVerdict=verdict,minimumQualifiedAppliedPoints=4,
        coefficientClosureObserved=False,physicalAccepted=False,pixelAAAccepted=False,
        visualAccepted=False,motionAccepted=False,performanceAccepted=False,shippingAccepted=False,
        sameFrameProven=False,drawIssuedProven=False,fragmentFetchProven=False,
        observerPassivityAccepted=False,geometryAccepted=False,nodeCountProven=False,
        energyAccepted=False,reciprocityAccepted=False,pngCausalityAccepted=False,
        actualFourRoleBindingsQualified=True,sourceRecoveryQualified=True,
        packSha256=identity['packSha256'],guardFrame=guard['frameBefore'],finalSnapshotFrame=raw['snapshotFrame'],
        distinctBarycentricTriples=len(triples),points=points,
        sourceSha256=dict(physicalHelper=SUN_SHA,reasonHelper=INSTRUMENTED_SHA,
            observerWaterFS=metadata['observer_water_fs_sha256'],physicalWaterFS=metadata['physical_water_fs_sha256']),
        scope='Separate prepared int1 guard and selected FINAL first-node reasons; no coefficient closure, same-frame/draw/fetch, physical, AA or visual acceptance')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw',type=Path);parser.add_argument('pack',type=Path);parser.add_argument('guard_raw',type=Path)
    args=parser.parse_args()
    try: report=audit(args.raw,args.pack,args.guard_raw)
    except (OSError,ValueError,TypeError,KeyError,BadZipFile,RuntimeError,OverflowError,UnicodeError) as failure:
        parser.exit(1,'Rejected Sun reason observation: '+type(failure).__name__+'\n')
    print(json.dumps(report,indent=2,sort_keys=True))
    if report['applicationVerdict']=='NEGATIVE_INSUFFICIENT_APPLICATION': raise SystemExit(1)


if __name__=='__main__': main()
