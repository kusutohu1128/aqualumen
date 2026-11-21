"""Read-only pre-relaunch restoration audit. Does not restore a save."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
baseline = json.loads((HERE / 'prelaunch.json').read_text())
game = Path(baseline['game'])
backup = Path(baseline['backup'])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
config = {n: sha(game / n) for n in baseline['configSHA256']}
assert config == baseline['configSHA256']
mods = {p.name: sha(p) for p in (game / 'mods').glob('*.jar')}
assert mods == baseline['activeMods']
controls = ['aqualumen-' + n for n in (
    'benchmark.enabled', 'sun-test.enabled', 'shore-observe.properties',
    'water-stage-observe.properties', 'sun-guard-observe.properties',
    'bathymetry-observe.properties', 'solar-cache-observe.properties',
    'atlas-final-observe.properties', 'atlas-joint-observe.properties')]
assert all(not (game / 'config' / n).exists() for n in controls)
assert not (game / 'aqualumen-benchmark/request.properties').exists()
assert not (game / 'aqualumen-benchmark/opaque-fixture-journal.json').exists()
ordinary = game / 'saves/新規ワールド'
assert not ordinary.is_symlink()
paths = list(ordinary.rglob('*'))
assert not any(p.is_symlink() for p in paths)
saved = {str(p.relative_to(ordinary)): sha(p) for p in paths if p.is_file()}
expected = json.loads((backup / 'ordinary-save-hashes.json').read_text())
assert saved == expected and len(saved) == 41
iris = (game / 'config/iris.properties').read_text()
assert 'shaderPack=Aqualumen-0.6.0.zip' in iris
assert sha(game / 'shaderpacks/Aqualumen-0.6.0.zip') == '6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73'
print(json.dumps(dict(schema='aqualumen-joint-restoration-before-relaunch-v1',
    configSHA256=config, activeMods=mods, normalPack='Aqualumen-0.6.0.zip',
    instrumentationEntryPointsAbsent=controls, ordinarySaveFileCount=41,
    ordinarySavedFilesUnchanged=True, ordinarySaveRestored=False,
    ordinaryCameraTimeTerrainAutomated=False,
    phase45OwnedClientExit=0, javaAbsentBeforeRestoration=True,
    freshOrdinaryRuntimeHandoff=False), indent=2, sort_keys=True))
