"""CPU-only checkpoint and revalidated ordinary handoff, no save restoration."""
import hashlib
import json
from pathlib import Path
import shutil
from water_source_boundary_finish import properties

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-06-water-observed-plane'


def finish():
    before = json.loads((ROOT / 'reports/2026-10-06-water-boundary-regression/fresh-normal-baseline.json').read_text())
    game, backup = Path(before['game']), Path(before['backup'])
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    for name in ('options.txt', 'config/aqualumen-benchmark.properties'):
        assert sha(game / name) == before['configSHA256'][name]
    assert properties(game / 'config/iris.properties') == properties(backup / 'config/iris.properties')
    assert {p.name: sha(p) for p in (game / 'mods').glob('*.jar')} == before['activeMods']
    for name in before['instrumentationEntryPointsAbsent']:
        assert not (game / 'config' / name).exists()
    for name in ('request.properties', 'opaque-test-journal.json'):
        assert not (game / 'aqualumen-benchmark' / name).exists()
    assert sha(game / 'shaderpacks/Aqualumen-0.6.0.zip') == '6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73'
    proc = Path('/proc/3229665')
    assert (proc / 'comm').read_text().strip() == 'java'
    assert (proc / 'fd/151').readlink() == game / 'saves/新規ワールド/session.lock'
    namespace = next(x for x in (proc / 'status').read_text().splitlines() if x.startswith('NSpid:')).split()[1:]
    assert namespace == ['3229665', '16']
    image = OUT / 'ordinary-pause-native-f2.png'
    assert not image.exists()
    shutil.copy2(game / 'screenshots/2026-10-06_13.45.18.png', image)
    log = (game / 'logs/latest.log').read_text()
    assert '2026-10-06_13.45.18.png' in log
    assert 'Using shaderpack: Aqualumen-0.6.0.zip' in log
    assert '[Aqualumen Physics] 0.2.0 contact bridge initialized' in log
    assert 'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti' in log
    with (OUT / 'ordinary-current.log').open('x') as stream:
        stream.write(log)
    result = dict(schema='aqualumen-observed-plane-checkpoint-v1',
        previousGoalTurnClassification='progress', currentGoalTurnClassification='progress',
        goalActive=True, fullGoalAchieved=False, CPUObservedPlanePartitionImplemented=True,
        boundaryAndFadeCPUSelectedGatesPassed=True, actualSSRPrecisionREDRetained=True,
        actualSSRPrecisionFixed=False, productionChanged=False, nativeGLExecuted=False,
        candidateInstalled=False, IrisCandidateAccepted=False, temporalAccepted=False,
        arbitraryGeometryProven=False, physicalEnergyAccepted=False,
        ordinaryHandoff=dict(ownedLauncherHandle=87409, hostJava=3229665, namespaceJava=16,
            ordinaryLockFD=151, window=62914567, display=':1', rootInspectedPause='2026-10-06 13:45:18 JST',
            pauseImageSHA256=sha(image), normalPack='0.6.0', normalPhysics='0.2.0',
            optionsAndBenchmarkBytesEqual=True, irisNoncommentPropertiesEqual=True,
            activeModAndPackHashesEqual=True, testEntryPointsAbsent=True,
            ordinarySaveIdentityIsHistorical=True, ordinaryWorldRestored=False,
            ordinaryWorldAutomation=False, standaloneNativeGLAfterHandoff=False))
    with (OUT / 'checkpoint.json').open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
    print('RECORDED CPU partition/gain progress and actual SSR precision RED; goal active')


if __name__ == '__main__':
    finish()
