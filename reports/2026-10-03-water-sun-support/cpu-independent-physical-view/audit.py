"""Read-only CPU audit of saved physical-display TEST views, not adoption."""
import argparse
import hashlib
import importlib.util
import json
import math
from datetime import datetime
from pathlib import Path
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from report import metrics,validate_underwater_up,check_png
from test_thin_runtime_audit import read_intervals
from water_residual_sun_iris_runtime import IDENTITY,exact_fields,zip_files,json_file,guard_observation
from water_sun_support_physical_pack import MANIFEST,FINAL,WATER,FINAL_SHA,WATER_SHA,PARENTS,FROZEN

SCENES=('underwater-up-near','underwater-up-deep','underwater-up-tilt')
PACK_PINS={'reject':'097f8f639fcc04681e09fc1045f9970462642c3f21ad4e74164aea52250e6e0e',
           'zero':'33164466c3828daa93724d6b9e531fcb66897e300ecd16dc4cfa90ec08c38cda'}
BUILDER_PIN='950860d5c2768f0f8899da65b479a70e7339af2eb202ab3e5ac5ebd03f5c4d49'
STAGES=('shaders/gbuffers_water.vsh','shaders/gbuffers_water.tcs','shaders/gbuffers_water.tes')
LAB_PACKS=Path.home()/'.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft/shaderpacks'
STAGE_HELPER=ROOT/'reports/2026-10-03-water-sun-support/cpu-independent-iris/audit.py'
STAGE_HELPER_PIN='911265553e2f44cf6ea475cdb3a69343fb9f7d5ae75be18ba012aa2f7133315f'


def require(value,message):
    if not value: raise ValueError(message)


def sha(value): return hashlib.sha256(value).hexdigest()


def audit_pack(pack,mode):
    """Exact archive comparison; inherited atlas metadata is provenance only."""
    require(mode in PACK_PINS,'Unknown physical-view policy')
    require(sha((ROOT/'tools/water_sun_support_physical_pack.py').read_bytes())==BUILDER_PIN,'Frozen builder changed')
    pack=Path(pack);require(sha(pack.read_bytes())==PACK_PINS[mode],'Frozen physical-view ZIP changed')
    files=zip_files(pack);meta=json.loads(files[MANIFEST]);name,parent_pin=PARENTS[mode]
    parent_path=ROOT/FROZEN/name;require(sha(parent_path.read_bytes())==parent_pin,'Frozen reasons parent changed')
    parent=zip_files(parent_path)
    extra={MANIFEST,'PARENT-SUN-PHYSICAL-VIEW-final.fsh','PARENT-SUN-PHYSICAL-VIEW-water.fsh'}
    require(set(files)==set(parent)|extra,'Physical-view archive inventory changed')
    changed=[name for name in sorted(parent) if files[name]!=parent[name]]
    require(changed==[FINAL,WATER],'Physical-view changed another parent member')
    require(files[FINAL]==parent['original/'+FINAL] and sha(files[FINAL])==FINAL_SHA
        and files[WATER]==parent['SUN-SUPPORT-physical.fsh'] and sha(files[WATER])==WATER_SHA,
        'Physical FINAL/water source restoration differs')
    require(files['PARENT-SUN-PHYSICAL-VIEW-final.fsh']==parent[FINAL]
        and files['PARENT-SUN-PHYSICAL-VIEW-water.fsh']==parent[WATER],'Prior sources were not preserved exactly')
    exact_fields(meta,dict(schema='aqualumen-water-sun-support-physical-view-v1',mode=mode,
        view='physical-final',test_only=True,not_shipping=True,parent_pack_sha256=parent_pin,
        parent_metadata_member='WATER-SUN-SUPPORT.json',parent_metadata_sha256=sha(parent['WATER-SUN-SUPPORT.json']),
        geometry_factor=4,fixed_phase_seconds=120.0,original_archives_unchanged=True,
        same_frozen_kernel_and_guard=True,role_STORE_removed=True,fully_observer_free=False,
        inherited_MRT_and_TES_retained=True,helper_reason_and_certificate_assignments_retained=True,
        inherited_metadata_is_current_display_policy=False,inherited_FINAL_legends_authoritative=False,
        FINAL_display_policy_changed=True,performance_settings_changed=False,
        sky_cloud_reflection_density_source_changed=False,current_FINAL_fixed16_qualification_available=False,
        C9_C12_FINAL_uniforms_expected_inactive=True,operator_application_observed=False,
        fixed16_minimum4_diagnostic_gate_waived=False),'Wrong authoritative physical-view contract')
    require(meta['changed_existing_members']==[FINAL,WATER],'Changed member declaration differs')
    policy=json.loads(parent['WATER-SUN-SUPPORT.json'])
    require(meta['guard_uniform']==policy['guard_uniform'] and meta['guard_call_expression']==policy['guard_call_expression']
        and meta['helper_sha256']==policy['helper_sha256'],'Guard/kernel provenance changed')
    for key in ('shipping_fix','physical_accepted','runtime_accepted','pixel_AA_accepted','visual_accepted',
                'performance_accepted','energy_accepted','reciprocity_accepted','shipping_accepted'):
        require(meta[key] is False,'Unaccepted physical-view claim')
    return dict(mode=mode,packSha256=PACK_PINS[mode],parentPackSha256=parent_pin,
        changedExistingMembers=changed,addedMembers=sorted(extra),restoredFinalSha256=FINAL_SHA,
        physicalWaterFSSha256=WATER_SHA,geometrySourceSha256={name:sha(files[name]) for name in STAGES},
        helperSha256=meta['helper_sha256'],applicationObserved=False,
        certificateCountsObserved=False,TESSelectedTexelsObserved=False,fullyObserverFree=False)


