"""Freeze exclusive resource evidence and prove normal-runtime handoff, CPU only."""
import json
from pathlib import Path
import re
import subprocess
import sys
from water_receiver_light_audit import ROOT, OUT, audit, sha
from water_receiver_light_lifecycle import copy
from water_receiver_texture_lifecycle import GAME
from water_normal_pause_event import verify_pause_event


def finish(pid,handle,runtime,pause):
    if (OUT/'SHA256SUMS').exists():
        raise ValueError('Never overwrite sealed evidence')
    baseline=json.loads((OUT/'fresh-normal-baseline.json').read_text())
    for name in ('normal-restored.json','normal-exact-before-reopening.json'):
        if json.loads((OUT/name).read_text())!=baseline:
            raise ValueError('Ordinary state not byte-exact before reopen')
    controls=baseline['instrumentationEntryPointsAbsent']+[
        'aqualumen-receiver-material-probe.properties','aqualumen-receiver-mesher-probe.properties',
        'aqualumen-receiver-draw-probe.properties','aqualumen-receiver-light-probe.properties']
    if any((GAME/'config'/name).exists() for name in controls):
        raise ValueError('TEST opt-in remains')
    if {p.name:sha(p) for p in (GAME/'mods').glob('*.jar')}!=baseline['activeMods']:
        raise ValueError('Ordinary Mod set changed')
    config={}
    for name,digest in baseline['configSHA256'].items():
        current=sha(GAME/name);timestamp=False
        if current!=digest:
            if name!='config/iris.properties':
                raise ValueError('Ordinary configuration changed')
            a=(Path(baseline['backup'])/name).read_text().splitlines();b=(GAME/name).read_text().splitlines()
            date=r'#(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) [A-Z][a-z]{2} +\d{1,2} \d{2}:\d{2}:\d{2} JST \d{4}'
            if len(a)!=len(b) or len(a)<3 or a[0]!=b[0] or a[2:]!=b[2:] or not re.fullmatch(date,a[1]) or not re.fullmatch(date,b[1]):
                raise ValueError('Actual Iris settings changed, not only startup timestamp')
            timestamp=True
        config[name]=dict(beforeSHA256=digest,runtimeSHA256=current,exactBytes=current==digest,onlyIrisStartupTimestampChanged=timestamp)
    pack=sha(GAME/'shaderpacks/Aqualumen-0.6.0.zip')
    if pack!='6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73':
        raise ValueError('Normal pack changed')
    proc=Path('/proc')/str(pid)
    if (proc/'comm').read_text().strip()!='java':
        raise ValueError('Actual normal Java is not live')
    locks=[]
    for path in (proc/'fd').iterdir():
        try:
            target=path.readlink()
        except FileNotFoundError:
            continue
        if target==GAME/'saves/新規ワールド/session.lock':
            locks.append(int(path.name))
    if len(locks)!=1:
        raise ValueError('Actual ordinary world ownership not established')
    log=(GAME/'logs/latest.log').read_text()
    chronology=verify_pause_event(log,runtime,pause)
    for filename in (runtime,pause):
        if Path(filename).name!=filename or not filename.startswith('2026-10-08_'):
            raise ValueError('Exact root-inspected current screenshot required')
    if ('OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti' not in log
            or 'Using shaderpack: Aqualumen-0.6.0.zip' not in log or '0.2.0 contact bridge initialized' not in log
            or 'OpenGL debug message' in log or 'aqualumen_receiver_light_probe' in log
            or any(s in log.lower() for s in ('error creating shader','shader fallback','failed to load shaderpack'))):
        raise ValueError('Ordinary real NVIDIA/Iris/physics activation rejected')
    result=audit()
    if json.loads((OUT/'independent-resource-material-audit.json').read_text())!=result:
        raise ValueError('Independent material result changed')
    receipt=json.loads((OUT/'build-receipt.json').read_text())
    for name,digest in receipt['sourceSHA256'].items():
        if sha(ROOT/name)!=digest or sha(OUT/'actual-build-v3/source'/name)!=digest:
            raise ValueError('Actual executed observer/helper source changed')
    if sha(OUT/'actual-build-v3'/receipt['jar'])!=receipt['artifactSHA256']:
        raise ValueError('Executed TEST artifact changed')
    previous=ROOT/'reports/2026-10-06-water-receiver-sun/native-v1/receipt.json'
    for name,digest in json.loads(previous.read_text())['sourceSHA256'].items():
        if name.startswith('shaders/') and sha(ROOT/name)!=digest:
            raise ValueError('Retained shader qualification no longer current')
    exits={}
    commands={
        'resource-audit-controls':['python3','tools/test_water_receiver_light_audit.py'],
        'pause-controls':['python3','tools/test_water_normal_pause_event.py'],
        'vertex-shader':['bash','tools/test-receiver-vertex-shader.sh'],
        'triangle':['bash','tools/test-receiver-triangle.sh'],
        'whitespace':['git','diff','--check']}
    for name,command in commands.items():
        run=subprocess.run(['rtk','proxy',*command],cwd=ROOT,capture_output=True)
        with (OUT/(name+'-green.log')).open('xb') as stream:
            stream.write(run.stdout+run.stderr)
        exits[name]=run.returncode
        if run.returncode:
            raise ValueError('Final CPU check failed: '+name)
    copy(GAME/'logs/latest.log',OUT/'normal-final-runtime.log')
    for original,name in ((runtime,'normal-runtime.png'),(pause,'normal-pause.png'),
        ('2026-10-06_18.01.43.png','normal-save-quit-focus.png'),('2026-10-06_18.02.12.png','normal-title-quit-focus.png'),
        ('2026-10-08_20.41.09.png','test-runtime.png'),('2026-10-08_20.42.33.png','test-save-quit-focus.png'),
        ('2026-10-08_20.43.18.png','test-title-quit-focus.png')):
        copy(GAME/'screenshots'/original,OUT/name)
    copy(Path(baseline['backup'])/'config/iris.properties',OUT/'iris-before-normal-reopen.properties')
    copy(GAME/'config/iris.properties',OUT/'iris-after-normal-reopen.properties')
    sources=[ROOT/'README.md',ROOT/'docs/REALISM_GOAL.md',ROOT/'docs/RECEIVER_FIELD.md',
        ROOT/'tools/build-receiver-light-probe.sh',*sorted((ROOT/'tools/receiver-light-probe').rglob('*')),
        *sorted((ROOT/'tools').glob('water_receiver_light_*.py')),ROOT/'tools/test_water_receiver_light_audit.py',
        ROOT/'tools/water_receiver_texture_lifecycle.py',ROOT/'tools/water_legacy_branch_snapshot.py',
        ROOT/'tools/water_normal_pause_event.py',ROOT/'physics-mod/dev/aqualumen/physics/ReceiverVertexShader.java',
        ROOT/'physics-mod/dev/aqualumen/physics/ReceiverTriangle.java']
    for source in dict.fromkeys(sources):
        if source.is_file():
            copy(source,OUT/'final-source'/source.relative_to(ROOT))
    checkpoint=dict(fullGoalAchieved=False,previousGoalTurnClassification='progress',
        actualRenderer=result['actualRenderer'],actualGLVersion=result['actualGLVersion'],
        actualActiveUniforms=result['actualUniforms'],actualSampledTextures=result['actualSampledTextures'],
        actualRawLevels=result['actualRawLevels'],actualRawTextureBytes=result['actualRawTextureBytes'],
        controlledGPUFetches=80,maximumMaterialError=result['maximumMaterialError'],
        maximumLevelZeroSubstitutionDifference=result['maximumLevelZeroSubstitutionDifference'],
        materialTolerance=result['materialTolerance'],naturalFragmentDerivatives=False,
        originalTerrainFragmentInvocation=False,liveMeshResourceEpochProven=False,
        sourceRadiance=False,shadedWorldSourceUploaded=False,dynamicIrisSourceBinding=False,
        productionNaturalVisualFixAccepted=False,newMinecraftFrameTimings=False,
        standaloneNativeGLExecutedThisCycle=False,standaloneNativeGLAfterNormalRelaunch=False,
        noProbeJarOrOptInInstalled=True,ordinarySavedFilesExactBeforeReopening=True,ordinarySavedFileCount=41,
        ordinaryWorldAutomation=False,ordinarySaveRestored=False,previousOrdinaryOwnedHandle=41323,
        previousOrdinaryHostJava=3488332,previousOrdinaryExit=0,
        interruptedFailedTestOwnedHandle=58826,interruptedFailedTestExit=None,
        testOwnedHandle=29657,testHostJava=1974135,testExit=0,
        ordinaryHostJava=pid,ordinaryOwnedHandle=handle,ordinaryLockFD=locks[0],normalPackSHA256=pack,
        normalPhysicsSHA256=sha(GAME/'mods/aqualumen-physics-0.2.0.jar'),allOptInEntryPointsAbsent=controls,
        runtimeScreenshot=runtime,pauseScreenshot=pause,rootInspectedRuntimeAndPause=True,
        pauseEventChronology=chronology,normalRuntimeConfigurationComparison=config,publicCPUCheckExitCodes=exits,
        openALDeviceUnavailable='Failed to open OpenAL device' in log,
        intendedNextAction='Join retained actual filtered material with unchanged original terrainLight/paired Sun, independent positive/rejection controls and coherent live geometry/resource ownership before source promotion')
    with (OUT/'checkpoint.json').open('x') as stream:
        json.dump(checkpoint,stream,indent=2,sort_keys=True)
    paths=sorted(p for p in OUT.rglob('*') if p.is_file())
    with (OUT/'SHA256SUMS').open('x') as stream:
        for path in paths:
            if path.is_symlink():
                raise ValueError('Evidence symlink rejected')
            stream.write(f'{sha(path)}  {path.relative_to(ROOT)}\n')
    print('Sealed',len(paths),'files; actual filtered material qualified; ordinary paused; full goal active')


if __name__=='__main__':
    finish(int(sys.argv[1]),int(sys.argv[2]),sys.argv[3],sys.argv[4])
