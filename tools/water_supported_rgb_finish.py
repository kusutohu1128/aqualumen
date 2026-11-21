"""Final CPU-only evidence and ordinary handoff record for this TEST slice."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import water_legacy_branch_restore_audit as restore

def settings(p):
    return dict(line.split('=',1) for line in p.read_text().splitlines() if '=' in line and not line.startswith('#'))
def finish(root):
    root=Path(root);game=restore.GAME;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    baseline=json.loads((root/'prelaunch.json').read_text())
    for name in ('options.txt','config/aqualumen-benchmark.properties'):assert sha(game/name)==baseline['configSHA256'][name]
    assert settings(game/'config/iris.properties')==settings(Path(baseline['backup'])/'config/iris.properties')
    assert {p.name:sha(p) for p in (game/'mods').glob('*.jar')}==baseline['activeMods']
    assert not any((game/'config'/n).exists() for n in baseline['instrumentationEntryPointsAbsent'])
    assert not (game/'aqualumen-benchmark/request.properties').exists()
    assert '/saves/新規ワールド/session.lock' in (root/'ordinary-world-open-files.txt').read_text()
    log=(root/'ordinary-game.log').read_text()
    for token in ('aqualumen_physics 0.2.0','Using shaderpack: Aqualumen-0.6.0.zip',
        'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti','OpenGL Version: 3.2.0 NVIDIA',
        'Preparing start region for dimension minecraft:overworld','0.2.0 contact bridge initialized'):assert token in log,token
    images={}
    for name in ('ordinary-runtime.png','ordinary-paused.png'):
        p=root/name;b=p.read_bytes();assert b[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',b[16:24])==(1600,900)
        images[name]=sha(p)
    current=json.loads((root/'main-02-audit-v3.json').read_text())
    assert current['actualOriginalMainRGBSourceResponsesQualified'] and current['freshDirectTESBitsMatchOriginalParent']
    before=json.loads((root/'restoration-before-relaunch.json').read_text())
    assert before['ordinarySavedFilesEqualFreshPostSaveBaseline'] and not before['ordinaryWorldRestored']
    return dict(schema='aqualumen-supported-rgb-checkpoint-v1',
        goalTurnClassification='progress',newRAndTOperatorImplemented=True,
        originalMainControlledSourceGreen=True,scope='One native TEST evaluation pixel; actual source geometry/Sun48 adapter still required.',
        freshTESDepthAndSourceInputsExact=True,ordinaryWorldRestored=False,ordinaryWorldAutomation=False,
        ordinarySavedTreeEqualBeforeReopening=True,normalPack='Aqualumen-0.6.0.zip',normalPhysics='0.2.0',
        originalOptionsBenchmarkBytesEqual=True,irisSemanticValuesEqual=True,testEntryPointsAbsent=True,
        normalReopenedGameLogQualified=True,ordinaryWorldLiveFileHandleQualified=True,
        ownedOrdinaryLauncherSession=88646,ordinaryImagesInspectedByRoot=True,ordinaryImageHashes=images,
        soundInitializationSucceeded='Failed to open OpenAL device' not in log,
        newCandidateIrisInstalled=False,newCandidateMinecraftIntervalsCaptured=False,
        physicalSourceTracingValidated=False,Sun48RoutingValidated=False,physicalEnergyAccepted=False,
        naturalWaterAccepted=False,motionAccepted=False,shippingAccepted=False,fullGoalAchieved=False)
if __name__=='__main__':print(json.dumps(finish(sys.argv[1]),indent=2,sort_keys=True))
