"""CPU-only final timing/restoration record; never a full visual-goal verifier."""
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import water_legacy_branch_restore_audit as restore

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def values(p):
    return dict(line.strip().split('=',1) for line in p.read_text().splitlines() if '=' in line and not line.startswith('#'))

def finish(root):
    root=Path(root);game=restore.GAME
    baseline=json.loads((root/'prelaunch.json').read_text())
    backup=Path(baseline['backup'])
    assert sha(game/'options.txt')==baseline['configSHA256']['options.txt']
    assert sha(game/'config/aqualumen-benchmark.properties')==baseline['configSHA256']['config/aqualumen-benchmark.properties']
    assert values(game/'config/iris.properties')==values(backup/'config/iris.properties')
    assert {p.name:sha(p) for p in (game/'mods').glob('*.jar')}==baseline['activeMods']
    assert not any((game/'config'/p).exists() for p in baseline['instrumentationEntryPointsAbsent'])
    assert not (game/'aqualumen-benchmark/request.properties').exists()
    log=(root/'ordinary-game.log').read_text()
    for token in ('aqualumen_physics 0.2.0','Using shaderpack: Aqualumen-0.6.0.zip',
                  'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti','OpenGL Version: 3.2.0 NVIDIA',
                  "ServerLevel[新規ワールド]",'0.2.0 contact bridge initialized'):
        assert token in log,token
    records=[]
    for role in ('phase0-full','phase0-base','phase45-full','phase45-base'):
        folder=root/(role+'-run')
        meta=json.loads((folder/'underwater-up-tilt.json').read_text())
        with (folder/'underwater-up-tilt.csv').open() as f:rows=list(csv.DictReader(f))
        ns=[int(r['ns']) for r in rows]
        assert ns and all(n>0 for n in ns) and len(ns)==meta['frames']
        fps=len(ns)*1e9/sum(ns)
        p99=sorted(ns)[math.ceil(.99*len(ns))-1]*1e-6
        assert math.isclose(fps,meta['mean_fps'],rel_tol=1e-12)
        assert math.isclose(p99,meta['p99_ms'],rel_tol=1e-12)
        assert meta['shader_active'] is True and meta['shader_fallback'] is False
        assert meta['resolution']==meta['framebuffer_resolution']==[1600,900]
        assert meta['world_id']=='b22dbccb-2970-41e6-847f-f183b1ec923d'
        assert meta['actual_camera_rotation']==[-45.0,-65.0]
        assert meta['underwater_up']['actual_world_time']==6000
        image=folder/'underwater-up-tilt.png'
        blob=image.read_bytes();assert blob[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',blob[16:24])==(1600,900)
        records.append(dict(role=role,intervals=len(ns),meanFPS=fps,p99Ms=p99,maxMs=max(ns)*1e-6,
            rawTimingSha256=sha(folder/'underwater-up-tilt.csv'),pngSha256=sha(image),
            timingScope='1600x900 diagnostic atlas warmed-view 5-second sample; not normal-pack FPS or performance acceptance'))
    return dict(schema='aqualumen-legacy-branch-final-record-v1',timings=records,
        normalPack='Aqualumen-0.6.0.zip',normalPhysics='0.2.0',activeModHashes=baseline['activeMods'],
        normalOptionsAndBenchmarkBytesEqual=True,irisSemanticValuesEqual=True,
        irisTimestampCommentMayRegenerate=True,irisCurrentSha256=sha(game/'config/iris.properties'),
        testEntryPointsAbsent=True,ordinaryReopenedUnderNormalModsLogQualified=True,
        ordinaryRuntimePngSha256=sha(root/'ordinary-runtime.png'),ordinaryPausedPngSha256=sha(root/'ordinary-paused.png'),
        ordinaryImagesInspectedByRoot=True,ownedOrdinaryLauncherSession=12444,
        ordinarySavedFileEqualityBeforeRelaunchEvidence='restoration-before-relaunch.json',
        ordinaryWorldRestored=False,ordinaryWorldAutomation=False,
        soundInitializationSucceeded='Failed to open OpenAL device' not in log,
        shippingSourcesChangedThisSlice=False,opticalFixImplemented=False,
        fullGoalAchieved=False,naturalWaterAccepted=False,motionAccepted=False,
        livePauseEvidenceScope='Root inspected Minecraft F2 runtime and pause-menu PNGs; shell process handle independently polled. No subsequent native GL work.')

if __name__=='__main__':
    print(json.dumps(finish(sys.argv[1]),indent=2,sort_keys=True,allow_nan=False))
