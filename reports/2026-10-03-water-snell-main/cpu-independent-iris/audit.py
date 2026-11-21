"""CPU replay of four actual Iris saved captures; no renderer or world writes."""
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import water_snell_main_runtime as inputs_api
import water_snell_main_reason_runtime as reasons_api
from water_residual_sun_iris_runtime import json_file,zip_files,exact_fields,IDENTITY
from report import check_png,metrics,validate_underwater_up
from test_thin_runtime_audit import read_intervals

PINS={'water_snell_main_runtime.py':'dc1fabf8706821f7f9a5e813bdfd45c2092a6317841ed09ffafd2237860f5ad8',
    'water_snell_main_reason_runtime.py':'e0f3bee7e1d8e0d7113772875595e60c34fcf9c8b512cc161c5170a16b60478b',
    'water_snell_boundary_reference.py':'511770d7c090a8ea5423cb7afd30dd655a2a09253c10f27ef0921215ba0bc9e0'}
MODES=('old','stable');ROLES=('reasons','inputs')


def require(value,message):
    if not value: raise ValueError(message)


def sha(value): return hashlib.sha256(value).hexdigest()


def time(value):
    # Retained nanoseconds are not invented; datetime only orders captures.
    return datetime.fromisoformat(value.replace('Z','+00:00'))


def bits(values): return [struct.pack('<f',v).hex() for v in values]


def stage_observation(stage,identity):
    exact_fields(stage,{**IDENTITY,'schema':'aqualumen-water-stage-observation-v1',
        'available':True,'scope':'terrain-tessellation-stages','observerVersion':'0.1.0',
        'expectedPack':identity['packName'],'expectedPackSha256':identity['packSha256'],
        'readOnly':True,'errorFlagConsumed':False,'localIntegratedSinglePlayer':True,
        'scopeAccepted':True,'currentPipelineMatches':True,'benchmarkState':'complete',
        'afterSetupStateTail':True,'pass':'TRANSLUCENT','constructorContainsTessellation':True,
        'usingTessellationAtAdmission':True,'sourceHashesRequested':True,'linkStatus':1,
        'attachedShaderCount':4,'tessControlOutputVertices':3,'patchVertices':3,
        'tesSourceMarkerPresent':True,'programAndFrameUnchanged':True},'Wrong attached-stage scope')
    require(stage['constructorProgram']==stage['programBefore']==stage['programAfter']>0
        and stage['frameBefore']==stage['frameAfter']>=0,'Stage program/frame changed')
    require(stage['capabilities']['GL_ARB_tessellation_shader'] is True and
        'NVIDIA' in stage['capabilities']['renderer'],'Actual tessellation capability')
    require(sorted(s['type'] for s in stage['stages'])==[35632,35633,36487,36488]
        and len({s['shader'] for s in stage['stages']})==4 and
        all(type(s['sourceBytes']) is int and 0<s['sourceBytes']<=256*1024
            and len(s['sourceSha256'])==64 for s in stage['stages']),'Typed four-stage source hashes')
    for key in ('drawIssuedProven','tessInvocationCountProven','fragmentValueFetchProven',
            'exclusiveWaterProgramProven','nativeOrNaturalAppearanceAccepted'):
        require(stage[key] is False,'Unobserved stage proof')
    return {str(s['type']):{'bytes':s['sourceBytes'],'sha256':s['sourceSha256']} for s in stage['stages']}


