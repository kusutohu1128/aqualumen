"""CPU saved Snell-main reason audit; fixed16/min4, no physical acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import BadZipFile

from water_residual_sun_iris_runtime import (IDENTITY,COORDINATES,exact_fields,json_file,
    zip_files,guard_observation,readback_points)
from water_residual_sun_reason_runtime import (metadata_object,qualify_point,CHANNELS,CATEGORIES)
from water_snell_main_pack import (PARENT,PARENT_SHA,HELPER,HELPER_SHA,WATER,MANIFEST,
    NODE,NODE_SHA,NODE_EXTENSION_GUARD,EXTENSION,recover_helper)
from water_residual_sun_reason_pack import STORE
from water_tessellation_runtime import require

ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT/'reports/2026-10-03-water-snell-main/cpu-pack'
PINS={
    'old':('9d09ed721c619b803279900cebb377fa00c144e92b43d732b70ce2999f8368fd',
           '3a39ab9442d4ad37a7d21110f44b8b94eb3689313bdaa7602ea9f5f1722f407c',
           'b6747e3a13d7991eb304f3db3fa8884e4cb5fd4d6b23d610247f2255f9df26f4'),
    'stable':('64e1a26e8225934639f7a265e3117f0733a6a7ca6ddb4489d7481d308a63d24b',
              'a0f5a99736429e07a839cf8b7c0ec2c67f5f19486600b714a924dc947b7ff9fd',
              '9ff50e1232b6c1a3e2478b9dfaa97ce223dddef58ed11fb6b088fdca22a856c1')}


def sha(value): return hashlib.sha256(value).hexdigest()


def pack_policy(pack):
    """New manifest/source contract, never the old reason pack_policy."""
    files=zip_files(pack);metadata=metadata_object(files[MANIFEST])
    mode=metadata.get('mode');require(type(mode) is str and mode in PINS,'Unknown reason math mode')
    exact_fields(metadata,dict(schema='aqualumen-water-snell-main-v1',observe='reasons',
        test_only=True,not_shipping=True,shipping_fix=False,parent_pack_sha256=PARENT_SHA,
        parent_helper_sha256=HELPER_SHA,geometry_factor=4,fixed_phase_seconds=120.0,
        old_shader_bytes_exact=mode=='old',runtime_accepted=False,physics_accepted=False,
        visual_accepted=False,shipping_accepted=False),'Wrong authoritative reason manifest')
    require(metadata.get('target_channels')==CHANNELS and metadata.get('declared_cap_rule')==[4,12],
        'Current C9 must be reasons and C12 must be TES')
    exact_fields(metadata.get('guard_uniform'),dict(name='aqualumenSunTestAuthorized',glsl_type='int',
        required_value=1,default_if_mod_absent=0),'Wrong scalar caller authorization')
    require(metadata.get('status0_policy')==metadata.get('statusMinus1_policy')=='Unchanged whole replacement rejection',
        'Inverse support/unknown may not bypass whole fallback')
    frozen_path=FROZEN/('Aqualumen-SnellMain-'+mode+'-reasons-v1.zip')
    require(sha(frozen_path.read_bytes())==PINS[mode][0],'Frozen current reason packet changed')
    frozen=zip_files(frozen_path)
    require(files[MANIFEST]==frozen[MANIFEST],'Current manifest differs from frozen reason policy')
    require(set(files)==set(frozen),'Unexpected/missing current reason members')
    require(all(value==frozen[name] for name,value in files.items()),'Changed frozen source or archive member')
    parent_path=ROOT/PARENT;require(sha(parent_path.read_bytes())==PARENT_SHA,'Frozen reason parent changed')
    parent=zip_files(parent_path)
    inherited=metadata_object(parent['WATER-RESIDUAL-SUN-REASONS.json'])
    require(inherited['fixed_texel_coordinates']==[list(p) for p in COORDINATES]
        and inherited['minimum_qualified_applied_points']==4 and inherited['loop_only'] is True
        and inherited['pre_or_post_loop_rejection_categorized'] is False,'Changed fixed inherited reason scope')
    helper,water=files[HELPER],files[WATER]
    require((sha(helper),sha(water))==PINS[mode][1:],'Actual helper/FS four-source pin differs')
    require((recover_helper(helper) if mode=='stable' else helper)==parent[HELPER],
        'Math source removal fails exact parent helper recovery')
    require(files['PARENT-SNELL-MAIN-reason-helper.glsl']==parent[HELPER]
        and files['PARENT-SNELL-MAIN-reason-water.fsh']==parent[WATER]
        and files['PARENT-SNELL-MAIN-physical.fsh']==parent['PARENT-SUN-REASONS-physical.fsh'],
        'Original physical/reason archives changed')
    require(files['SNELL-MAIN-reason-helper.glsl']==helper and files['SNELL-MAIN-reason-water.fsh']==water,
        'Current reason archives differ')
    original_water=water.replace(EXTENSION.encode(),b'',1) if mode=='stable' else water
    require(original_water==parent[WATER],'Main differs beyond explicit stable FP64 directive')
    require(water.decode().count(STORE)==1 and water.decode().replace(STORE,'').encode()
        ==files['SNELL-MAIN-physical.fsh'],'Reason STORE recovery differs from archived physical FS')
    for key,member in (('helper_sha256',HELPER),('observer_water_fs_sha256',WATER),
        ('physical_water_fs_sha256','SNELL-MAIN-physical.fsh'),
        ('reason_helper_sha256','SNELL-MAIN-reason-helper.glsl'),
        ('reason_water_fs_sha256','SNELL-MAIN-reason-water.fsh')):
        require(metadata.get(key)==sha(files[member]),'Current source digest differs')
    if mode=='stable':
        original=files['PARENT-SNELL-MAIN-node.glsl'];adapted=files[NODE]
        require(sha(original)==NODE_SHA and original.count(NODE_EXTENSION_GUARD.encode())==1
            and adapted==original.replace(NODE_EXTENSION_GUARD.encode(),b'',1),
            'Adapted FP64 module changed beyond exact extension guard removal')
        require(water.startswith(b'#version 330 compatibility\n'+EXTENSION.encode())
            and water.count(EXTENSION.encode())==1,'Required FP64 directive not immediately after version')
        exact_fields(metadata,dict(node_original_member='PARENT-SNELL-MAIN-node.glsl',
            node_original_sha256=NODE_SHA,node_adapted_member=NODE,node_adapted_sha256=sha(adapted)),
            'Actual stable module identity differs')
    return metadata


def audit(raw_file,pack,guard_raw):
    """Read-only FINAL/pack/independent prepared-guard public interface."""
    pack=Path(pack);metadata=pack_policy(pack)
    identity={**IDENTITY,'packName':pack.name,'packSha256':sha(pack.read_bytes())}
    guard=json_file(guard_raw);guard_observation(guard,identity)
    raw=json_file(raw_file);points=readback_points(raw,identity)
    for point in points: point['reasonTuple']=point.pop('coefficients')
    triples=set();requested=applied=loop_rejected=unclassified=0
    histogram={str(k):0 for k in range(1,10)};groups=dict(hemisphere=0,receiver=0,other=0)
    for point in points:
        qualify_point(point)
        first,*counts=point['reasonTuple'];status=point['sun_status']
        if first: histogram[str(int(first))]+=1
        requested+=status[0]==1;applied+=status[1]==1
        if sum(counts)>0:
            loop_rejected+=1
            for name,count in zip(groups,counts): groups[name]+=count
        elif status[3]>0: unclassified+=1
        if point['stage'][3]!=0: triples.add(tuple(round(v,4) for v in point['stage'][:3]))
    stage_points=sum(p['stage'][3]!=0 for p in points)
    require(stage_points>=4 and len(triples)>=2,'Vacuous/constant actual TES output')
    categories=dict(CATEGORIES)
    if metadata['mode']=='stable': categories['2']='inverse_node_status_rejection'
    verdict='QUALIFIED_SELECTED_APPLICATION' if applied>=4 else 'NEGATIVE_INSUFFICIENT_APPLICATION'
    return dict(schema='aqualumen-snell-main-reason-audit-v1',mode=metadata['mode'],
        selectedPoints=len(points),stagePresentPoints=stage_points,qualifiedAppliedPoints=applied,
        requestedPoints=requested,loopRejectedPoints=loop_rejected,unclassifiedRejectedPoints=unclassified,
        firstReasonHistogram=histogram,firstReasonCategories=categories,groupedRejectedNodes=groups,
        category2Scope=('Old float facet/facing/transmittedDot/discriminant compound gate' if metadata['mode']=='old'
            else 'Stable waterSnellNode status!=1 compound gate; status0 versus status-1 is NOT exported'),
        reasonEvidenceQualified=True,readbackQualified=True,guardUniformQualified=True,
        reasonGate='QUALIFIED_SELECTED_NODE_REASON_ACCOUNTING',operatorActiveQualified=applied>=4,
        applicationVerdict=verdict,minimumQualifiedAppliedPoints=4,distinctBarycentricTriples=len(triples),
        actualFourRoleBindingsQualified=True,sourceRecoveryQualified=True,
        packSha256=identity['packSha256'],guardFrame=guard['frameBefore'],finalSnapshotFrame=raw['snapshotFrame'],
        sourceSha256=dict(helper=metadata['helper_sha256'],observerWaterFS=metadata['observer_water_fs_sha256'],
            physicalWaterFS=metadata['physical_water_fs_sha256']),points=points,
        perCategoryNodeCountsObserved=False,sunUniformObserved=False,receiverGroupIsOpaqueProof=False,
        coefficientClosureObserved=False,physicalAccepted=False,pixelAAAccepted=False,
        visualAccepted=False,motionAccepted=False,performanceAccepted=False,shippingAccepted=False,
        sameFrameProven=False,drawIssuedProven=False,fragmentFetchProven=False,
        observerPassivityAccepted=False,geometryAccepted=False,nodeCountProven=False,
        energyAccepted=False,reciprocityAccepted=False,pngCausalityAccepted=False,
        GPUArithmeticCauseProven=False,all48NodeCausesObserved=False,
        scope='Separate prepared int1 guard and fixed16 FINAL first-node reason tuples. Loop-only first-category/group counts, not all48 causes or coefficients. Unclassified pre/post fallback remains distinct. No same-frame/draw/fetch, arithmetic cause, physics/AA/visual/shipping acceptance.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw',type=Path);parser.add_argument('pack',type=Path);parser.add_argument('guard_raw',type=Path)
    args=parser.parse_args()
    try: report=audit(args.raw,args.pack,args.guard_raw)
    except (OSError,ValueError,TypeError,KeyError,BadZipFile,RuntimeError,OverflowError,UnicodeError) as failure:
        parser.exit(1,'Rejected Snell main reason observation: '+type(failure).__name__+'\n')
    print(json.dumps(report,indent=2,sort_keys=True,allow_nan=False))
    if not report['operatorActiveQualified']: raise SystemExit(1)


if __name__=='__main__': main()