def audit_scene(run,row,ns):
    """Complete first-person WATER pose and integer timing; no sampler claims."""
    scenario=row.get('scenario');require(scenario in SCENES,'Unapproved physical-view scene')
    exact_fields(row,dict(scenario=scenario,run_id=run['run_id'],world_id=IDENTITY['worldId'],
        pack_name=run['pack_name'],pack_sha256=run['pack_sha256'],resolution=[1600,900],
        framebuffer_resolution=[1600,900],player_dimension='minecraft:overworld',
        workload='warmed-view',warmup_seconds=10.0,sample_seconds_requested=5.0,
        contact_driver='none',window_focused=True,camera_follows_local_player=True,
        physics_active_seen=True,shader_active=True,shader_fallback=False),'Wrong measured scene identity/controls')
    require(bool(row.get('camera_lock')),'Missing camera lock')
    validate_underwater_up(row,scenario)
    require(type(ns) is list and 10<=len(ns)<=100000 and all(type(n) is int and 0<n<2**63 for n in ns),
        'Raw frame intervals must be positive integer nanoseconds')
    computed=metrics([n*1e-6 for n in ns]);ordered=sorted(ns);slow=max(1,math.ceil(len(ns)*.01))
    integer=dict(frames=len(ns),mean_fps=1e9*len(ns)/sum(ns),
        one_percent_low_fps=1e9*slow/sum(ordered[-slow:]),
        p99_ms=ordered[math.ceil(len(ns)*.99)-1]/1e6,max_ms=max(ns)/1e6,
        min_instantaneous_fps=1e9/max(ns),frames_over_16_667_ms=sum(n*60>1000000000 for n in ns))
    for field,value in computed.items():
        saved=row.get(field)
        require(type(saved) in (int,float) and math.isfinite(saved)
            and math.isclose(saved,value,rel_tol=1e-12,abs_tol=1e-9)
            and math.isclose(integer[field],value,rel_tol=1e-12,abs_tol=1e-9),'Integer timing metric mismatch: '+field)
        if type(value) is int: require(type(saved) is int,'Integer frame count recorded with wrong type')
    duration=sum(ns)/1e9;actual=row.get('sample_seconds_actual');recorded=row.get('recorded_seconds')
    require(type(actual) in (int,float) and type(recorded) in (int,float)
        and math.isfinite(actual) and math.isfinite(recorded) and actual>=4.9 and duration>=4.9
        and duration<=actual+1e-8 and math.isclose(recorded,duration,rel_tol=0,abs_tol=1e-8),
        'Truncated/inconsistent five-second raw sample')
    return dict(scenario=scenario,rawFrameIntervals=len(ns),rawNanosecondsTotal=sum(ns),
        rawDurationSeconds=duration,metrics=computed,cameraPosition=row['actual_camera_position'],
        eyePosition=row['actual_eye_position'],cameraRotation=row['actual_camera_rotation'],
        actualEyeDepth=row['underwater_up']['actual_eye_depth'],applicationObserved=False,
        certificateCountsObserved=False,TESSelectedTexelsObserved=False,FPSFloorAccepted=False)


