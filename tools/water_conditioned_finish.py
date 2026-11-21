"""CPU-only checkpoint and live ordinary handoff checks; no GL or save writes."""
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import water_legacy_branch_restore_audit as restore


def finish(root,pid,session):
    root=Path(root);game=restore.GAME
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    base=json.loads((root/'prelaunch.json').read_text())
    pre=json.loads((root/'restoration-before-relaunch.json').read_text())
    assert pre['ordinarySavedFilesEqualFreshPostSaveBaseline'] and not pre['ordinaryWorldRestored']
    for name in ('options.txt','config/aqualumen-benchmark.properties'):
        assert sha(game/name)==base['configSHA256'][name]
    def props(path):
        return dict(line.split('=',1) for line in path.read_text().splitlines() if '=' in line and not line.startswith('#'))
    assert props(game/'config/iris.properties')==props(Path(base['backup'])/'config/iris.properties')
    assert {p.name:sha(p) for p in (game/'mods').glob('*.jar')}==base['activeMods']
    assert sha(game/'shaderpacks/Aqualumen-0.6.0.zip')=='6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73'
    assert not any((game/'config'/n).exists() for n in base['instrumentationEntryPointsAbsent'])
    assert not (game/'aqualumen-benchmark/request.properties').exists()
    os.kill(pid,0);status=Path(f'/proc/{pid}/status').read_text();assert 'Name:\tjava' in status
    assert os.readlink(f'/proc/{pid}/fd/154')==str(game/'saves/新規ワールド/session.lock')
    log=(root/'ordinary-game.log').read_text()
    for token in ('aqualumen_physics 0.2.0','Using shaderpack: Aqualumen-0.6.0.zip',
        'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti','OpenGL Version: 3.2.0 NVIDIA',
        'Preparing start region for dimension minecraft:overworld','0.2.0 contact bridge initialized'):
        assert token in log,token
    image_hashes={}
    for name in ('ordinary-runtime.png','ordinary-paused.png'):
        data=(root/name).read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',data[16:24])==(1600,900)
        image_hashes[name]=sha(root/name)
    gpu=json.loads((root/'gpu-capture-02-audit.json').read_text());assert gpu['allSelectedNodeGatesPassed']
    old=json.loads((root/'gpu-capture-01-audit.json').read_text());assert not old['allSelectedNodeGatesPassed']
    main=json.loads((root/'source-64-main-01-final-audit.json').read_text())
    assert main['finiteProposalAndCapGatesPassed'] and not main['denseCoefficientGatesPassed']
    reflection=json.loads((root/'reflector-64-01-audit.json').read_text())
    assert reflection['actualSeparateReflectedSourceResponseQualified']
    timing=json.loads((root/'timing-64-01-audit.json').read_text());assert timing['currentMAINWitnessExact']
    assert '11 program pairs compiled and linked' in (root/'native-regressions.log').read_text()
    return dict(schema='aqualumen-conditioned-checkpoint-v1',normalPack='0.6.0',normalPhysics='0.2.0',
        noCandidateInstalled=True,TESTEntryPointsAbsent=True,optionsBenchmarkByteIdentity=True,irisSemanticIdentity=True,
        normalAssetHashesEqual=True,ordinarySaveIdentityBeforeReopening=True,ordinarySaveRestored=False,
        ordinaryWorldAutomation=False,ownedLauncherSession=session,hostJavaPID=pid,windowID=62914567,
        ordinaryWorldLockFD=154,ordinaryImageHashes=image_hashes,rootInspectedRuntime='2026-10-06T12:34:13+09:00',
        rootInspectedPaused='2026-10-06T12:34:37+09:00',nativeGLAfterHandoff=False,
        standaloneSelectedNodeGatesPassed=True,scalarNodeComparisons=gpu['scalarComparisons'],
        finiteOriginalMAINSourceReplayQualified=True,dense64SampleConvergenceQualified=False,
        actualReflectedSourcePositiveQualified=True,nativeOnePixelDraw=timing['nativeDraws'],
        soundInitializationSucceeded='Failed to open OpenAL device' not in log,
        candidateIrisExecuted=False,newMinecraftFPSMeasured=False,naturalVisualAccepted=False,
        temporalAccepted=False,physicalEnergyAccepted=False,fullGoalAchieved=False,
        scope='Same-model TEST sampler GPU/source progress, not natural renderer completion. Safe normal handoff independently checked; old rejected packets retained.')


if __name__=='__main__':
    root=Path(sys.argv[1]);result=finish(root,int(sys.argv[2]),int(sys.argv[3]))
    with (root/'checkpoint.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True)
    print('PASS bounded sampler progress and live normal handoff; full goal remains open')
