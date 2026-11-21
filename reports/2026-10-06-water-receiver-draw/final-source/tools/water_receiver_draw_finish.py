"""CPU-only provenance / safe ordinary handoff and exclusive evidence seal."""
import json
from pathlib import Path
import subprocess
import sys
from water_receiver_draw_audit import ROOT, OUT, audit, sha
from water_receiver_sun_finish import copy
from water_receiver_texture_lifecycle import GAME
from water_normal_pause_event import verify_pause_event

def main(pid, handle, runtime, pause):
    if (OUT / 'SHA256SUMS').exists(): raise ValueError('Never overwrite sealed evidence')
    for name in (runtime,pause):
        if Path(name).name != name or not name.startswith('2026-10-06_'):
            raise ValueError('Exact root-inspected screenshot names required')
    baseline = json.loads((OUT/'fresh-normal-baseline.json').read_text())
    for name in ('normal-restored.json','normal-exact-before-reopening.json'):
        if json.loads((OUT/name).read_text()) != baseline:
            raise ValueError('Ordinary state not byte-exact before reopening')
    if len(baseline['ordinarySavedFilesSHA256']) != 41:
        raise ValueError('Ordinary snapshot scope changed')
    controls = baseline['instrumentationEntryPointsAbsent'] + [
        'aqualumen-receiver-material-probe.properties','aqualumen-receiver-mesher-probe.properties',
        'aqualumen-receiver-draw-probe.properties']
    if any((GAME/'config'/name).exists() for name in controls):
        raise ValueError('TEST opt-in remains enabled')
    if {p.name:sha(p) for p in (GAME/'mods').glob('*.jar')} != baseline['activeMods']:
        raise ValueError('Ordinary Mod set changed')
    config_receipt = {}
    for name,digest in baseline['configSHA256'].items():
        current = sha(GAME/name)
        timestamp_only = False
        if current != digest:
            if name != 'config/iris.properties': raise ValueError('Ordinary configuration changed')
            before = (Path(baseline['backup'])/name).read_text().splitlines()
            after = (GAME/name).read_text().splitlines()
            # Iris saves Properties on startup: preserve this observed timestamp change.
            # Never treat an actual property/value change as merely semantic equality.
            if (len(before) != len(after) or len(before) < 3 or before[0] != after[0]
                    or before[2:] != after[2:] or not before[1].startswith('#Tue Oct 06 ')
                    or not after[1].startswith('#Tue Oct 06 ')):
                raise ValueError('Iris change is not only its observed startup timestamp')
            timestamp_only = True
        config_receipt[name] = dict(beforeSHA256=digest, runtimeSHA256=current,
                                  exactBytes=current==digest, onlyIrisStartupTimestampChanged=timestamp_only)
    pack = sha(GAME/'shaderpacks/Aqualumen-0.6.0.zip')
    if pack != '6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73':
        raise ValueError('Ordinary pack changed')
    proc = Path('/proc')/str(pid)
    if (proc/'comm').read_text().strip() != 'java': raise ValueError('Actual Java not live')
    locks = [int(p.name) for p in (proc/'fd').iterdir() if p.readlink() == GAME/'saves/新規ワールド/session.lock']
    if len(locks) != 1: raise ValueError('Actual ordinary ownership not proved')
    log = (GAME/'logs/latest.log').read_text()
    chronology = verify_pause_event(log,runtime,pause)
    if ('OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti' not in log
            or 'Using shaderpack: Aqualumen-0.6.0.zip' not in log
            or '0.2.0 contact bridge initialized' not in log
            or any(s in log for s in ('aqualumen_receiver_draw_probe','aqualumen_receiver_mesher_probe',
                                     'aqualumen_receiver_material_probe','OpenGL debug message'))):
        raise ValueError('Actual normal NVIDIA/Iris/physics activation not proved')
    if json.loads((OUT/'independent-draw-audit.json').read_text()) != audit():
        raise ValueError('Saved independent draw audit changed')
    build = json.loads((OUT/'build-receipt.json').read_text())
    for name,digest in build['sourceSHA256'].items():
        if sha(ROOT/name) != digest: raise ValueError('Actual built observer source changed')
    native = ROOT/'reports/2026-10-06-water-receiver-sun/native-v1/receipt.json'
    for name,digest in json.loads(native.read_text())['sourceSHA256'].items():
        if name.startswith('shaders/') and sha(ROOT/name) != digest:
            raise ValueError('GLSL changed since retained NVIDIA qualification')
    increments = {}
    labels = ['decode-'+phase+str(i) for i in (1,2,3) for phase in ('red','green')]
    labels += ['decode-final','audit-red1','audit-green1','audit-final']
    messages = {'decode-red1':'Actual encoded vertex must decode through public API',
                'decode-red2':'Nonfinite actual matrix must remain unready',
                'decode-red3':'Outside pinned encoded light range stays unready',
                'audit-red1':'Independent actual draw reader not implemented'}
    for label in labels:
        receipt = json.loads((OUT/label/'receipt.json').read_text())
        expected = 1 if 'red' in label else 0
        if receipt['exitCode'] != expected: raise ValueError('Increment result changed')
        for name,digest in receipt['sourceSHA256'].items():
            if sha(OUT/label/'source'/name) != digest: raise ValueError('Frozen increment changed')
            if label.endswith('final') and sha(ROOT/name) != digest: raise ValueError('Final CPU source changed')
        if label in messages and messages[label] not in (OUT/label/'test.log').read_text():
            raise ValueError('RED was not the declared public behavior')
        increments[label] = expected
    exits = {}
    for name,command in {
        'vertex-shader':['bash','tools/test-receiver-vertex-shader.sh'],
        'public-draw-audit':['python3','tools/test_water_receiver_draw_audit.py'],
        'retained-vertex':['bash','tools/test-receiver-vertex.sh'],
        'retained-mesher-scope':['bash','tools/test-receiver-mesher-scope.sh'],
        'retained-public-mesher-audit':['python3','tools/test_water_receiver_mesher_audit.py'],
        'pause-chronology':['python3','tools/test_water_normal_pause_event.py'],
        'worktree-whitespace':['git','diff','--check']}.items():
        run = subprocess.run(['rtk','proxy',*command],cwd=ROOT,capture_output=True)
        with (OUT/(name+'-green.log')).open('xb') as stream: stream.write(run.stdout+run.stderr)
        exits[name] = run.returncode
        if run.returncode: raise ValueError('Final CPU check failed: '+name)
    copy(GAME/'logs/latest.log',OUT/'normal-final-runtime.log')
    copy(Path(baseline['backup'])/'config/iris.properties',OUT/'iris-before-normal-reopen.properties')
    copy(GAME/'config/iris.properties',OUT/'iris-after-normal-reopen.properties')
    images = [(runtime,'normal-runtime.png'),(pause,'normal-pause.png'),
        ('2026-10-06_17.17.37.png','normal-save-quit-focus.png'),
        ('2026-10-06_17.21.56.png','normal-title-quit-focus.png'),
        ('2026-10-06_17.24.40.png','test-runtime.png'),
        ('2026-10-06_17.27.15.png','test-save-quit-focus.png'),
        ('2026-10-06_17.27.52.png','test-title-quit-focus.png')]
    for original,name in images: copy(GAME/'screenshots'/original,OUT/name)
    sources = [ROOT/'docs/REALISM_GOAL.md',ROOT/'docs/RECEIVER_FIELD.md',
        ROOT/'physics-mod/dev/aqualumen/physics/ReceiverVertexShader.java',
        ROOT/'physics-mod/test/dev/aqualumen/physics/ReceiverVertexShaderTest.java',
        ROOT/'tools/test-receiver-vertex-shader.sh',ROOT/'tools/test_water_receiver_draw_audit.py',
        ROOT/'tools/build-receiver-draw-probe.sh',ROOT/'tools/water_receiver_texture_lifecycle.py',
        ROOT/'tools/water_receiver_sun_finish.py',ROOT/'tools/water_receiver_sun_audit.py',
        ROOT/'tools/water_normal_pause_event.py',ROOT/'tools/water_legacy_branch_snapshot.py',
        *sorted((ROOT/'tools').glob('water_receiver_draw*.py')),
        *sorted((ROOT/'tools/receiver-draw-probe').rglob('*'))]
    for source in dict.fromkeys(sources):
        if source.is_file(): copy(source,OUT/'final-source'/source.relative_to(ROOT))
    checkpoint = dict(fullGoalAchieved=False, previousGoalTurnClassification='no_progress',
        actualDrawInputsValidated=True, actualGPUOutputFloatsMatched=448, cpuDecoderMaximumGPUFloatError=0,
        independentDecoderMaximumGPUFloatError=0, actualArchivedFaces=14, actualArchivedVertices=56,
        originalTerrainFragmentInvocation=False, filteredFragmentFetchProven=False,
        liveMeshResourceEpochProven=False, shadedWorldSourceUploaded=False, dynamicIrisSourceBinding=False,
        productionNaturalVisualFixAccepted=False,newMinecraftFrameTimings=False,
        standaloneNativeGLExecutedThisCycle=False, ownedInMinecraftVSFixtureExecuted=True,
        standaloneNativeGLAfterNormalRelaunch=False,ordinaryWorldAutomation=False,ordinarySaveRestored=False,
        ordinarySavedFilesExactBeforeReopening=True, ordinarySavedFileCount=41,
        previousOrdinaryOwnedHandle=3603,previousOrdinaryExit=0,testOwnedHandle=49872,testHostJava=3461463,
        testExit=0,testExitConfirmedByOwnedHandle=True,noJavaConfirmedBeforeRestore=True,
        ordinaryHostJava=pid,ordinaryOwnedHandle=handle,ordinaryLockFD=locks[0],
        normalPackSHA256=pack,normalPhysicsSHA256=sha(GAME/'mods/aqualumen-physics-0.2.0.jar'),
        allOptInEntryPointsAbsent=controls,runtimeScreenshot=runtime,pauseScreenshot=pause,
        normalRuntimeConfigurationComparison=config_receipt,
        rootInspectedRuntimeAndPause=True,rootInspectedTestView=True,
        actualTestVisualWaterStillCyanAndSerrated=True,pauseEventChronology=chronology,
        publicCPUCheckExitCodes=exits,incrementExitCodes=increments,
        openALDeviceUnavailable='Failed to open OpenAL device' in log,
        intendedNextAction='Qualify actual triangle interpolation/material fetch and shared lighting/Sun before live per-face source promotion')
    with (OUT/'checkpoint.json').open('x') as stream: json.dump(checkpoint,stream,indent=2,sort_keys=True)
    paths = sorted(p for p in OUT.rglob('*') if p.is_file())
    with (OUT/'SHA256SUMS').open('x') as stream:
        for path in paths:
            if path.is_symlink(): raise ValueError('Evidence symlink rejected')
            stream.write(f'{sha(path)}  {path.relative_to(ROOT)}\n')
    print('Sealed',len(paths),'files; actual vertex decode qualified, ordinary paused; full goal active')

if __name__ == '__main__': main(int(sys.argv[1]),int(sys.argv[2]),sys.argv[3],sys.argv[4])
