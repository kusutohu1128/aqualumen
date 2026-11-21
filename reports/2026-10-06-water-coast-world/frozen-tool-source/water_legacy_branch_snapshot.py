"""Read-only fresh Lab baseline audit after normal save/quit. No save restore."""
import hashlib
import json
from pathlib import Path
import sys

GAME=Path('/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft')
backup=Path(sys.argv[1])
assert backup.parent==Path('/home/kusutohu/.cache') and backup.name.startswith('aqualumen-legacy-branch-host-')
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
config={n:sha(GAME/n) for n in ('options.txt','config/iris.properties','config/aqualumen-benchmark.properties')}
assert all(sha(backup/n)==v for n,v in config.items())
mods={p.name:sha(p) for p in (GAME/'mods').glob('*.jar')}
assert set(mods)=={'aqualumen-physics-0.2.0.jar','iris-fabric-1.8.8+mc1.21.1.jar','sodium-fabric-0.6.9+mc1.21.1.jar'}
assert 'shaderPack=Aqualumen-0.6.0.zip' in (GAME/'config/iris.properties').read_text()
controls=['aqualumen-'+n for n in ('benchmark.enabled','sun-test.enabled','shore-observe.properties','water-stage-observe.properties',
    'sun-guard-observe.properties','bathymetry-observe.properties','solar-cache-observe.properties','atlas-final-observe.properties','atlas-joint-observe.properties')]
assert not any((GAME/'config'/n).exists() for n in controls)
save=GAME/'saves/新規ワールド'
paths=list(save.rglob('*'));assert not save.is_symlink() and not any(p.is_symlink() for p in paths)
tree={str(p.relative_to(save)):sha(p) for p in paths if p.is_file()}
assert len(tree)==41
print(json.dumps(dict(game=str(GAME),backup=str(backup),configSHA256=config,activeMods=mods,
    ordinarySavedFilesSHA256=tree,ordinarySaveRestored=False,ordinaryClientExit=0,
    instrumentationEntryPointsAbsent=controls),indent=2,sort_keys=True))