def audit(packet,*,installed_packs=None):
    """Public filesystem boundary; default aliases are read-only Lab exports."""
    packet=Path(packet).resolve();installed=LAB_PACKS if installed_packs is None else Path(installed_packs)
    require(all((packet/('iris-'+mode+'-physical')).is_dir() for mode in PACK_PINS),'Incomplete physical-view packet')
    require(sha(STAGE_HELPER.read_bytes())==STAGE_HELPER_PIN,'Frozen stage qualification helper changed')
    spec=importlib.util.spec_from_file_location('frozen_physical_stage_contract',STAGE_HELPER)
    stage_helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage_helper)
    records={};manifest={}
    for mode in PACK_PINS:
        directory=packet/('iris-'+mode+'-physical');run_dir=directory/'run'
        name='Aqualumen-ShoreProbe-world-sun-support-'+mode+'-physical-v1.zip'
        pack=packet/'cpu-physical-view'/name;source=audit_pack(pack,mode)
        require((installed/name).read_bytes()==pack.read_bytes(),'Retained installed ZIP differs from frozen export')
        run=json_file(run_dir/'run.json');complete=json_file(run_dir/'complete.json')
        require(not (run_dir/'aborted.json').exists(),'Physical-view capture aborted')
        exact_fields(run,dict(schema=2,world_id=IDENTITY['worldId'],seed=IDENTITY['seed'],
            world_generator='minecraft:noise/overworld',scenarios=list(SCENES),warmup_seconds=10.0,
            sample_seconds=5.0,frame_limit=120,vsync=False,render_chunks=12,simulation_chunks=6,
            pack_name=name,pack_sha256=PACK_PINS[mode],expected_pack_sha256=PACK_PINS[mode],
            resolution=[1600,900],framebuffer_resolution=[1600,900],expected_resolution=[1600,900],
            player_dimension='minecraft:overworld',shader_active=True,shader_fallback=False),
            'Wrong complete physical-view run identity/controls')
        require(type(run.get('run_id')) is str and bool(run['run_id'])
            and Path(run['world_directory']).name==IDENTITY['world'],'Wrong exact disposable world/run')
        exact_fields(complete,dict(status='complete',run_id=run['run_id'],scenarios=list(SCENES),
            fixture_cleanup_complete=True),'Incomplete three-view capture or cleanup')
        mods={'aqualumen_benchmark':'0.3.9','aqualumen_physics':'0.3.0','aqualumen_water_sun_test':'0.1.0',
            'aqualumen_water_stage_probe':'0.1.0','iris':'1.8.8+mc1.21.1','sodium':'0.6.9+mc1.21.1',
            'minecraft':'1.21.1','java':'21'}
        exact_fields(run['mods'],mods,'Wrong actual Mod versions')
        require('NVIDIA' in run['gl_renderer'] and '3080 Ti' in run['gl_renderer'],'Wrong recorded GPU')
        properties={}
        for line in run['iris_configuration'].splitlines():
            if line and not line.startswith('#') and '=' in line:
                key,value=line.split('=',1);require(key not in properties,'Duplicate Iris configuration');properties[key]=value
        require(properties.get('enableShaders')=='true' and properties.get('shaderPack')==name,'Wrong selected Iris pack')
        identity={**IDENTITY,'packName':name,'packSha256':PACK_PINS[mode]}
        guard=json_file(directory/'guard-raw.json');guard_observation(guard,identity)
        stage=json_file(directory/'stage-raw.json');linked=stage_helper.stage_contract(stage,identity)
        require(guard['benchmarkState']=='complete' and guard['constructorProgram']==stage['constructorProgram'],
            'Prepared guard/stage not matched after complete run')
        stamp=lambda value: datetime.fromisoformat(value.replace('Z','+00:00'))
        require(stamp(complete['utc'])<stamp(guard['capturedUtc'])
            and stamp(complete['utc'])<stamp(stage['capturedUtc']),'Observation predates measurement completion')
        geometry={key:value for key,value in linked.items() if key!='35632'}
        if records: require(geometry==records['reject']['actualGeometryStageHashes'],'Actual rewritten geometry stages changed')
        rows=[]
        for scenario in SCENES:
            scene=json_file(run_dir/(scenario+'.json'));ns,_=read_intervals(run_dir/(scenario+'.csv'))
            row=audit_scene(run,scene,ns);check_png(run_dir/(scenario+'.png'),(1600,900))
            row['PNGIntegrityQualified']=True;row['pngSha256']=sha((run_dir/(scenario+'.png')).read_bytes());rows.append(row)
        records[mode]=dict(source=source,runId=run['run_id'],scenes=rows,actualGeometryStageHashes=geometry,
            actualFragmentStageHash=linked['35632'],guardFrame=guard['frameBefore'],stageFrame=stage['frameBefore'],
            preparedGuardUniform=guard['uniform'],completedUtc=complete['utc'],
            lastCompletedScene='underwater-up-tilt',observerCameraPoseMeasured=False)
        for path in directory.rglob('*'):
            if path.is_file(): manifest[str(path.relative_to(packet))]=sha(path.read_bytes())
    require(records['reject']['source']['geometrySourceSha256']==records['zero']['source']['geometrySourceSha256'],
        'Archive geometry differs between policies')
    pairs=[]
    for left,right in zip(records['reject']['scenes'],records['zero']['scenes']):
        for field in ('scenario','cameraPosition','eyePosition','cameraRotation','actualEyeDepth'):
            require(left[field]==right[field],'Actual paired pose differs: '+field)
        pairs.append(dict(scenario=left['scenario'],actualPoseEqual=True,
            PNGByteEqual=left['pngSha256']==right['pngSha256'],sameFrameProven=False,pixelCausalityAccepted=False))
    return dict(schema='aqualumen-independent-physical-view-audit-v1',evidenceReplay='PASS',sceneCount=6,
        records=records,pairedViews=pairs,manifest=manifest,applicationObserved=False,
        certificateCountsObserved=False,TESSelectedTexelsObserved=False,currentFINALFixed16Qualified=False,
        minimum4DiagnosticGateWaived=False,fullyObserverFree=False,sameFrameProven=False,
        drawIssuedProven=False,fragmentFetchProven=False,actualSunUniformObserved=False,
        sourcePhysicalAccepted=False,naturalAppearanceAccepted=False,pixelAAAccepted=False,
        motionAccepted=False,FPSFloorAccepted=False,performanceAccepted=False,energyAccepted=False,
        reciprocityAccepted=False,shippingAccepted=False,
        scope='Six static warmed900p/120-cap physical-display views; full PNG/pose/integer-ns/source audit. '
            'Prepared guard and attached terrain stages are separate after-complete snapshots, not PNG-frame '
            'application, fragment fetch or current FINAL-bound diagnostic texels. Original min4 gate is not '
            'waived; it is unobserved here. Live entities/contact fields may differ despite phase120 source. '
            'No appearance, pixel-AA, motion,1440p,FPS-floor,energy,reciprocity or shipping adoption.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet',type=Path)
    args=parser.parse_args()
    try: result=audit(args.packet)
    except (OSError,ValueError,TypeError,KeyError,OverflowError,UnicodeError) as error:
        parser.exit(1,'Rejected physical-view packet: '+type(error).__name__+'\n')
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))


if __name__=='__main__': main()
