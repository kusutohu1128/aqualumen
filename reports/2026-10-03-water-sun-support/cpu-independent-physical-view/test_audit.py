"""CPU-only public tests; synthetic/missing files are not Minecraft evidence."""
from pathlib import Path
import importlib.util
import json
import shutil
import struct
import zlib
import subprocess
import sys
import tempfile
import unittest

AUDITOR=Path(__file__).with_name('audit.py')
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
sys.dont_write_bytecode=True
from report import metrics,EYE_TOLERANCE_M
from water_residual_sun_iris_runtime import VERSIONS
spec=importlib.util.spec_from_file_location('physical_view_audit',AUDITOR)
auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)


def synthetic_scene(scenario='underwater-up-near'):
    """Explicit CPU mock metadata, never a saved Minecraft capture."""
    depth,pitch={'underwater-up-near':(.5,-90),'underwater-up-deep':(3.25,-90),
        'underwater-up-tilt':(.5,-65)}[scenario]
    eye=[448.5,62.8889-depth,-383.5];player=[448.5,62.8889-1.62-depth,-383.5]
    run=dict(run_id='mock-only',world_id='b22dbccb-2970-41e6-847f-f183b1ec923d',seed=308060,
        pack_name='mock-only.zip',pack_sha256='1'*64)
    pose=dict(scene=scenario,camera_submersion_type='WATER',camera_first_person=True,
        camera_eye_match=True,player_touching_water=True,player_submerged_in_water=True,
        requested_player_position=player,requested_camera_rotation=[-45,pitch],
        requested_eye_depth=depth,reference_surface_y=62.8889,eye_tolerance_m=EYE_TOLERANCE_M,
        terrain_placement=False,requested_world_time=6000,actual_world_time=6000,
        actual_server_world_time=6000,measured_surface_y=62.8889,actual_eye_depth=depth,
        actual_eye_position=eye,actual_camera_position=eye)
    row=dict(scenario=scenario,run_id=run['run_id'],world_id=run['world_id'],
        pack_name=run['pack_name'],pack_sha256=run['pack_sha256'],resolution=[1600,900],
        framebuffer_resolution=[1600,900],player_dimension='minecraft:overworld',
        workload='warmed-view',warmup_seconds=10.0,sample_seconds_requested=5.0,
        contact_driver='none',window_focused=True,camera_follows_local_player=True,
        camera_first_person=True,camera_eye_match=True,physics_active_seen=True,
        shader_active=True,shader_fallback=False,camera_lock='mock-only',
        actual_player_position=player,actual_eye_position=eye,actual_camera_position=eye,
        expected_camera_rotation=[-45,pitch],actual_player_rotation=[-45,pitch],
        actual_camera_rotation=[-45,pitch],underwater_up=pose,
        sample_seconds_actual=5.0,recorded_seconds=5.0,**metrics([100.0]*50))
    return run,row,[100000000]*50


