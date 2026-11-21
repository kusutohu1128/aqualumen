import csv
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import statistics
import sys

root=Path('/home/kusutohu/repos/aqualumen');sys.path.insert(0,str(root/'tools'))
from water_hit_depth_run import run,save,sha
from water_hit_depth_runtime import lab_java_processes
import water_paired_runtime as runtime

report=root/'reports/2026-10-22-water-hit-depth'
checks=report/'final-checks'
python='/tmp/aqualumen-optics-python.7uUOLF/bin/python'
for mode in ('baseline','candidate'):
    audit_path=report/(mode+'-near-audit-final.json')
    if audit_path.exists():
        existing=json.loads(audit_path.read_text())
        assert existing['auditScriptSHA256']==sha(root/'tools/water_hit_depth_audit.py')
        assert existing['manifestSHA256']==sha(report/('runtime-'+mode+'2')/'underwater-up-near-paired-capture/manifest.json')
        assert json.loads((checks/(mode+'-near-final-audit-receipt.json')).read_text())['exitCode']==0
    else:
        run([python,root/'tools/water_hit_depth_audit.py',report/('runtime-'+mode+'2')/'underwater-up-near-paired-capture',
            '--mode',mode,'--out',audit_path],checks,mode+'-near-final-audit')
audits={name:json.loads((report/(name+'.json')).read_text()) for name in
    ('baseline-near-audit-final','candidate-near-audit-final','baseline-deep-owned-audit','candidate-deep-owned-audit')}
assert audits['baseline-near-audit-final']['baselineReproductionPassed']
assert audits['baseline-deep-owned-audit']['baselineReproductionPassed']
assert audits['candidate-near-audit-final']['boundedDepthEyeConsistencyPassed']
assert audits['candidate-deep-owned-audit']['boundedDepthEyeConsistencyPassed']
assert all(value['auditScriptSHA256']==sha(root/'tools/water_hit_depth_audit.py') for value in audits.values())
for name in ('native-depth2','native-ownership3'):
    receipt=json.loads((report/name/'receipt.json').read_text());assert receipt['passed']
    assert all(sha(root/path if path.startswith('tools/') else root/'tools'/path)==pin for path,pin in receipt['sources'].items())
assert json.loads((checks/'unit-regression-receipt.json').read_text())['exitCode']==0
assert 'Ran 58 tests' in (checks/'unit-regression.stderr').read_text()
ordinary=json.loads((report/'runtime-candidate3/baseline.json').read_text())
assert not lab_java_processes(runtime.GAME)
assert runtime.prior.ordinary_tree()==ordinary['ordinarySave']
assert {p.name:sha(p) for p in (runtime.GAME/'mods').glob('*.jar')}==ordinary['mods']
assert {name:sha(runtime.GAME/name) for name in runtime.CONFIG}==ordinary['config']
assert sha(runtime.GAME.parent/'instance.cfg')==ordinary['instanceSHA256']
assert 'shaderPack=Aqualumen-0.6.0.zip' in (runtime.GAME/'config/iris.properties').read_text().splitlines()
assert not (runtime.GAME/'aqualumen-benchmark/request.properties').exists()
assert not any(p.name.startswith('aqualumen-') and (p.name.endswith('.enabled') or 'observe' in p.name and p.suffix=='.properties')
    for p in (runtime.GAME/'config').iterdir())
restored={}
for mode in ('baseline','candidate'):
    path=report/('runtime-'+mode+'3')/'restored.json';restored[mode]=json.loads(path.read_text())
    assert all(restored[mode][key] for key in ('normalConfigExact','normalModsExact','instanceExact','ordinarySaveExact'))
    assert restored[mode]['ordinarySaveRestored'] is False
    assert json.loads((path.parent/'launcher-exit.json').read_text())['exitCode']==0
prior=json.loads((root/'reports/2026-10-22-underwater-rim-fix/CLOSURE.json').read_text())
assert all(sha(root/path)==pin for path,pin in prior['originalSourcePins'].items())
physical_pins={
    'reports/2026-10-22-underwater-rim-fix/hit1/control.zip':'31540e3de53edec87d73087b1217072a45aee3a04f2b9e2ab7e93d4d6a06231e',
    'reports/2026-10-22-underwater-rim-fix/hit1/paired.zip':'9bf027a4905a420a43a6e67eb48155e545a210eb2e654fe7b69fb692e92490a2',
    'reports/2026-10-22-underwater-rim-fix/optical3/optical.zip':'4c35bd7cde0858fffddd8718c02ea3d61858fecc2683d35ec1472f0473a3af46'}
