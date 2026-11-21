"""Read-only ordinary handoff audit; image review and live handle are external."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
base = json.loads((HERE / 'prelaunch.json').read_text())
game, backup = Path(base['game']), Path(base['backup'])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
properties = lambda p: sorted(x.strip() for x in p.read_text().splitlines()
                              if x.strip() and not x.lstrip().startswith('#'))
assert properties(game / 'config/iris.properties') == properties(backup / 'config/iris.properties')
assert sha(game / 'options.txt') == base['configSHA256']['options.txt']
assert sha(game / 'config/aqualumen-benchmark.properties') == base['configSHA256']['config/aqualumen-benchmark.properties']
assert {p.name: sha(p) for p in (game / 'mods').glob('*.jar')} == base['activeMods']
controls = json.loads((HERE / 'restoration-before-relaunch.json').read_text())['instrumentationEntryPointsAbsent']
assert all(not (game / 'config' / n).exists() for n in controls)
log = (HERE / 'ordinary-return-game.log').read_text()
for marker in ('- aqualumen_physics 0.2.0', 'Using shaderpack: Aqualumen-0.6.0.zip',
               '0.2.0 contact bridge initialized', 'OpenGL Renderer: NVIDIA GeForce RTX 3080 Ti',
               'OpenGL Version: 3.2.0 NVIDIA 580.173.02', 'Saving and pausing game...',
               "ServerLevel[新規ワールド]"):
    assert marker in log, marker
for marker in ('- aqualumen_benchmark ', '- aqualumen_atlas_joint ',
               '- aqualumen_water_sun_test ', 'Benchmark preparing:', 'Shader compilation failed'):
    assert marker not in log, marker
assert (HERE / 'ordinary-paused.png').is_file() and (HERE / 'ordinary-runtime.png').is_file()
print(json.dumps(dict(schema='aqualumen-joint-ordinary-handoff-v1',
    ordinaryPack='Aqualumen-0.6.0.zip', actualPhysicsVersion='0.2.0',
    renderer='NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2', minecraftGL='3.2.0 NVIDIA 580.173.02',
    ownedLiveSession=23157, observedWindow=62914567,
    actualOrdinaryWorld='新規ワールド', freshlyViewedRuntimeAndPause=True,
    optionsAndBenchmarkBytesRestored=True, irisPropertiesEqualIgnoringTimestampComment=True,
    irisShaAfterRelaunch=sha(game / 'config/iris.properties'),
    instrumentationEntryPointsAbsent=controls,
    ordinarySavedTreeMatchedBeforeRelaunch=True, ordinarySaveRestored=False,
    ordinaryCameraTimeTerrainAutomated=False, nativeGLAfterHandoff=False,
    retainedAudioLimitation='OpenAL device could not open; also present in prior ordinary client. '
                            'Sound/music disabled by Minecraft. Audio stack not changed.',
    visualGoalAchieved=False, opticalFixClaimed=False), indent=2, sort_keys=True))
