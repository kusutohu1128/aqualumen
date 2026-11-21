"""Post-native ordinary handoff receipt. Does not restore any ordinary save."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/2026-10-06-water-supported-sources'
GAME=Path('/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def properties(text):
    return sorted(a.strip() for a in text.splitlines() if a.strip() and not a.lstrip().startswith('#'))


def finish(backup,pid,session,runtime,paused):
    backup=Path(backup)
    assert backup.parent==Path('/home/kusutohu/.cache') and backup.name.startswith('aqualumen-legacy-branch-host-supported-sources-')
    before=json.loads((OUT/'fresh-normal-baseline.json').read_text())
    prelaunch=json.loads((OUT/'normal-prelaunch.json').read_text())
    assert before['ordinarySavedFilesSHA256']==prelaunch['ordinarySavedFilesSHA256']
    assert before['configSHA256']==prelaunch['configSHA256']
    assert before['activeMods']==prelaunch['activeMods']
    for name in ('options.txt','config/aqualumen-benchmark.properties'):
        assert sha(GAME/name)==sha(backup/name)
    assert properties((GAME/'config/iris.properties').read_text())==properties((backup/'config/iris.properties').read_text())
    assert {p.name:sha(p) for p in (GAME/'mods').glob('*.jar')}==before['activeMods']
    for name in before['instrumentationEntryPointsAbsent']:
        assert not (GAME/'config'/name).exists()
    assert sha(GAME/'shaderpacks/Aqualumen-0.6.0.zip')=='6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73'
    status=Path(f'/proc/{pid}/status').read_text();assert re.search(r'^Name:\s+java$',status,re.M)
    locks=[]
    for p in Path(f'/proc/{pid}/fd').iterdir():
        try:target=p.readlink()
        except FileNotFoundError:continue
        if target==GAME/'saves/新規ワールド/session.lock':locks.append(str(p))
    assert locks
    log=(GAME/'logs/latest.log').read_text()
    assert 'Using shaderpack: Aqualumen-0.6.0.zip' in log and 'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti' in log
    assert 'Shader compilation failed' not in log
    images={}
    for role,name in (('ordinary-runtime.png',runtime),('ordinary-paused.png',paused)):
        assert re.fullmatch(r'2026-10-06_[0-9]{2}\.[0-9]{2}\.[0-9]{2}\.png',name)
        source=GAME/'screenshots'/name;assert (OUT/role).read_bytes()==source.read_bytes()
        images[role]=sha(OUT/role)
    source=json.loads((OUT/'main-02-audit-v2.json').read_text())
    assert source['exactRawComparisons']==920 and source['actualOpaqueTracePositiveQualified']
    timing=json.loads((OUT/'timing-01-audit.json').read_text())
    assert timing['currentMAINWitnessExact'] and timing['exactWitnessComparisons']==34
    native=(OUT/'retained-native-check.log').read_text()
    assert 'NVIDIA GeForce RTX 3080 Ti' in native and '11 program pairs compiled and linked.' in native
    seals={}
    for name in ('rgb','glsl','transmission','legacy'):
        lines=(OUT/f'old-{name}-seal-after.log').read_text().splitlines()
        assert lines and all(a.endswith(': OK') for a in lines)
        seals[name]=len(lines)
    result=dict(schema='aqualumen-supported-sources-handoff-v1',goalTurnClassification='progress',
        actualSourceAdapterImplemented=True,actualOpaqueAndSunSourceControlsQualified=True,
        physicalOffscreenReflectionValidated=False,sourceExactRawComparisons=920,
        normalOwnedLauncherSession=session,normalJavaPID=pid,normalWindow=62914567,display=':1',
        normalPack='Aqualumen-0.6.0.zip',normalPhysics='0.2.0',ordinaryWorldLockFDs=locks,
        ordinaryImageHashes=images,ordinaryImagesInspectedByRoot=True,
        originalOptionsBenchmarkBytesEqual=True,irisSemanticValuesEqual=True,
        ordinarySavedTreeEqualBeforeReopening=True,ordinaryWorldRestored=False,ordinaryWorldAutomation=False,
        ordinaryPriorLauncherExit=0,testEntryPointsAbsent=True,newTESTPackInstalled=False,
        newMinecraftCandidateIntervalsCaptured=False,oldSealsQualified=seals,
        nativeDrawTiming=timing['nativeDraws'],nativeTimingIsMinecraftFPS=False,
        samplingPrototypeGLExecuted=False,samplingPrototypeAdopted=False,
        physicalEnergyAccepted=False,naturalWaterAccepted=False,motionAccepted=False,shippingAccepted=False,
        fullGoalAchieved=False,soundInitializationSucceeded='Sound engine started' in log)
    with (OUT/'checkpoint.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('backup');p.add_argument('pid',type=int);p.add_argument('session',type=int)
    p.add_argument('runtime');p.add_argument('paused');args=p.parse_args()
    print(json.dumps(finish(args.backup,args.pid,args.session,args.runtime,args.paused),indent=2,sort_keys=True))