def audit(packet,shaderpacks):
    packet=Path(packet).resolve();shaderpacks=Path(shaderpacks)
    for name,digest in PINS.items(): require(sha((ROOT/'tools'/name).read_bytes())==digest,'Frozen public source changed')
    reports={};raws={};packs={};manifest={}
    for mode in MODES:
        for role in ROLES:
            key=mode+'-'+role;directory=packet/('iris-'+key)
            pack=shaderpacks/('Aqualumen-ShoreProbe-world-snell-main-'+key+'-v1.zip')
            exported=packet/'cpu-pack'/('Aqualumen-SnellMain-'+key+'-v1.zip')
            require(pack.read_bytes()==exported.read_bytes(),'Actual installed alias differs from frozen exported ZIP')
            packs[key]=zip_files(pack)
            api=reasons_api if role=='reasons' else inputs_api
            recalculated=api.audit(directory/'final-raw.json',pack,directory/'guard-raw.json')
            expected=(json.dumps(recalculated,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
            root_result=directory/('reason-audit.json' if role=='reasons' else 'input-audit.json')
            require(root_result.read_bytes()==expected,'Public replay does not byte-match root audit JSON')
            raw=json_file(directory/'final-raw.json');guard=json_file(directory/'guard-raw.json')
            identity={**IDENTITY,'packName':pack.name,'packSha256':sha(pack.read_bytes())}
            stage=json_file(directory/'stage-raw.json');stages=stage_observation(stage,identity)
            require(stage['versions']['aqualumen_benchmark']=='0.3.9' and
                stage['versions']['aqualumen_physics']=='0.3.0','Stage version pins')
            require(stage['constructorProgram']==guard['constructorProgram'],'Guard/stage pipeline program mismatch')
            run_dir=directory/'run';run=json_file(run_dir/'run.json');complete=json_file(run_dir/'complete.json')
            scene=json_file(run_dir/'underwater-up-near.json')
            for value in (run,scene):
                exact_fields(value,dict(world_id=IDENTITY['worldId'],seed=IDENTITY['seed']) if value is run else
                    dict(world_id=IDENTITY['worldId']), 'Wrong fixed world')
                exact_fields(value,dict(pack_name=pack.name,pack_sha256=identity['packSha256'],
                    shader_active=True,shader_fallback=False,resolution=[1600,900],framebuffer_resolution=[1600,900],
                    player_dimension='minecraft:overworld'),'Wrong actual shader/storage/dimension')
            exact_fields(run,dict(scenarios=['underwater-up-near'],warmup_seconds=10.0,sample_seconds=5.0,
                frame_limit=120,vsync=False,render_chunks=12,simulation_chunks=6),'Changed warmed-view controls')
            require(run['mods']['aqualumen_benchmark']=='0.3.9' and run['mods']['aqualumen_physics']=='0.3.0',
                'Run version pins')
            exact_fields(complete,dict(status='complete',scenarios=['underwater-up-near'],fixture_cleanup_complete=True),
                'Incomplete capture/cleanup')
            require(run['run_id']==scene['run_id']==complete['run_id'] and scene['window_focused'] is True
                and scene['camera_follows_local_player'] is True and scene['physics_active_seen'] is True,'Run/focus/local actor')
            validate_underwater_up(scene,'underwater-up-near')
            check_png(run_dir/'underwater-up-near.png',(1600,900))
            ns,ms=read_intervals(run_dir/'underwater-up-near.csv');calculated=metrics(ms)
            for name,value in calculated.items():
                require(scene[name]==value if type(value) is int else math.isclose(scene[name],value,rel_tol=1e-12,abs_tol=1e-9),
                    'Raw integer-ns metric differs: '+name)
            require(time(complete['utc'])<time(raw['utc']) and time(complete['utc'])<time(guard['capturedUtc'])
                and time(complete['utc'])<time(stage['capturedUtc']),'Observer not after measurement complete')
            require(raw['unshiftedCameraPosition']==scene['actual_camera_position'],'Held raw-camera pose differs from measured camera')
            for name in ('gbuffers_water.vsh','gbuffers_water.tcs','gbuffers_water.tes'):
                require(packs[key]['shaders/'+name]==packs['old-reasons']['shaders/'+name], 'Archive geometry changed')
            geometry={k:v for k,v in stages.items() if k!='35632'}
            if reports: require(geometry==reports['old-reasons']['actualGeometryStageHashes'],'Post-Iris geometry hashes changed')
            if role=='reasons': require(recalculated['qualifiedAppliedPoints']==2 and
                recalculated['minimumQualifiedAppliedPoints']==4 and
                recalculated['applicationVerdict']=='NEGATIVE_INSUFFICIENT_APPLICATION','Application gate cannot be relaxed')
            raws[key]=raw
            reports[key]=dict(publicAuditSha256=sha(expected),packSha256=identity['packSha256'],
                selectedPoints=recalculated['selectedPoints'],firstReasonHistogram=recalculated['firstReasonHistogram'],
                applicationVerdict=recalculated.get('applicationVerdict','NOT_OBSERVED_INPUT_ROLE'),
                qualifiedAppliedPoints=recalculated.get('qualifiedAppliedPoints'),
                referenceClassifications=recalculated.get('referenceClassifications'),
                actualGeometryStageHashes=geometry,actualFragmentStageHash=stages['35632'],
                guardFrame=guard['frameBefore'],stageFrame=stage['frameBefore'],finalFrame=raw['snapshotFrame'],
                frameTimeCounter=raw['frameTimeCounter'],cameraPosition=raw['unshiftedCameraPosition'],
                metrics=calculated,rawNanosecondsTotal=sum(ns),actualEyeDepth=scene['underwater_up']['actual_eye_depth'])
            for path in directory.rglob('*'):
                if path.is_file(): manifest[str(path.relative_to(packet))]=sha(path.read_bytes())
    comparisons=[]
    old=inputs_api.audit(packet/'iris-old-inputs/final-raw.json',shaderpacks/'Aqualumen-ShoreProbe-world-snell-main-old-inputs-v1.zip',packet/'iris-old-inputs/guard-raw.json')['points']
    stable=inputs_api.audit(packet/'iris-stable-inputs/final-raw.json',shaderpacks/'Aqualumen-ShoreProbe-world-snell-main-stable-inputs-v1.zip',packet/'iris-stable-inputs/guard-raw.json')['points']
    for i,(a,b) in enumerate(zip(old,stable)):
        require((a['x'],a['y'])==(b['x'],b['y']),'Crossvariant selected coordinate mismatch')
        field_equal={name:bits(a[name])==bits(b[name]) for name in ('mean_called','view_requested','covariance_flags')}
        require(all(field_equal.values()),'Actual mean/view/covariance/flags crossvariant witness changed')
        for mode,point in (('old',a),('stable',b)):
            samplers=raws[mode+'-reasons']['samplers'][:4]
            require(samplers[2]['samples'][i]['rgba']==point['covariance_flags'], 'Crossrole actual covariance/flags mismatch')
            require(samplers[0]['samples'][i]['rgba'][0]==point['firstReason'], 'Different-frame first reason disagrees')
        same_target=bits(a['first_target_reason'][:3])==bits(b['first_target_reason'][:3])
        same_index=a['firstNodeIndex']==b['firstNodeIndex']
        comparisons.append(dict(x=a['x'],y=a['y'],inputFieldBitsEqual=field_equal,targetBitsEqual=same_target,
            firstNodeIndexEqual=same_index,oldReason=a['firstReason'],stableReason=b['firstReason'],
            oldNodeIndex=a['firstNodeIndex'],stableNodeIndex=b['firstNodeIndex'],
            oldReferenceClassification=a['arithmeticReplayClassification'],stableReferenceClassification=b['arithmeticReplayClassification'],
            oldSupported=(a['reference']['physical']['supported'] if a['reference'] else None),
            stableSupported=(b['reference']['physical']['supported'] if b['reference'] else None),
            sameInputSupportedCategory4To3Witness=all(field_equal.values()) and same_target and same_index and
                a['firstReason']==4 and b['firstReason']==3 and a['reference']['physical']['supported']))
    failed=json_file(packet/'iris-old-inputs/final-failed-request-raw.json')
    require(failed['available'] is False,'Initial unavailable request must remain rejected')
    return dict(schema='aqualumen-independent-snell-main-iris-audit-v1',evidenceReplay='PASS',
        applicationVerdict='NEGATIVE_INSUFFICIENT_APPLICATION',minimumQualifiedAppliedPoints=4,
        publicSourceSHA256=PINS,records=reports,crossVariantPoints=comparisons,
        sameInputSupportedCategory4To3Witnesses=sum(p['sameInputSupportedCategory4To3Witness'] for p in comparisons),
        preservedUnavailableRequest=True,manifest=manifest,sameFrameProven=False,
        actualGPUArithmeticCauseProven=False,all48CausesObserved=False,allStageSourcesExported=False,
        naturalAppearanceAccepted=False,pixelAAAccepted=False,energyAccepted=False,FPSFloorAccepted=False,
        shippingAccepted=False,scope='Four separate actual Iris captures: public audit byte-replay, full PNG CRC/decode, '
            'integer-ns timing, fixed pose, prepared int1 and FINAL11-state, attached four-stage hash linkage. '
            'Only selected first-target witnesses; raw mean/view/C/flags and compared first target/index bits qualified. '
            'Actual source rewritten hashes are not archive hashes or proof of per-draw invocation. Guard/stage/FINAL/PNG '
            'are separately captured, not same-frame. Reason2 semantics differ old compound vs stable status!=1; '
            'a supported4→3 witness does not prove exact GPU rounding, all48 causes, sufficient application or visual fix.')


if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit('usage: audit.py SAVED_PACKET READ_ONLY_ACTUAL_SHADERPACK_DIRECTORY')
    print(json.dumps(audit(sys.argv[1],sys.argv[2]),indent=2,sort_keys=True,allow_nan=False))