def synthetic_packet(packet):
    """Generated CPU filesystem boundary only; no observed GL or game data."""
    installed=packet/'mock-installed';installed.mkdir()
    exports=packet/'cpu-physical-view';exports.mkdir()
    rgba=(b'\x00'+b'\x00\x00\x00\xff'*1600)*900
    def chunk(name,body): return struct.pack('>I',len(body))+name+body+struct.pack('>I',zlib.crc32(name+body))
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1600,900,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rgba))+chunk(b'IEND',b'')
    def save(path,value): path.write_text(json.dumps(value,allow_nan=False))
    for mode in ('reject','zero'):
        name='Aqualumen-ShoreProbe-world-sun-support-'+mode+'-physical-v1.zip'
        source=ROOT/'reports/2026-10-03-water-sun-support/cpu-physical-view'/name
        for folder in (installed,exports): shutil.copyfile(source,folder/name)
        directory=packet/('iris-'+mode+'-physical');directory.mkdir();run_dir=directory/'run';run_dir.mkdir()
        run,_,_=synthetic_scene();run.update(schema=2,pack_name=name,pack_sha256=auditor.PACK_PINS[mode],
            expected_pack_sha256=auditor.PACK_PINS[mode],world_directory='AqualumenNaturalV2',
            world_generator='minecraft:noise/overworld',scenarios=list(auditor.SCENES),warmup_seconds=10.0,
            sample_seconds=5.0,frame_limit=120,vsync=False,render_chunks=12,simulation_chunks=6,
            resolution=[1600,900],framebuffer_resolution=[1600,900],expected_resolution=[1600,900],
            player_dimension='minecraft:overworld',shader_active=True,shader_fallback=False,
            gl_renderer='NVIDIA mock-only RTX 3080 Ti',mods={'aqualumen_benchmark':'0.3.9',
                'aqualumen_physics':'0.3.0','aqualumen_water_sun_test':'0.1.0',
                'aqualumen_water_stage_probe':'0.1.0','iris':'1.8.8+mc1.21.1','sodium':'0.6.9+mc1.21.1',
                'minecraft':'1.21.1','java':'21'},iris_configuration='enableShaders=true\nshaderPack='+name+'\n')
        save(run_dir/'run.json',run)
        save(run_dir/'complete.json',dict(status='complete',run_id=run['run_id'],scenarios=list(auditor.SCENES),
            fixture_cleanup_complete=True,utc='2026-10-03T00:00:40Z'))
        for scenario in auditor.SCENES:
            _,row,_=synthetic_scene(scenario);row.update(pack_name=name,pack_sha256=run['pack_sha256'])
            save(run_dir/(scenario+'.json'),row);(run_dir/(scenario+'.png')).write_bytes(png)
            (run_dir/(scenario+'.csv')).write_text('frame,ns,ms\n'+''.join(f'{i},100000000,100.0\n' for i in range(50)))
        identity=dict(worldId=run['world_id'],world='AqualumenNaturalV2',seed=308060,
            dimension='minecraft:overworld',packName=name,packSha256=run['pack_sha256'])
        guard={**identity,'schema':'aqualumen-sun-guard-observation-v1','observerVersion':'0.1.0',
            'available':True,'readOnly':True,'scopeAuthorized':True,'localIntegratedSinglePlayer':True,
            'currentPipelineMatches':True,'containsTessellation':True,'pass':'TRANSLUCENT',
            'scope':'prepared-current-translucent-int-uniform','supplierAuthorization':1,
            'programAndFrameUnchanged':True,'seam':'SodiumShader.updateUniforms TAIL',
            'registrationPath':'CommonUniforms.addDynamicUniforms TAIL uniform1i PER_FRAME',
            'supplierPath':'SunAuthorization.value(runtime(game)) fresh each invocation; no cache/latch',
            'benchmarkState':'complete','versions':dict(VERSIONS),'constructorProgram':401,
            'programBefore':401,'programAfter':401,'frameBefore':100,'frameAfter':100,
            'capturedUtc':'2026-10-03T00:00:41Z','uniform':dict(name='aqualumenSunTestAuthorized',
                active=True,type=5124,size=1,value=1,location=4)}
        for field in ('errorFlagConsumed','drawIssuedProven','fragmentFetchProven','WNSApplicationProven',
                      'pngSameFrameProven','allGLStateUnchangedProven'): guard[field]=False
        save(directory/'guard-raw.json',guard)
        stage={**identity,'expectedPack':name,'expectedPackSha256':run['pack_sha256'],
            'schema':'aqualumen-water-stage-observation-v1','available':True,'scope':'terrain-tessellation-stages',
            'observerVersion':'0.1.0','readOnly':True,'errorFlagConsumed':False,'localIntegratedSinglePlayer':True,
            'scopeAccepted':True,'currentPipelineMatches':True,'benchmarkState':'complete','afterSetupStateTail':True,
            'pass':'TRANSLUCENT','constructorContainsTessellation':True,'usingTessellationAtAdmission':True,
            'sourceHashesRequested':True,'linkStatus':1,'attachedShaderCount':4,'tessControlOutputVertices':3,
            'patchVertices':3,'tesSourceMarkerPresent':True,'programAndFrameUnchanged':True,'constructorProgram':401,
            'programBefore':401,'programAfter':401,'frameBefore':101,'frameAfter':101,
            'capturedUtc':'2026-10-03T00:00:42Z','versions':dict(VERSIONS),
            'capabilities':dict(GL_ARB_tessellation_shader=True,renderer='NVIDIA mock-only'),
            'stages':[dict(shader=i+1,type=t,sourceBytes=100,sourceSha256='a'*64) for i,t in
                enumerate((35632,35633,36487,36488))]}
        for field in ('drawIssuedProven','tessInvocationCountProven','fragmentValueFetchProven',
                      'exclusiveWaterProgramProven','nativeOrNaturalAppearanceAccepted'): stage[field]=False
        save(directory/'stage-raw.json',stage)
    return installed


