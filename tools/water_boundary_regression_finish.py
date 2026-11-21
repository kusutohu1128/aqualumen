"""Read-only final live handoff verification and frozen diagnostic receipt."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
from water_source_boundary_finish import properties, tracer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-06-water-boundary-regression'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finish(pid, session, runtime_image, paused_image):
    before = json.loads((OUT / 'fresh-normal-baseline.json').read_text())
    for name in ('normal-prelaunch.json', 'normal-after-refinement.json', 'normal-final-prelaunch.json'):
        assert json.loads((OUT / name).read_text()) == before
    game, backup = Path(before['game']), Path(before['backup'])
    for name in ('options.txt', 'config/aqualumen-benchmark.properties'):
        assert sha(game / name) == before['configSHA256'][name]
    assert properties(game / 'config/iris.properties') == properties(backup / 'config/iris.properties')
    assert 'shaderPack=Aqualumen-0.6.0.zip' in properties(game / 'config/iris.properties')
    assert {p.name: sha(p) for p in (game / 'mods').glob('*.jar')} == before['activeMods']
    for name in before['instrumentationEntryPointsAbsent']:
        assert not (game / 'config' / name).exists()
    for name in ('request.properties', 'opaque-test-journal.json'):
        assert not (game / 'aqualumen-benchmark' / name).exists()
    assert sha(game / 'shaderpacks/Aqualumen-0.6.0.zip') == '6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73'
    proc = Path(f'/proc/{pid}')
    assert (proc / 'comm').read_text().strip() == 'java'
    lock = game / 'saves/新規ワールド/session.lock'
    locks = []
    for path in (proc / 'fd').iterdir():
        try:
            if path.readlink() == lock:
                locks.append(int(path.name))
        except FileNotFoundError:
            pass
    assert locks
    namespace = next(line for line in (proc / 'status').read_text().splitlines() if line.startswith('NSpid:')).split()[1:]
    log = (game / 'logs/latest.log').read_text()
    for marker in ('Using shaderpack: Aqualumen-0.6.0.zip',
                   'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti',
                   '[Aqualumen Physics] 0.2.0 contact bridge initialized',
                   'Saving and pausing game...'):
        assert marker in log
    for marker in ('Using shaderpack: (off)', 'Shader compilation failed', 'Shader compilation error'):
        assert marker not in log
    images = {}
    for role, name in (('runtime-native-f2.png', runtime_image), ('paused-native-f2.png', paused_image)):
        assert re.fullmatch(r'2026-10-06_[0-9]{2}\.[0-9]{2}\.[0-9]{2}\.png', name)
        assert name in log
        target = OUT / role
        assert not target.exists()
        shutil.copy2(game / 'screenshots' / name, target)
        images[role] = dict(original=name, sha256=sha(target))
    with (OUT / 'normal-runtime.log').open('x') as output:
        output.write(log)
    ten = json.loads((OUT / 'main-01-audit.json').read_text())
    assert ten['retainedSourceAudit']['exactRawComparisons'] == 920
    assert ten['denseSelectedTransmissionGatesPassed']
    dense = json.loads((OUT / 'dense-refinement-audit.json').read_text())
    assert dense['exactRawGeometryInputAndNonRuleComparisons'] == 234
    assert [r['order'] for r in dense['records']] == [96, 128, 192]
    assert not dense['convergenceCertified']
    current = tracer((ROOT / 'shaders/gbuffers_water.fsh').read_text())
    assert hashlib.sha256(current.encode()).hexdigest() == '99d5a541c4bcc6f45869be60b74e79f9aa8d0d118ba6ba5d5cda943e0a44c158'
    record = dict(schema='aqualumen-boundary-regression-checkpoint-v1',
        previousGoalTurnClassification='no_progress',
        previousTurnScope='Permission explanation only; preceding shader implementation was progress.',
        currentGoalTurnClassification='progress', goalActive=True, fullGoalAchieved=False,
        affectedTenCaseSourcesExecuted=True, actualRawComparisons=920,
        denseSelectedTransmissionGatesPassed=True, denseReflectionRefinement=dense,
        sourceConvergenceAccepted=False, arbitraryGeometryAccepted=False,
        candidateInstalled=False, IrisCandidateAccepted=False, temporalAccepted=False,
        physicalEnergyAccepted=False, naturalAppearanceAccepted=False,
        ordinaryHandoff=dict(ownedLauncherHandle=session, hostJava=pid,
            namespacePIDs=namespace, ordinaryLockFDs=locks, window=62914567, display=':1',
            rootInspectedRuntimeAndPause=True, images=images,
            originalOptionsAndBenchmarkBytesEqual=True, irisNoncommentPropertiesEqual=True,
            normalPack='0.6.0', normalPhysics='0.2.0', testEntryPointsAbsent=True,
            normalSavedTreeEqualBeforeReopening=True, saveIdentityHistoricalAfterReopening=True,
            ordinaryWorldRestored=False, ordinaryWorldAutomation=False,
            oldOwnedLauncherExit=0, nativeGLAfterHandoff=False,
            preexistingOpenALFailureUnfixed='Failed to open OpenAL device' in log))
    with (OUT / 'checkpoint.json').open('x') as output:
        json.dump(record, output, indent=2, sort_keys=True)
    print('RECORDED affected10/native refinement progress and live ordinary safe handoff; full goal active')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('pid', type=int)
    parser.add_argument('session', type=int)
    parser.add_argument('runtime_image')
    parser.add_argument('paused_image')
    args = parser.parse_args()
    finish(args.pid, args.session, args.runtime_image, args.paused_image)