assert all(sha(root/path)==pin for path,pin in physical_pins.items())
timings=[]
for mode,generation,scene in [('baseline',2,'near'),('candidate',2,'near'),('baseline',3,'deep'),('candidate',3,'deep')]:
    directory=report/('runtime-'+mode+str(generation))/('underwater-up-'+scene+'-scene')
    metadata=json.loads((directory/'run.json').read_text());row=json.loads((directory/('underwater-up-'+scene+'.json')).read_text())
    assert metadata['world_id']==runtime.prior.WORLD_ID and metadata['shader_active'] and not metadata['shader_fallback']
    assert metadata['resolution']==[1600,900] and 'NVIDIA' in metadata['gl_renderer']
    assert metadata['pack_sha256']==json.loads((report/(mode+str(generation))/'manifest.json').read_text())['archives']['paired']
    path=directory/('underwater-up-'+scene+'.csv')
    with path.open() as stream:values=[int(item['ns']) for item in csv.DictReader(stream)]
    assert len(values)==row['frames'] and all(value>0 for value in values)
    assert abs(1e9*len(values)/sum(values)-row['mean_fps'])<1e-8
    timings.append(dict(mode=mode,generation=generation,scene=scene,frames=len(values),runs=1,
        csvSHA256=sha(path),sceneSHA256=sha(directory/('underwater-up-'+scene+'.json')),runSHA256=sha(directory/'run.json'),
        p50ms=statistics.median(values)*1e-6,p95ms=sorted(values)[math.ceil(len(values)*.95)-1]*1e-6,
        p99ms=row['p99_ms'],maxms=row['max_ms'],meanFPS=row['mean_fps'],limiter='unprofiled; no performance comparison accepted'))
save(report/'TIMING-OBSERVATIONS.json',dict(verdict='inconclusive',scope='Single instrumented correctness scenes, not production or ordinary0.6',
    width=1600,height=900,repeatedInterleavedRuns=False,ordinaryFPSMeasured=False,observations=timings))
tools=['water_depth_candidate.py','water_hit_depth_test.glsl','test_water_depth_candidate.py','water_hit_depth_runtime.py',
    'test_water_hit_depth_runtime.py','water_hit_depth_audit.py','test_water_hit_depth_audit.py','water_hit_depth_run.py',
    'water_hit_depth_native.cpp','water_hit_depth_ownership.py','test_water_hit_depth_ownership.py',
    'water_hit_depth_ownership_run.py','water_hit_depth_ownership_native.cpp']
closure=dict(schema='aqualumen-water-hit-depth-closure-v1',utc=datetime.now(timezone.utc).isoformat(),
    scope='Bounded frozen TEST primary hit/depth/eye attenuation and explicit known nonwater writer protocol, not all appearance/physical/release acceptance',
    renderer='NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2',nativeDepthPassed=True,nativeNonwaterWitnessPassed=True,
    actualNearDepthEyePassed=True,actualKnownWaterDeepDepthEyePassed=True,
    candidateNearWaterPixels=audits['candidate-near-audit-final']['waterPixels'],
    candidateDeepWaterPixels=audits['candidate-deep-owned-audit']['waterPixels'],
    candidateDeepKnownNonwaterWriterPixels=audits['candidate-deep-owned-audit']['lastKnownNonwaterDiagnosticWriterPixels'],
    originalSourcePinsMatched=True,originalSourcePins=prior['originalSourcePins'],previousFrozenArchivePins=physical_pins,
    currentToolSHA256={name:sha(root/'tools'/name) for name in tools},
    auditSHA256={name:sha(report/(name+'.json')) for name in audits},
    unitReceiptSHA256=sha(checks/'unit-regression-receipt.json'),focusedTests=58,
    finalLabJavaAbsent=True,normalConfigsExact=True,normalModsExact=True,instanceExact=True,ordinarySaveExact=True,
    ordinarySaveRestored=False,ordinaryPack='Aqualumen-0.6.0.zip',ordinaryPhysics='0.2.0',testControlsAbsent=True,
    runtime3LauncherExitCodes=dict(baseline=0,candidate=0),restored=restored,
    historicalGeneration2CandidateWrapperExitCodeObserved=False,
    actualOpaqueStraddleExercised=None,actualWaterDrawStateObserved=False,
    actualUninstrumentedVsInstrumentedWholeSceneC0Proof=False,
    fullVisualAccepted=False,fullPhysicalAccepted=False,performanceAccepted=False,releaseAccepted=False,
    openGates=['Frozen17s and zero interaction ripples, known deep water and limited footprint only.',
        'R2/secondary interfaces, raster coverage and headroom/contact containment, dynamic and general-world behavior.',
        'Actual water draw state and opaque straddles/ceiling remain unobserved; native fixture proves only its own pipeline.',
        'Known nonwater marker is not universal depth/beauty ownership; unmarked paths and depth-stencil mode remain open.',
        'Source incident height approximation and actual shadow radiance attribution remain outside this unit.',
        'Instrumented scenes are very slow and are not production FPS; no speedup/regression verdict or visual curl completion.'])
save(report/'CLOSURE.json',closure)
print('Closed bounded checks,58 tests and exact normal restoration; all full physical/visual/performance/release gates remain open')
