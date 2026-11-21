"""CPU-only residual statistics/FINAL binding auditor; stdout only.

C9-C11 are NOT old normal/Fresnel/reflection fields. Readback qualification and
observed operator application are distinct; neither accepts physical energy,
reciprocity, per-node truth, geometry, images, performance or shipping.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from water_tessellation_runtime import NAMES, STATE_KEYS, require


CHANNELS = {'9':['mass','R','T','TIR'], '10':['valid','applied','minFacing','opaqueCount'],
            '11':['Cxx','Cxz','Czz','productionFlags'],
            '12':['barycentricX','barycentricY','barycentricZ','stagePresent']}
FLAGS = dict(known=1,upper=2,underwater=4,residualEligible=8)
FLAG_EXPRESSION = 'float(localColumnKnown)+2.0*float(upperSurface)+4.0*float(underwater)+8.0*float(residualEligible)'
HELPERS = ('shaders/lib/wave_residual.glsl','shaders/lib/water_residual.glsl')
FALSE_DECLARATIONS = ('shipping_fix','GL_neutrality_verified','runtime_accepted','visual_accepted',
    'performance_accepted','energy_accepted','reciprocity_accepted','generated_geometry_accepted',
    'motion_accepted','pack_enforces_world_guard','actual_shader_node_count_qualified',
    'parent_metadata_is_current_atlas_policy','inherited_metadata_is_current_atlas_policy',
    'parent_metadata_is_current_optical_policy')


def member(archive,name,maximum):
    entries=[e for e in archive.infolist() if e.filename==name]
    require(len(entries)==1 and entries[0].file_size<=maximum,'Ambiguous/oversized member')
    with archive.open(entries[0]) as stream: encoded=stream.read(maximum+1)
    require(len(encoded)<=maximum,'Oversized member')
    return encoded


def audit(raw_file,pack):
    raw_file,pack=Path(raw_file),Path(pack)
    require(pack.stat().st_size<=64*1024*1024,'Oversized pack')
    with ZipFile(pack) as archive:
        metadata=json.loads(member(archive,'WATER-RESIDUAL-OBSERVE.json',32768))
        require(type(metadata) is dict and metadata.get('schema')=='aqualumen-water-residual-observe-v1'
            and metadata.get('mode')=='residual-interface-observe','Wrong authoritative policy')
        require(metadata.get('test_only') is True and metadata.get('not_shipping') is True and
            all(metadata.get(k) is False for k in FALSE_DECLARATIONS),'Unaccepted boundaries required')
        require(type(metadata.get('geometry_factor')) is int and metadata['geometry_factor']==4 and
            type(metadata.get('quadrature_order')) is int and metadata['quadrature_order']==3 and
            type(metadata.get('fixed_phase_seconds')) in (int,float) and metadata['fixed_phase_seconds']==120,
            'Wrong geometry/phase/order declaration')
        require(metadata.get('target_channels')==CHANNELS and type(metadata.get('production_flags')) is dict and
            metadata['production_flags']==FLAGS and all(type(v) is int for v in metadata['production_flags'].values()) and
            type(metadata.get('production_flags_range')) is list and metadata['production_flags_range']==[0,15] and
            all(type(v) is int for v in metadata['production_flags_range']) and
            metadata.get('production_flags_expression')==FLAG_EXPRESSION,'Wrong residual roles/flags')
        require(type(metadata.get('parent_pack_sha256')) is str and
            re.fullmatch('[0-9a-f]{64}',metadata['parent_pack_sha256']) and
            metadata.get('parent_metadata_member')=='WATER-RESIDUAL-PROBE.json','Missing parent provenance')
        parent_bytes=member(archive,'WATER-RESIDUAL-PROBE.json',32768)
        require(hashlib.sha256(parent_bytes).hexdigest()==metadata.get('parent_metadata_sha256'),
                'Parent metadata digest mismatch')
        parent=json.loads(parent_bytes)
        require(type(parent) is dict and parent.get('schema')=='aqualumen-water-residual-probe-v1' and
            parent.get('mode')=='residual-interface-atlas' and
            type(metadata.get('helper_sha256')) is dict and set(metadata['helper_sha256'])==set(HELPERS)
            and metadata['helper_sha256']==parent.get('helper_sha256'),'Wrong helper/parent provenance')
        for name in HELPERS:
            require(hashlib.sha256(member(archive,name,262144)).hexdigest()==metadata['helper_sha256'][name],
                    'Helper bytes differ from declaration')
    with raw_file.open('rb') as stream: encoded=stream.read(1048577)
    require(len(encoded)<=1048576,'Oversized raw JSON')
    raw=json.loads(encoded)
    require(type(raw) is dict,'Raw capture must be an object')
    digest=hashlib.sha256()
    with pack.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''): digest.update(block)
    for key in ('available','stateRestored','scopeAuthorized'):
        require(raw.get(key) is True,'Unavailable or unauthorized capture')
    identity=dict(worldId='b22dbccb-2970-41e6-847f-f183b1ec923d',world='AqualumenNaturalV2',
        seed=308060,dimension='minecraft:overworld',observerVersion='0.3.9',
        packName=pack.name,packSha256=digest.hexdigest(),width=1600,height=900)
    require(all(raw.get(k)==v and type(raw.get(k)) is type(v) for k,v in identity.items()),'Wrong identity/scope')
    require(type(raw.get('renderer')) is str and 'NVIDIA' in raw['renderer'],'NVIDIA capture required')
    require(type(raw.get('program')) is int and raw['program']>0 and
        type(raw.get('expectedProgram')) is int and raw['program']==raw['expectedProgram'],'Wrong FINAL program')
    before,after=raw.get('stateBefore'),raw.get('stateAfter')
    require(type(before) is dict and type(after) is dict and set(before)==STATE_KEYS and
            all(type(v) is int for v in before.values()) and all(type(v) is int for v in after.values()) and before==after,
            'GL state not restored')
    samplers=raw.get('samplers')
    require(type(samplers) is list and len(samplers)==4 and all(type(s) is dict for s in samplers)
        and {s.get('name') for s in samplers}==set(NAMES),'Expected exactly C9-C12')
    require(len({s.get('unit') for s in samplers})==4 and len({s.get('textureId') for s in samplers})==4,
            'Aliased bindings')
    by_name={s['name']:s for s in samplers};coordinates=None
    for sampler in samplers:
        required=dict(type=35678,size=1,actualFormat=34836,width=1600,height=900)
        require(sampler.get('active') is True and sampler.get('textureExists') is True and
            all(type(sampler.get(k)) is int and sampler[k]==v for k,v in required.items()) and
            all(type(sampler.get(k)) is int and sampler[k]>=0 for k in ('location','unit')) and
            type(sampler.get('textureId')) is int and sampler['textureId']>0,'Wrong typed storage/binding')
        points=sampler.get('samples');require(type(points) is list and len(points)==16,'Expected sixteen texels')
        current=[]
        for point in points:
            require(type(point) is dict and type(point.get('x')) is int and type(point.get('y')) is int and
                0<=point['x']<1600 and 0<=point['y']<900,'Invalid texel coordinate')
            values=point.get('rgba')
            require(type(values) is list and len(values)==4 and
                all(type(v) in (int,float) and math.isfinite(v) for v in values),'Invalid finite RGBA')
            current.append((point['x'],point['y']))
        require(len(set(current))==16 and (coordinates is None or coordinates==current),'Repeated/mismatched texels')
        coordinates=current
        entries=raw.get('samplerMetadata');require(type(entries) is list and all(type(e) is dict for e in entries),
            'Missing readback bounds')
        matched=[e for e in entries if e.get('unit')==sampler['unit'] and e.get('textureId')==sampler['textureId']]
        require(len(matched)==1 and matched[0].get('wholeTargetReadbackBytes')==1600*900*16 and
            matched[0].get('exportedTexelCount')==16,'Wrong readback bounds')
    points=[];stage_points=0;triples=set();active_points=[];max_mass_error=0.;max_balance_error=0.
    for i,coordinate in enumerate(coordinates):
        coefficient,status,covariance,stage=[by_name[name]['samples'][i]['rgba'] for name in NAMES]
        flags=covariance[3]
        require(flags==int(flags) and 0<=flags<=15,'Invalid production bitword')
        flags=int(flags);require(not flags&8 or flags&7==7,'Hook eligibility lacks required domain bits')
        require(status[0] in (0,1) and status[1] in (0,1) and status[3]>=0 and status[3]==int(status[3]),
                'Invalid operator status')
        if stage==[0,0,0,0]:
            require(flags==0 and status[1]==0,'Nonwater point claims eligible/applied')
        else:
            require(abs(stage[3]-1)<=8*2**-23 and all(-2e-5<=v<=1+2e-5 for v in stage[:3])
                and abs(sum(stage[:3])-1)<=2e-5,'Invalid TES stage/simplex')
            stage_points+=1;triples.add(tuple(round(v,4) for v in stage[:3]))
        applied=status[1]==1
        if applied:
            require(flags==15 and status[0]==1 and status[2]>0 and status[3]==0 and stage!=[0,0,0,0],
                    'Applied operator lacks domain/validity')
            mass,R,T,tir=coefficient;xx,xz,zz=covariance[:3]
            require(xx>=0 and zz>=0 and xx*zz-xz*xz>=0,'Applied covariance not PSD')
            require(abs(mass-1)<=2e-5 and min(R,T,tir)>=0 and R<=mass+2e-5 and tir<=R+2e-5
                and abs(R+T-mass)<=2e-5,'Applied coefficients inconsistent')
            max_mass_error=max(max_mass_error,abs(mass-1));max_balance_error=max(max_balance_error,abs(R+T-mass))
            active_points.append(i)
        points.append(dict(x=coordinate[0],y=coordinate[1],productionFlags=flags,
            known=bool(flags&1),upper=bool(flags&2),underwater=bool(flags&4),eligible=bool(flags&8),
            applied=applied,operatorStatisticsQualified=applied))
    require(stage_points>=4 and len(triples)>=2,'Vacuous TES output')
    return dict(readbackQualified=True,operatorActiveQualified=bool(active_points),
        operatorActivePoints=len(active_points),operatorActivePointIndices=active_points,
        inactivePoints=16-len(active_points),inactiveStatisticsQualified=False,
        stagePresentPoints=stage_points,distinctBarycentricTriples=len(triples),points=points,
        maximumAppliedMassError=max_mass_error,maximumAppliedCoefficientBalanceError=max_balance_error,
        actualFourRoleBindingsQualified=True,actualProductionFlagsQualified=True,
        declaredGeometryFactor=4,declaredFixedPhaseSeconds=120,declaredQuadratureOrder=3,
        parentPackSha256Declared=metadata['parent_pack_sha256'],packSha256=digest.hexdigest(),
        nodeCountProven=False,physicalEnergyAccepted=False,reciprocityAccepted=False,
        geometryAccepted=False,stageAttachmentQueryObserved=False,drawCountAccepted=False,
        shippingAccepted=False,visualQualityAccepted=False,pngSameFrameAccepted=False,
        pngCausalityAccepted=False,motionAccepted=False,performanceAccepted=False,fpsFloorAccepted=False,
        frameCounterBeforeAfterProven=False,sourceClassMassReadbackProven=False,
        scope='Selected unfiltered FINAL-bound residual statistics and actual production eligibility flags; no per-node physical oracle or image acceptance')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw',type=Path);parser.add_argument('pack',type=Path);args=parser.parse_args()
    try: result=audit(args.raw,args.pack)
    except (OSError,ValueError,TypeError,KeyError,BadZipFile,RuntimeError,OverflowError) as failure:
        parser.exit(1,'Rejected residual observation: '+type(failure).__name__+'\n')
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=='__main__': main()
