"""Record live normal handoff and bounded results. No game/GPU mutations."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/2026-10-06-water-fast-inverse'


def finish():
    baseline=json.loads((OUT/'prelaunch.json').read_text())
    game=Path(baseline['game']);backup=Path(baseline['backup'])
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    mods={p.name:sha(p) for p in (game/'mods').glob('*.jar')}
    assert mods==baseline['activeMods']
    for name in ('options.txt','config/aqualumen-benchmark.properties'):
        assert sha(game/name)==baseline['configSHA256'][name]
    def properties(path):
        return sorted(x.strip() for x in path.read_text().splitlines()
            if x.strip() and not x.lstrip().startswith('#'))
    assert properties(game/'config/iris.properties')==properties(backup/'config/iris.properties')
    assert 'shaderPack=Aqualumen-0.6.0.zip' in properties(game/'config/iris.properties')
    pack=sha(game/'shaderpacks/Aqualumen-0.6.0.zip')
    assert pack=='6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73'
    for name in baseline['instrumentationEntryPointsAbsent']:
        assert not (game/'config'/name).exists()
    assert not (game/'aqualumen-benchmark/request.properties').exists()
    assert not (game/'aqualumen-benchmark/opaque-test-journal.json').exists()
    proc=Path('/proc/3202154')
    assert (proc/'comm').read_text().strip()=='java'
    assert (proc/'fd/154').readlink()==game/'saves/新規ワールド/session.lock'
    nspid=next(x for x in (proc/'status').read_text().splitlines() if x.startswith('NSpid:'))
    assert nspid.split()[1:]==['3202154','26']
    parents=[];pid=3202154
    for _ in range(6):
        path=Path(f'/proc/{pid}')
        if not path.exists():break
        status=(path/'status').read_text().splitlines()
        parent=int(next(x for x in status if x.startswith('PPid:')).split()[1])
        parents.append(dict(pid=pid,parent=parent,comm=(path/'comm').read_text().strip()))
        if parent<=1:break
        pid=parent
    runtime=(OUT/'ordinary-runtime/runtime.log').read_text()
    assert 'Using shaderpack: Aqualumen-0.6.0.zip' in runtime
    assert '[Aqualumen Physics] 0.2.0 contact bridge initialized' in runtime
    assert 'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti' in runtime
    assert 'Using shaderpack: (off)' not in runtime
    inverse=json.loads((OUT/'paired-timing-01-audit.json').read_text())
    probability=json.loads((OUT/'probability-timing-02-audit.json').read_text())
    dense=json.loads((OUT/'main-probability-8-01-audit.json').read_text())
    reflection={}
    for name in ('fast64','probability8','probability12'):
        reflection[name]=json.loads((OUT/f'reflector-{name}-01-audit.json').read_text())
    record=dict(schema='aqualumen-fast-inverse-checkpoint-v1',goalActive=True,
        fullGoalAchieved=False,priorGoalTurnClassification='progress',
        currentGoalTurnClassification='progress',candidateInstalled=False,
        nativeInverseSelectedGatesPassed=True,denseSelectedTransmissionGatesPassed=True,
        actualSourceBoundaryConvergenceAccepted=False,IrisCandidateAccepted=False,
        temporalAccepted=False,physicalEnergyAccepted=False,shippingAccepted=False,
        inverseABBA=inverse,probabilityABBA=probability,
        denseSelectedComparisons=dense['denseComparisons'],reflection=reflection,
        nativeRegressionLog='native-check.log',
        ordinaryHandoff=dict(ownedLauncherHandle=16740,hostJava=3202154,namespaceJava=26,
            window=62914567,display=':1',ordinaryLockFD=154,parentChain=parents,
            runtimeRootInspected='2026-10-06 13:01:38 JST',
            finalPauseRootInspected='2026-10-06 13:02:13 JST',
            finalPauseSHA256=sha(OUT/'ordinary-runtime/paused-final-native-f2.png'),
            packSHA256=pack,activeMods=mods,originalOptionsAndBenchmarkBytesEqual=True,
            irisNoncommentPropertiesEqual=True,testEntryPointsAbsent=True,
            ordinarySavedFileIdentityProvenBeforeRelaunch=True,
            ordinarySaveIdentityIsHistoricalAfterRelaunch=True,
            ordinarySaveRestored=False,ordinaryWorldAutomation=False,
            nativeGLAfterHandoff=False,preexistingOpenALFailureUnfixed=True))
    with (OUT/'checkpoint.json').open('x') as f:json.dump(record,f,indent=2,sort_keys=True)
    print('RECORDED normal handoff / selected T progress / reflection convergence rejected / goal active')


if __name__=='__main__':finish()
