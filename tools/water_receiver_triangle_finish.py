"""CPU-only actual-input provenance and ordinary handoff; exclusive packet seal."""
import json
from pathlib import Path
import subprocess
import sys
from water_receiver_triangle_audit import ROOT, OUT, audit, sha
from water_receiver_sun_finish import copy
from water_receiver_texture_lifecycle import GAME
from water_normal_pause_event import verify_pause_event

def main(pid,handle,runtime,pause):
    if (OUT/'SHA256SUMS').exists():raise ValueError('Never overwrite sealed evidence')
    for name in (runtime,pause):
        if Path(name).name!=name or not name.startswith('2026-10-06_'):raise ValueError('Exact inspected screenshot names required')
    baseline=json.loads((OUT/'fresh-normal-baseline.json').read_text())
    for name in ('normal-exact-after-native.json','normal-exact-before-reopening.json'):
        if json.loads((OUT/name).read_text())!=baseline:raise ValueError('Ordinary snapshot not exact before reopen')
    if len(baseline['ordinarySavedFilesSHA256'])!=41:raise ValueError('Ordinary snapshot scope changed')
    controls=baseline['instrumentationEntryPointsAbsent']+['aqualumen-receiver-material-probe.properties',
        'aqualumen-receiver-mesher-probe.properties','aqualumen-receiver-draw-probe.properties']
    if any((GAME/'config'/n).exists() for n in controls):raise ValueError('TEST opt-in remains')
    if {p.name:sha(p) for p in (GAME/'mods').glob('*.jar')}!=baseline['activeMods']:raise ValueError('Normal Mod set changed')
    config_receipt={}
    for name,digest in baseline['configSHA256'].items():
        current=sha(GAME/name);timestamp=False
        if current!=digest:
            if name!='config/iris.properties':raise ValueError('Ordinary config changed')
            before=(Path(baseline['backup'])/name).read_text().splitlines();after=(GAME/name).read_text().splitlines()
            if len(before)!=len(after) or len(before)<3 or before[0]!=after[0] or before[2:]!=after[2:] or not before[1].startswith('#Tue Oct 06 ') or not after[1].startswith('#Tue Oct 06 '):
                raise ValueError('Iris actual setting changed, not only startup timestamp')
            timestamp=True
        config_receipt[name]=dict(beforeSHA256=digest,runtimeSHA256=current,exactBytes=current==digest,onlyIrisStartupTimestampChanged=timestamp)
    pack=sha(GAME/'shaderpacks/Aqualumen-0.6.0.zip')
    if pack!='6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73':raise ValueError('Normal pack changed')
    proc=Path('/proc')/str(pid)
    if (proc/'comm').read_text().strip()!='java':raise ValueError('Normal Java not live')
    locks=[]
    for p in (proc/'fd').iterdir():
        try: target=p.readlink()
        except FileNotFoundError: continue  # Unrelated transient FD; ownership is still mandatory below.
        if target==GAME/'saves/新規ワールド/session.lock':locks.append(int(p.name))
    if len(locks)!=1:raise ValueError('Actual ordinary ownership not proven')
    log=(GAME/'logs/latest.log').read_text();chronology=verify_pause_event(log,runtime,pause)
    if ('OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti' not in log or 'Using shaderpack: Aqualumen-0.6.0.zip' not in log
            or '0.2.0 contact bridge initialized' not in log or 'OpenGL debug message' in log
            or any(s in log for s in ('aqualumen_receiver_draw_probe','aqualumen_receiver_mesher_probe','aqualumen_receiver_material_probe'))):
        raise ValueError('Actual ordinary NVIDIA/Iris/physics activation not proved')
    result=audit()
    if json.loads((OUT/'independent-triangle-audit.json').read_text())!=result:raise ValueError('Saved independent audit changed')
    native=json.loads((OUT/'native-v1-receipt.json').read_text())
    for name,digest in native['sourceSHA256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Executed native fixture/helper source changed')
    contract=json.loads((OUT/'input-contract.json').read_text())
    if sha(ROOT/'tools/ReceiverIndexReference.java')!=contract['referenceSourceSHA256']:raise ValueError('Actual index-reference source changed')
    previous=ROOT/'reports/2026-10-06-water-receiver-sun/native-v1/receipt.json'
    for name,digest in json.loads(previous.read_text())['sourceSHA256'].items():
        if name.startswith('shaders/') and sha(ROOT/name)!=digest:raise ValueError('Retained shader qualification no longer current')
    increments={}
    for label in [f'triangle-{p}{i}' for i in (1,2,3) for p in ('red','green')]+['triangle-final']:
        receipt=json.loads((OUT/label/'receipt.json').read_text());expected=1 if 'red' in label else 0
        if receipt['exitCode']!=expected:raise ValueError('Public increment result changed')
        for name,digest in receipt['sourceSHA256'].items():
            if sha(OUT/label/'source'/name)!=digest:raise ValueError('Frozen increment changed')
            if label=='triangle-final' and sha(ROOT/name)!=digest:raise ValueError('Final public CPU source changed')
        increments[label]=expected
    exits={}
    for name,command in {
        'triangle':['bash','tools/test-receiver-triangle.sh'],
        'triangle-gradient':['bash','tools/test-receiver-triangle-gradient.sh'],
        'public-triangle-audit':['python3','tools/test_water_receiver_triangle_audit.py'],
        'retained-pause':['python3','tools/test_water_normal_pause_event.py'],
        'whitespace':['git','diff','--check']}.items():
        run=subprocess.run(['rtk','proxy',*command],cwd=ROOT,capture_output=True)
        with (OUT/(name+'-green.log')).open('xb') as stream:stream.write(run.stdout+run.stderr)
        exits[name]=run.returncode
        if run.returncode:raise ValueError('Final CPU check failed: '+name)
    copy(GAME/'logs/latest.log',OUT/'normal-final-runtime.log')
    copy(Path(baseline['backup'])/'config/iris.properties',OUT/'iris-before-normal-reopen.properties')
    copy(GAME/'config/iris.properties',OUT/'iris-after-normal-reopen.properties')
    for original,name in ((runtime,'normal-runtime.png'),(pause,'normal-pause.png'),
        ('2026-10-06_17.42.30.png','normal-save-quit-focus.png'),('2026-10-06_17.44.37.png','normal-title-quit-focus.png')):
        copy(GAME/'screenshots'/original,OUT/name)
    sources=[ROOT/'README.md',ROOT/'docs/REALISM_GOAL.md',ROOT/'docs/RECEIVER_FIELD.md',
        ROOT/'physics-mod/dev/aqualumen/physics/ReceiverTriangle.java',ROOT/'physics-mod/dev/aqualumen/physics/ReceiverVertexShader.java',
        *sorted((ROOT/'physics-mod/test/dev/aqualumen/physics').glob('ReceiverTriangle*.java')),
        *sorted((ROOT/'tools').glob('water_receiver_triangle*.py')),
        ROOT/'tools/test_water_receiver_triangle_audit.py',ROOT/'tools/ReceiverIndexReference.java',ROOT/'tools/receiver-triangle-gpu.cpp',
        ROOT/'tools/test-receiver-triangle.sh',ROOT/'tools/test-receiver-triangle-gradient.sh',
        ROOT/'tools/water_normal_pause_event.py',ROOT/'tools/water_receiver_sun_finish.py',
        ROOT/'tools/water_receiver_sun_audit.py',ROOT/'tools/water_receiver_texture_lifecycle.py',ROOT/'tools/water_legacy_branch_snapshot.py']
    for source in dict.fromkeys(sources):copy(source,OUT/'final-source'/source.relative_to(ROOT))
    checkpoint=dict(fullGoalAchieved=False,previousGoalTurnClassification='progress',actualInstalledIndexGeneratorQualified=True,
        actualArchivedInputFaces=14,savedFirstReceiverPoints=16,supplementalPoints=42,qualifiedGPUInterpolantFloats=928,
        maximumGPUScalarError=result['maximumGPUScalarError'],maximumOppositeDiagonalDifference=result['maximumOppositeDiagonalDifference'],
        sourceRadiance=False,filteredFragmentFetchProven=False,dynamicIrisSourceBinding=False,
        liveMeshResourceEpochProven=False,originalLiveIndexBufferRead=False,originalTerrainFragmentInvocation=False,
        productionNaturalVisualFixAccepted=False,newMinecraftFrameTimings=False,
        standaloneNativeGLExecutedThisCycle=True,standaloneNativeGLAfterNormalRelaunch=False,
        noTestWorldClientLaunched=True,noProbeJarOrOptInInstalled=True,ordinaryWorldAutomation=False,ordinarySaveRestored=False,
        ordinarySavedFilesExactBeforeReopening=True,ordinarySavedFileCount=41,previousOrdinaryOwnedHandle=1355,
        previousOrdinaryHostJava=3470645,previousOrdinaryExit=0,nativeOwnedHandle=95321,nativeExit=0,
        ordinaryHostJava=pid,ordinaryOwnedHandle=handle,ordinaryLockFD=locks[0],normalPackSHA256=pack,
        normalPhysicsSHA256=sha(GAME/'mods/aqualumen-physics-0.2.0.jar'),allOptInEntryPointsAbsent=controls,
        runtimeScreenshot=runtime,pauseScreenshot=pause,rootInspectedRuntimeAndPause=True,pauseEventChronology=chronology,
        normalRuntimeConfigurationComparison=config_receipt,publicCPUCheckExitCodes=exits,incrementExitCodes=increments,
        nativeCompilerWarningCount=3,openALDeviceUnavailable='Failed to open OpenAL device' in log,
        intendedNextAction='Join actual filtered material and shared original terrainLight/direct-Sun with coherent live ownership before dynamic per-face source upload')
    with (OUT/'checkpoint.json').open('x') as stream:json.dump(checkpoint,stream,indent=2,sort_keys=True)
    paths=sorted(p for p in OUT.rglob('*') if p.is_file())
    with (OUT/'SHA256SUMS').open('x') as stream:
        for p in paths:
            if p.is_symlink():raise ValueError('Evidence symlink rejected')
            stream.write(f'{sha(p)}  {p.relative_to(ROOT)}\n')
    print('Sealed',len(paths),'files; face interpolation qualified; ordinary paused; full goal active')

if __name__=='__main__':main(int(sys.argv[1]),int(sys.argv[2]),sys.argv[3],sys.argv[4])