class PhysicalViewAuditTests(unittest.TestCase):
    def test_incomplete_packet_fails_closed_without_writes(self):
        with tempfile.TemporaryDirectory(prefix='physical-view-public-test-') as temporary:
            packet=Path(temporary)
            result=subprocess.run([sys.executable,'-B',str(AUDITOR),str(packet)],
                text=True,capture_output=True)
            self.assertEqual(result.returncode,1)
            self.assertEqual(result.stderr,'Rejected physical-view packet: ValueError\n')
            self.assertEqual(result.stdout,'')
            self.assertEqual(list(packet.iterdir()),[])

    def test_complete_mock_near_preserves_integer_timing_without_application_claim(self):
        result=auditor.audit_scene(*synthetic_scene())
        self.assertEqual(result['rawFrameIntervals'],50)
        self.assertEqual(result['rawNanosecondsTotal'],5000000000)
        self.assertEqual(result['metrics']['mean_fps'],10.0)
        self.assertIs(result['applicationObserved'],False)

    def test_both_frozen_pack_sources_restore_only_exact_display_members(self):
        for mode in ('reject','zero'):
            pack=ROOT/'reports/2026-10-03-water-sun-support/cpu-physical-view'/(
                'Aqualumen-ShoreProbe-world-sun-support-'+mode+'-physical-v1.zip')
            result=auditor.audit_pack(pack,mode)
            self.assertEqual(result['changedExistingMembers'],['shaders/final.fsh','shaders/gbuffers_water.fsh'])
            self.assertIs(result['applicationObserved'],False)

    def test_complete_synthetic_filesystem_has_six_views_and_no_raw_application_claim(self):
        with tempfile.TemporaryDirectory(prefix='physical-view-complete-mock-') as temporary:
            packet=Path(temporary);installed=synthetic_packet(packet)
            result=auditor.audit(packet,installed_packs=installed)
            self.assertEqual(result['sceneCount'],6)
            self.assertIs(result['applicationObserved'],False)
            self.assertIs(result['currentFINALFixed16Qualified'],False)
            self.assertIs(result['shippingAccepted'],False)

    def test_wrong_actual_head_is_rejected(self):
        run,row,ns=synthetic_scene();row['underwater_up']['camera_submersion_type']='NONE'
        with self.assertRaises(ValueError): auditor.audit_scene(run,row,ns)

    def test_positive_but_short_raw_sample_is_rejected(self):
        run,row,ns=synthetic_scene();ns=ns[:48]
        row.update(recorded_seconds=4.8,**metrics([100.0]*48))
        with self.assertRaisesRegex(ValueError,'Truncated'): auditor.audit_scene(run,row,ns)

    def test_moving_profile_cannot_enter_static_packet(self):
        with tempfile.TemporaryDirectory(prefix='physical-view-moving-mock-') as temporary:
            packet=Path(temporary);installed=synthetic_packet(packet)
            path=packet/'iris-zero-physical/run/run.json';run=json.loads(path.read_bytes())
            run['scenarios'].append('moving-view');path.write_text(json.dumps(run))
            with self.assertRaises(ValueError): auditor.audit(packet,installed_packs=installed)

    def test_guard_zero_cannot_qualify_prepared_authorization(self):
        with tempfile.TemporaryDirectory(prefix='physical-view-guard-mock-') as temporary:
            packet=Path(temporary);installed=synthetic_packet(packet)
            path=packet/'iris-zero-physical/guard-raw.json';guard=json.loads(path.read_bytes())
            guard['uniform']['value']=0;path.write_text(json.dumps(guard))
            with self.assertRaises(ValueError): auditor.audit(packet,installed_packs=installed)

    def test_partial_png_cannot_be_accepted_by_complete_metadata(self):
        with tempfile.TemporaryDirectory(prefix='physical-view-PNG-mock-') as temporary:
            packet=Path(temporary);installed=synthetic_packet(packet)
            path=packet/'iris-zero-physical/run/underwater-up-deep.png';path.write_bytes(path.read_bytes()[:100])
            with self.assertRaises(ValueError): auditor.audit(packet,installed_packs=installed)


if __name__=='__main__': unittest.main(verbosity=2)
