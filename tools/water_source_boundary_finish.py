"""Read-only live normal-handoff qualification; never restore ordinary saves."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-06-water-source-boundary'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def properties(path):
    return sorted(line.strip() for line in path.read_text().splitlines()
                  if line.strip() and not line.lstrip().startswith('#'))


def tracer(text):
    start = text.index('vec4 reflectionTrace(')
    opening = text.index('{', start)
    end, level = opening + 1, 1
    while level:
        level += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def finish():
    baseline = json.loads((OUT / 'prelaunch.json').read_text())
    game, backup = Path(baseline['game']), Path(baseline['backup'])
    mods = {p.name: sha(p) for p in (game / 'mods').glob('*.jar')}
    assert mods == baseline['activeMods']
    for name in ('options.txt', 'config/aqualumen-benchmark.properties'):
        assert sha(game / name) == baseline['configSHA256'][name]
    assert properties(game / 'config/iris.properties') == properties(backup / 'config/iris.properties')
    assert 'shaderPack=Aqualumen-0.6.0.zip' in properties(game / 'config/iris.properties')
    pack = sha(game / 'shaderpacks/Aqualumen-0.6.0.zip')
    assert pack == '6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73'
    for name in baseline['instrumentationEntryPointsAbsent']:
        assert not (game / 'config' / name).exists()
    for name in ('request.properties', 'opaque-test-journal.json'):
        assert not (game / 'aqualumen-benchmark' / name).exists()
    proc = Path('/proc/3220839')
    assert (proc / 'comm').read_text().strip() == 'java'
    assert (proc / 'fd/154').readlink() == game / 'saves/新規ワールド/session.lock'
    nspid = next(x for x in (proc / 'status').read_text().splitlines() if x.startswith('NSpid:'))
    assert nspid.split()[1:] == ['3220839', '26']
    runtime = (OUT / 'ordinary-runtime/runtime.log').read_text()
    for marker in ('Using shaderpack: Aqualumen-0.6.0.zip',
                   '[Aqualumen Physics] 0.2.0 contact bridge initialized',
                   'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti',
                   '[13:24:13] [Server thread/INFO]: Saving and pausing game...'):
        assert marker in runtime
    assert 'Using shaderpack: (off)' not in runtime
    restored = json.loads((OUT / 'restoration-before-relaunch.json').read_text())
    assert restored['ordinarySavedFilesEqualFreshPostSaveBaseline']
    assert restored['ordinarySavedFileCount'] == 41
    assert not restored['ordinaryWorldRestored']
    production = ROOT / 'shaders/gbuffers_water.fsh'
    function = tracer(production.read_text())
    assert function == tracer((OUT / 'fixed-observer-12-v1/baseline.fsh').read_text())
    function_hash = hashlib.sha256(function.encode()).hexdigest()
    assert function_hash == '99d5a541c4bcc6f45869be60b74e79f9aa8d0d118ba6ba5d5cda943e0a44c158'
    with (OUT / 'production-water-at-handoff.fsh').open('xb') as output:
        output.write(production.read_bytes())
    comparisons = {str(order): json.loads((OUT / f'compare-{order}-v1.json').read_text())
                   for order in (8, 12)}
    for result in comparisons.values():
        assert result['newOutsideOrPreviouslyAbsentHitCount'] == 0
        assert not result['physicalKernelWeightsUnitsChanged']
    record = dict(schema='aqualumen-source-boundary-checkpoint-v1',
        goalActive=True, fullGoalAchieved=False,
        previousGoalTurnClassification='progress', currentGoalTurnClassification='progress',
        candidateInstalled=False, IrisCandidateAccepted=False,
        temporalAccepted=False, physicalEnergyAccepted=False,
        arbitraryGeometryAccepted=False, sourceConvergenceAccepted=False,
        affectedTenCaseSourcesPrepared=True, affectedTenCaseSourcesExecuted=False,
        qualifiedReflectionFunctionSHA256=function_hash,
        productionFragmentSHA256=sha(production), comparisons=comparisons,
        nativeRetainedPairsPassed=11, nativeLog='native-current-fix-check.log',
        ordinaryHandoff=dict(ownedLauncherHandle=54078, hostJava=3220839,
            namespaceJava=26, window=62914567, display=':1', ordinaryLockFD=154,
            runtimeRootInspected='2026-10-06 13:24:07 JST',
            finalPauseRootInspected='2026-10-06 13:24:13 JST',
            finalPauseSHA256=sha(OUT / 'ordinary-runtime/paused-native-f2.png'),
            packSHA256=pack, activeMods=mods,
            originalOptionsAndBenchmarkBytesEqual=True, irisNoncommentPropertiesEqual=True,
            testEntryPointsAbsent=True, ordinarySavedFileIdentityProvenBeforeRelaunch=True,
            ordinarySaveIdentityIsHistoricalAfterRelaunch=True,
            ordinarySaveRestored=False, ordinaryWorldAutomation=False,
            nativeGLAfterHandoff=False, preexistingOpenALFailureUnfixed=True))
    with (OUT / 'checkpoint.json').open('x') as output:
        json.dump(record, output, indent=2, sort_keys=True)
    print('RECORDED live normal handoff; qualified omission fixed; convergence/full goal unaccepted')


if __name__ == '__main__':
    finish()
