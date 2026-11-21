"""Saved actual WNS telemetry qualification, not physical or pixel-AA adoption."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from water_tessellation_runtime import NAMES, STATE_KEYS, require
from water_residual_sun_iris_pack import (CAP_RELATIVE,CAP_SHA256,SUN_SHA256,OLD_CALL,
    UNIFORM,GUARDED_CALL,FLAGS,STORE,PARENT_PANELS,PANELS)

CHANNELS={'9':['mass','R','T','TIR'],'10':['requested','featureApplied','sourceKind','rejectionCount'],
          '11':['Cxx','Cxz','Czz','productionFlags'],
          '12':['barycentricX','barycentricY','barycentricZ','stagePresent']}
IDENTITY=dict(worldId='b22dbccb-2970-41e6-847f-f183b1ec923d',world='AqualumenNaturalV2',
              seed=308060,dimension='minecraft:overworld')
VERSIONS=dict(aqualumen_water_sun_test='0.1.0',aqualumen_benchmark='0.3.9',
              aqualumen_physics='0.3.0',iris='1.8.8',sodium='0.6.9',minecraft='1.21.1')
COORDINATES=((801,451),(401,451),(1201,451),(801,251),(33,451),(65,451),(129,451),(193,451),
             (1409,451),(1473,451),(1537,451),(1567,451),(129,129),(1473,129),(129,771),(1473,771))


def exact_fields(value,expected,message):
    require(type(value) is dict and all(type(value.get(k)) is type(v) and value[k]==v
                                       for k,v in expected.items()),message)


def json_file(path):
    with Path(path).open('rb') as stream: encoded=stream.read(1048577)
    require(len(encoded)<=1048576,'Oversized observation')
    def unique(pairs):
        result={}
        for key,value in pairs:
            require(key not in result,'Duplicate JSON key');result[key]=value
        return result
    value=json.loads(encoded,object_pairs_hook=unique)
    require(type(value) is dict,'Observation object required')
    return value


def zip_files(path):
    require(Path(path).stat().st_size<=64*1024*1024,'Oversized ZIP')
    with ZipFile(path) as archive:
        entries=archive.infolist()
        require(len(entries)<=1024 and len({e.filename for e in entries})==len(entries)
                and sum(e.file_size for e in entries)<=64*1024*1024,'Ambiguous/oversized ZIP')
        return {e.filename:archive.read(e) for e in entries}


def pack_policy(pack):
    files=zip_files(pack)
    require(len(files['WATER-RESIDUAL-SUN-IRIS.json'])<=32768,'Oversized metadata')
    metadata=json.loads(files['WATER-RESIDUAL-SUN-IRIS.json'])
    exact_fields(metadata,dict(schema='aqualumen-water-residual-sun-iris-v1',mode='guarded-native-sun-observe',
        test_only=True,not_shipping=True,parent_cap_pack_sha256=CAP_SHA256,geometry_factor=4,
        fixed_phase_seconds=120.0,world_guard_requires_mod=True,shader_authorization_gate_present=True),
        'Wrong authoritative Sun policy')
    for key in ('shipping_fix','pack_enforces_world_guard','actual_guard_runtime_verified','runtime_accepted',
        'GL_neutrality_verified','pixel_AA_equivalence_accepted','energy_accepted','reciprocity_accepted',
        'visual_accepted','performance_accepted','generated_geometry_accepted','motion_accepted',
        'actual_shader_node_count_qualified','inherited_metadata_is_current_optical_policy',
        'inherited_metadata_is_current_atlas_policy','geometry_source_changed','cap_helper_source_changed',
        'atmosphere_source_changed','scalar_units_changed','scatter_policy_changed','FS_C0_source_observation_changed'):
        require(metadata.get(key) is False,'Unaccepted boundary must remain false')
    enabled=metadata.get('enabled');require(type(enabled) is int and enabled in (0,1),'Invalid enabled mode')
    require(metadata.get('target_channels')==CHANNELS and metadata.get('production_flags_expression')==FLAGS
        and metadata.get('production_flags_range')==[0,15] and metadata.get('declared_cap_rule')==[4,12],
        'Wrong channel/flag/rule policy')
    exact_fields(metadata.get('production_flags'),dict(known=1,upper=2,underwater=4,residualEligible=8),'Wrong flag types')
    exact_fields(metadata.get('guard_uniform'),dict(name='aqualumenSunTestAuthorized',glsl_type='int',
        required_value=1,default_if_mod_absent=0),'Wrong guard declaration')
    require(metadata.get('guard_call_expression')=='if (aqualumenSunTestAuthorized==1)','Wrong caller guard')
    parent_path=Path(__file__).resolve().parents[1]/CAP_RELATIVE
    require(hashlib.sha256(parent_path.read_bytes()).hexdigest()==CAP_SHA256,'Frozen CAP changed')
    parent=zip_files(parent_path)
    extra={'PARENT-SUN-IRIS-physical.fsh','PARENT-SUN-IRIS-final.fsh',
           'WATER-RESIDUAL-SUN-IRIS.json','WATER-RESIDUAL-SUN-IRIS.txt'}
    require(set(files)==set(parent)|extra,'Unexpected/missing source members')
    for name,content in parent.items():
        if name not in ('shaders/gbuffers_water.fsh','shaders/final.fsh'):
            require(files[name]==content,'Changed parent helper/geometry/archive')
    parent_metadata=parent['WATER-RESIDUAL-SUN-CAP.json']
    require(metadata.get('parent_cap_metadata_member')=='WATER-RESIDUAL-SUN-CAP.json'
        and metadata.get('parent_cap_metadata_sha256')==hashlib.sha256(parent_metadata).hexdigest(),
        'Parent metadata hash mismatch')
    parent_policy=json.loads(parent_metadata)
    require(metadata.get('original_sha256')==parent_policy['original_sha256'],'Original provenance changed')
    helpers={'shaders/lib/water_residual_sun.glsl':SUN_SHA256,**parent_policy['old_helper_sha256']}
    require(metadata.get('helper_sha256')==helpers,'Wrong pinned helpers')
    for name,digest in helpers.items():
        require(hashlib.sha256(files[name]).hexdigest()==digest,'Helper digest mismatch')
    water=files['shaders/gbuffers_water.fsh'].decode()
    physical=files['PARENT-SUN-IRIS-physical.fsh'].decode()
    config=('// AQUALUMEN_SUN_IRIS_CONFIG_BEGIN\n#define NATIVE_SUN_ENABLED '+str(enabled)+
            '\n// AQUALUMEN_SUN_IRIS_CONFIG_END\n')
    require(water.count(STORE)==1 and water.replace(STORE,'')==physical,'Observer removal not exact physical FS')
    require(all(physical.count(s)==1 for s in (UNIFORM,config,GUARDED_CALL)) and
        physical.replace(UNIFORM,'').replace(config,'').replace(GUARDED_CALL,OLD_CALL).encode()
        ==parent['shaders/gbuffers_water.fsh'],'Disabled/guard removal not exact CAP FS')
    for field,name in (('physical_water_fs_sha256','PARENT-SUN-IRIS-physical.fsh'),
        ('observer_water_fs_sha256','shaders/gbuffers_water.fsh'),('parent_final_sha256','PARENT-SUN-IRIS-final.fsh')):
        require(metadata.get(field)==hashlib.sha256(files[name]).hexdigest(),'FS provenance mismatch')
    require(metadata.get('physical_water_fs_member')=='PARENT-SUN-IRIS-physical.fsh'
        and metadata.get('parent_final_member')=='PARENT-SUN-IRIS-final.fsh'
        and metadata.get('parent_water_fs_sha256')==hashlib.sha256(parent['shaders/gbuffers_water.fsh']).hexdigest(),
        'Wrong parent source member/hash')
    require(files['PARENT-SUN-IRIS-final.fsh']==parent['shaders/final.fsh'] and
        files['shaders/final.fsh']==parent['shaders/final.fsh'].decode().replace(PARENT_PANELS,PANELS).encode(),
        'FINAL does not consume declared roles')
    return enabled


def guard_observation(guard,identity):
    exact_fields(guard,{**identity,'schema':'aqualumen-sun-guard-observation-v1','observerVersion':'0.1.0',
        'available':True,'readOnly':True,'scopeAuthorized':True,'localIntegratedSinglePlayer':True,
        'currentPipelineMatches':True,'containsTessellation':True,'pass':'TRANSLUCENT',
        'scope':'prepared-current-translucent-int-uniform','supplierAuthorization':1,
        'programAndFrameUnchanged':True,'seam':'SodiumShader.updateUniforms TAIL',
        'registrationPath':'CommonUniforms.addDynamicUniforms TAIL uniform1i PER_FRAME',
        'supplierPath':'SunAuthorization.value(runtime(game)) fresh each invocation; no cache/latch'},'Wrong prepared guard observation')
    require(guard.get('benchmarkState') in ('idle','complete','aborted'),'Guard measured during timing')
    for key in ('errorFlagConsumed','drawIssuedProven','fragmentFetchProven','WNSApplicationProven',
                'pngSameFrameProven','allGLStateUnchangedProven'):
        require(guard.get(key) is False,'Guard cannot declare unobserved proof')
    versions=guard.get('versions');require(type(versions) is dict and set(versions)==set(VERSIONS),'Missing versions')
    require(all(type(versions[k]) is str and (versions[k]==v or versions[k].startswith(v+'+'))
                for k,v in VERSIONS.items()),'Wrong pinned versions')
    require(all(type(guard.get(k)) is int and guard[k]>0 for k in ('constructorProgram','programBefore','programAfter'))
        and guard['constructorProgram']==guard['programBefore']==guard['programAfter'],'Guard program changed')
    require(type(guard.get('frameBefore')) is int and guard['frameBefore']>=0 and
        type(guard.get('frameAfter')) is int and guard['frameBefore']==guard['frameAfter'],'Guard frame changed')
    uniform=guard.get('uniform')
    exact_fields(uniform,dict(name='aqualumenSunTestAuthorized',active=True,type=5124,size=1,value=1),
                 'Wrong active scalar integer authorization')
    require(type(uniform.get('location')) is int and uniform['location']>=0,'Inactive guard uniform')


def readback_points(raw,identity):
    # Generic Shore capture has no schema field. Snapshot.capture overwrites
    # the wrapper's preliminary DEBUG-shore-runtime tag via result.putAll.
    exact_fields(raw,{**identity,'observerVersion':'0.3.9','width':1600,'height':900,
        'available':True,'stateRestored':True,'scopeAuthorized':True,'tag':'DEBUG-shore-sampler',
        'seam':'FinalPassRenderer.renderFinalPass before FullScreenQuadRenderer.renderQuad; after Program.use and CustomUniforms.push',
        'rawReadPolicy':'GL3.2 glGetTexImage level0, bounded reusable whole-target scratch; only selected texels exported',
        'samplingInterpretation':'unfiltered level-zero texels, not tone-mapped or reconstructed FINAL texture() values',
        'texelCoordinateConvention':'integer level-zero texture coordinates; bottom-left origin',
        'maximumSelectedTexels':16,'selectedTexelsFiniteOnly':True,'timingAcceptanceExcluded':True},'Wrong FINAL identity/protocol/scope')
    require(type(raw.get('renderer')) is str and 'NVIDIA' in raw['renderer'],'NVIDIA capture required')
    require(type(raw.get('snapshotFrame')) is int and raw['snapshotFrame']>=0,'Missing actual FINAL frame')
    require(type(raw.get('program')) is int and raw['program']>0 and type(raw.get('expectedProgram')) is int
        and raw['program']==raw['expectedProgram'],'Wrong FINAL program')
    before,after=raw.get('stateBefore'),raw.get('stateAfter')
    require(type(before) is dict and type(after) is dict and set(before)==set(after)==STATE_KEYS
        and all(type(v) is int for v in [*before.values(),*after.values()]) and before==after,'Unrestored typed state')
    descriptors=raw.get('samplers');require(type(descriptors) is list and 4<=len(descriptors)<=7
        and all(type(s) is dict for s in descriptors),'Wrong bounded descriptors')
    samplers,extras=descriptors[:4],descriptors[4:]
    require(tuple(s.get('name') for s in samplers)==NAMES,'Wrong primary sampler role order')
    require(all(set(s)=={'name','active','reason'} and s.get('name') in ('colortex13','colortex14','colortex15')
        and s.get('active') is False and s.get('reason')=='inactive_uniform' for s in extras)
        and len({s['name'] for s in extras})==len(extras),'Unapproved inactive extras')
    require(len({s.get('unit') for s in samplers})==len({s.get('textureId') for s in samplers})==4,'Aliased bindings')
    bounds=raw.get('samplerMetadata');require(type(bounds) is list and len(bounds)==4
        and all(type(s) is dict for s in bounds),'Wrong readback metadata')
    coordinates=None;by_name={s['name']:s for s in samplers}
    for sampler in samplers:
        exact_fields(sampler,dict(active=True,textureExists=True,type=35678,size=1,actualFormat=34836,width=1600,height=900),
                     'Wrong typed sampler/storage')
        require(all(type(sampler.get(k)) is int and sampler[k]>=0 for k in ('location','unit'))
            and type(sampler.get('textureId')) is int and sampler['textureId']>0,'Invalid binding')
        samples=sampler.get('samples');require(type(samples) is list and len(samples)==16,'Exactly sixteen selected texels required')
        current=[]
        for p in samples:
            require(type(p) is dict and type(p.get('x')) is int and type(p.get('y')) is int
                and 0<=p['x']<1600 and 0<=p['y']<900,'Invalid texel coordinate')
            values=p.get('rgba');require(type(values) is list and len(values)==4 and
                all(type(v) in (int,float) and math.isfinite(v) for v in values),'Invalid finite RGBA')
            current.append((p['x'],p['y']))
        require(len(set(current))==16 and (coordinates is None or coordinates==current),'Repeated/mismatched coordinates')
        require(tuple(current)==COORDINATES,'Coordinates differ from predeclared sixteen-point policy')
        coordinates=current
        matches=[s for s in bounds if s.get('unit')==sampler['unit'] and s.get('textureId')==sampler['textureId']]
        require(len(matches)==1,'Missing/ambiguous readback bounds')
        exact_fields(matches[0],dict(unit=sampler['unit'],textureId=sampler['textureId'],
            wholeTargetReadbackBytes=1600*900*16,exportedTexelCount=16),'Wrong readback bounds')
    return [dict(x=x,y=y,**{field:by_name[name]['samples'][i]['rgba'] for field,name in
        zip(('coefficients','sun_status','covariance_flags','stage'),NAMES)}) for i,(x,y) in enumerate(coordinates)]


def audit(raw_file,pack,guard_raw_file):
    """Read-only saved FINAL and independent prepared-uniform observations."""
    pack=Path(pack);enabled=pack_policy(pack)
    identity={**IDENTITY,'packName':pack.name,'packSha256':hashlib.sha256(pack.read_bytes()).hexdigest()}
    guard= json_file(guard_raw_file);guard_observation(guard,identity)
    raw=json_file(raw_file);points=readback_points(raw,identity)
    triples=set();stage_count=0
    for p in points:
        flags=p['covariance_flags'][3];stage=p['stage']
        require(flags==int(flags) and 0<=flags<=15,'Invalid production flags')
        flags=int(flags);require(not flags&8 or flags&7==7,'Eligibility lacks actual domain')
        if stage==[0,0,0,0]:
            require(flags==0 and p['sun_status']==[0,0,0,0],'Nonwater claims domain/application')
        else:
            require(abs(stage[3]-1)<=8*2**-23 and all(-2e-5<=x<=1+2e-5 for x in stage[:3])
                and abs(sum(stage[:3])-1)<=2e-5,'Invalid TES stage/simplex')
            stage_count+=1;triples.add(tuple(round(x,4) for x in stage[:3]))
    require(stage_count>=4 and len(triples)>=2,'Vacuous/constant TES output')
    report=qualify_texels(points,enabled,authorized=1)
    verdict=('DISABLED_CONTROL' if enabled==0 else 'QUALIFIED_SELECTED_APPLICATION'
             if report['qualifiedAppliedPoints']>=4 else 'NEGATIVE_INSUFFICIENT_APPLICATION')
    report.update(readbackQualified=True,guardUniformQualified=True,
        operatorActiveQualified=report['qualifiedAppliedPoints']>=4,enabled=enabled,
        applicationVerdict=verdict,minimumQualifiedAppliedPoints=4,
        distinctBarycentricTriples=len(triples),
        packSha256=identity['packSha256'],guardFrame=guard['frameBefore'],finalSnapshotFrame=raw.get('snapshotFrame'),
        actualFourRoleBindingsQualified=True,sourceRecoveryQualified=True,
        sameFrameProven=False,drawIssuedProven=False,fragmentFetchProven=False,
        observerPassivityAccepted=False,geometryAccepted=False,nodeCountProven=False,
        reciprocityAccepted=False,energyAccepted=False,pngCausalityAccepted=False,
        narrowCovarianceAccepted=False,rimVisibilityCriticalAccepted=False,
        scope='Separate saved prepared int1 guard and selected FINAL WNS telemetry; no same-frame/draw/fetch or physics/AA acceptance')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw',type=Path);parser.add_argument('pack',type=Path);parser.add_argument('guard_raw',type=Path)
    args=parser.parse_args()
    try: report=audit(args.raw,args.pack,args.guard_raw)
    except (OSError,ValueError,TypeError,KeyError,BadZipFile,RuntimeError,OverflowError,UnicodeError) as failure:
        parser.exit(1,'Rejected Sun observation: '+type(failure).__name__+'\n')
    print(json.dumps(report,indent=2,sort_keys=True))
    if report['applicationVerdict']=='NEGATIVE_INSUFFICIENT_APPLICATION':
        raise SystemExit(1)


def qualify_texels(points,enabled,authorized):
    """Public selected readback seam; WNS status is not legacy WR status.

    Bindings/source/guard identity are a separate file-audit responsibility.
    Inactive or rejected statistics do not establish the new operator domain.
    """
    requested=applied=rejected=stage_points=0
    for point in points:
        for field in ('sun_status','covariance_flags','coefficients','stage'):
            values=point[field]
            if (type(values) is not list or len(values)!=4
                    or any(type(v) not in (int,float) or not math.isfinite(v) for v in values)):
                raise ValueError('Finite four-component telemetry required')
        status=point['sun_status']
        if (status[0] not in (0,1) or status[1] not in (0,1) or status[2]!=0
                or status[3]<0 or status[3]!=int(status[3]) or (status[1]==1 and status[3]!=0)):
            raise ValueError('Malformed native requested/applied/kind/rejection telemetry')
        if status[0]==1 and (authorized!=1 or enabled!=1):
            raise ValueError('Requested Sun lacks current authorization/enabled mode')
        if status[1]==1 and (authorized!=1 or enabled!=1 or status[0]!=1):
            raise ValueError('Applied Sun lacks current authorization/enabled request')
        if status[1]==1:
            xx,xz,zz,flags=point['covariance_flags']
            if flags!=15 or xx<=0 or zz<=0 or xx*zz-xz*xz<=0:
                raise ValueError('Applied Sun lacks original water domain or strict covariance')
            mass,reflection,transmission,tir=point['coefficients']
            stage=point['stage']
            if (abs(mass-1)>2e-5 or min(reflection,transmission,tir)<0
                    or tir>reflection+2e-5 or abs(reflection+transmission-mass)>2e-5
                    or abs(stage[3]-1)>8*2**-23 or abs(sum(stage[:3])-1)>2e-5
                    or any(x < -2e-5 or x > 1+2e-5 for x in stage[:3])):
                raise ValueError('Applied Sun lacks qualified legacy coefficients or actual TES')
        requested+=status[0]==1
        applied+=status[1]==1
        rejected+=status[3]>0
        stage_points+=point['stage'][3]!=0
    return dict(selectedPoints=len(points),requestedPoints=requested,
                qualifiedAppliedPoints=applied,rejectedPoints=rejected,
                stagePresentPoints=stage_points,physicalAccepted=False,
                pixelAAAccepted=False,visualAccepted=False,motionAccepted=False,
                performanceAccepted=False,shippingAccepted=False,
                scope='Selected WNS telemetry only; not source integration, pixel filtering or model acceptance')


if __name__=='__main__': main()
