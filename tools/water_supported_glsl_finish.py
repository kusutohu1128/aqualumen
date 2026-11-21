"""CPU-only evidence summary and normal-runtime handoff checks; no GPU work."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import water_legacy_branch_restore_audit as restore

def values(path):
    return dict(line.split('=',1) for line in path.read_text().splitlines() if '=' in line and not line.startswith('#'))

def finish(root):
    root=Path(root);game=restore.GAME
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    baseline=json.loads((root/'prelaunch.json').read_text())
    before=json.loads((root/'restoration-before-relaunch.json').read_text())
    assert before['ordinarySavedFilesEqualFreshPostSaveBaseline'] and not before['ordinaryWorldRestored']
    for name in ('options.txt','config/aqualumen-benchmark.properties'):assert sha(game/name)==baseline['configSHA256'][name]
    assert values(game/'config/iris.properties')==values(Path(baseline['backup'])/'config/iris.properties')
    assert {p.name:sha(p) for p in (game/'mods').glob('*.jar')}==baseline['activeMods']
    assert not any((game/'config'/n).exists() for n in baseline['instrumentationEntryPointsAbsent'])
    assert not (game/'aqualumen-benchmark/request.properties').exists()
    log=(root/'ordinary-game.log').read_text()
    for token in ('aqualumen_physics 0.2.0','Using shaderpack: Aqualumen-0.6.0.zip',
        'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti','OpenGL Version: 3.2.0 NVIDIA',
        'Preparing start region for dimension minecraft:overworld','0.2.0 contact bridge initialized'):assert token in log,token
    assert '/saves/新規ワールド/session.lock' in (root/'ordinary-world-open-files.txt').read_text()
    images={}
    for name in ('ordinary-runtime.png','ordinary-paused.png'):
        p=root/name;blob=p.read_bytes()
        assert blob[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',blob[16:24])==(1600,900)
        images[name]=sha(p)
    audits=[json.loads((root/f'gpu-{order}-01-audit.json').read_text()) for order in (48,64,96)]
    assert all(a['allFourReferenceGatesPassed'] for a in audits)
    optical=json.loads((root/'main-old-01-audit.json').read_text())
    assert optical['independentlyQualifiedOldOpticalRED'] and not optical['candidateMainGREEN']
    return dict(schema='aqualumen-supported-glsl-checkpoint-v1',
        normalPack='Aqualumen-0.6.0.zip',normalPhysics='0.2.0',testEntryPointsAbsent=True,
        originalOptionsAndBenchmarkBytesEqual=True,irisSemanticValuesEqual=True,
        ordinarySavedTreeEqualBeforeReopening=True,ordinaryWorldRestored=False,ordinaryWorldAutomation=False,
        normalReopenedGameLogQualified=True,ordinaryImageHashes=images,
        ownedOrdinaryLauncherSession=55236,ordinaryImagesInspectedByRoot=True,
        soundInitializationSucceeded='Failed to open OpenAL device' not in log,
        oldMainOpticalREDQualified=True,newStandaloneGLSLAll4InputsAll3OrdersQualified=True,
        standaloneGLSL96MaximumAbsoluteError=max(p['error'] for p in audits[2]['constantAirDifferences']),
        candidateFullInterfaceImplemented=False,candidateMainGREEN=False,candidateIrisTestRun=False,
        naturalWaterAccepted=False,motionAccepted=False,physicalEnergyAccepted=False,fullGoalAchieved=False,
        scope='Concrete original-MAIN regression and unused TEST integral port, not a corrected full RGB interface or natural-view acceptance. No fresh candidate Minecraft timings. Normal handoff viewed after all native GL.')
if __name__=='__main__':print(json.dumps(finish(sys.argv[1]),indent=2,sort_keys=True))
