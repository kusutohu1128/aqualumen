"""Read-only fresh ordinary handoff and full-goal limitations receipt."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
from water_source_boundary_finish import properties
from water_path_precision_prepare import ROOT, OUT, GAME, tracer


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finish(pid, session, runtime, pause):
    baseline = json.loads((OUT/'fresh-normal-baseline.json').read_text())
    for name in ('normal-before-iris.json','normal-after-iris.json','normal-final-prelaunch.json'):
        assert json.loads((OUT/name).read_text()) == baseline
    backup = Path(baseline['backup'])
    for name in ('options.txt','config/aqualumen-benchmark.properties'):
        assert sha(GAME/name) == baseline['configSHA256'][name]
    assert properties(GAME/'config/iris.properties') == properties(backup/'config/iris.properties')
    assert {p.name:sha(p) for p in (GAME/'mods').glob('*.jar')} == baseline['activeMods']
    for name in baseline['instrumentationEntryPointsAbsent']:
        assert not (GAME/'config'/name).exists()
    for name in ('request.properties','opaque-test-journal.json','opaque-fixture-journal.json'):
        assert not (GAME/'aqualumen-benchmark'/name).exists()
    assert sha(GAME/'shaderpacks/Aqualumen-0.6.0.zip') == '6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73'
    proc = Path(f'/proc/{pid}')
    assert (proc/'comm').read_text().strip() == 'java'
    ordinary = GAME/'saves/新規ワールド/session.lock'
    locks = []
    for path in (proc/'fd').iterdir():
        try:
            if path.readlink() == ordinary:
                locks.append(int(path.name))
        except FileNotFoundError:
            pass
    assert locks
    namespace = next(l for l in (proc/'status').read_text().splitlines() if l.startswith('NSpid:')).split()[1:]
    log = (GAME/'logs/latest.log').read_text()
    for text in ('Using shaderpack: Aqualumen-0.6.0.zip','OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti',
                 '[Aqualumen Physics] 0.2.0 contact bridge initialized','Saving and pausing game...'):
        assert text in log
    for text in ('Using shaderpack: (off)','Shader compilation failed','Shader compilation error'):
        assert text not in log
    images = {}
    for name,role in ((runtime,'normal-runtime-native-f2.png'),(pause,'normal-pause-native-f2.png')):
        assert re.fullmatch(r'2026-10-06_[0-9]{2}\.[0-9]{2}\.[0-9]{2}\.png',name) and name in log
        assert not (OUT/role).exists()
        shutil.copy2(GAME/'screenshots'/name,OUT/role)
        images[role] = dict(original=name,sha256=sha(OUT/role))
    with (OUT/'normal-runtime.log').open('x') as f:
        f.write(log)
    precision = json.loads((OUT/'precision-comparison.json').read_text())
    assert precision['centerOpticalGates'] == 85 and precision['exactOldNewComparisons'] == 10246
    current = tracer((ROOT/'shaders/gbuffers_water.fsh').read_text())
    assert current == tracer((OUT/'production-refine12.fsh').read_text())
    assert hashlib.sha256(current.encode()).hexdigest() == precision['candidateFunctionSHA256']
    iris = json.loads((OUT/'iris1440-audit.json').read_text())
    motion = json.loads((OUT/'motion900-audit.json').read_text())
    assert iris['sceneCount'] == 9 and iris['intervalCount'] == 3478
    assert motion['videoFrames'] == 480 and motion['videoSeconds'] == 20
    receipt = dict(schema='aqualumen-path-precision-checkpoint-v1',previousGoalTurnClassification='no_progress',
        previousTurnScope='Permission explanation only; preceding CPU/precision RED was concrete progress.',
        currentGoalTurnClassification='progress',goalActive=True,fullGoalAchieved=False,
        productionSSRRefinements=12,productionFunctionSHA256=precision['candidateFunctionSHA256'],
        actualNvidiaOriginalMAINPrecisionGatePassed=True,centerOpticalGates=85,
        zeroPositiveSourcesAndRetainedHitClassesPassed=True,retainedNative11PairsAndBehaviorPassed=True,
        closedBlackFirstRedBackgroundNegativePassed=True,actualIris1440Qualification=iris,
        separate900MotionCapture=motion,candidateTestOnly=True,normalReleaseChanged=False,
        generalFirstObjectAccepted=False,practicalSourceIntegrationAccepted=False,
        naturalAppearanceAccepted=False,wholeMotionAccepted=False,energyAccepted=False,
        ordinaryHandoff=dict(ownedLauncherHandle=session,hostJava=pid,namespacePIDs=namespace,
            ordinaryLockFDs=locks,window=62914567,display=':1',rootInspectedRuntimeAndPause=True,images=images,
            normalPack='0.6.0',normalPhysics='0.2.0',originalOptionsAndBenchmarkBytesEqual=True,
            irisNoncommentPropertiesEqual=True,originalAssetsQualified=True,
            ordinarySavedTreeEqualBeforeReopening=True,saveIdentityHistoricalAfterReopening=True,
            ordinaryWorldRestored=False,ordinaryWorldAutomation=False,TESTEntryPointsDisabled=True,
            requestAndJournalsAbsent=True,testLauncherExit=0,testJava3247904Absent=not Path('/proc/3247904').exists(),
            nativeGLAfterOrdinaryRelaunch=False,preexistingOpenALFailureUnfixed='Failed to open OpenAL device' in log))
    with (OUT/'checkpoint.json').open('x') as f:
        json.dump(receipt,f,indent=2,sort_keys=True)
    print('Recorded real GPU precision fix, actual9 Iris scenes, separate motion recording and normal safe handoff; full goal ACTIVE')


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('pid',type=int);p.add_argument('session',type=int)
    p.add_argument('runtime');p.add_argument('pause');a=p.parse_args()
    finish(a.pid,a.session,a.runtime,a.pause)
