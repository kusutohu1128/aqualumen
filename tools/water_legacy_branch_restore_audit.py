"""Verify fresh byte restoration and ordinary save identity BEFORE reopening."""
import hashlib
import json
from pathlib import Path
import sys

GAME=Path('/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft')

def audit(root):
    root=Path(root)
    baseline=json.loads((root/'prelaunch.json').read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    config={n:sha(GAME/n) for n in baseline['configSHA256']}
    assert config==baseline['configSHA256'],'Fresh config bytes differ'
    mods={p.name:sha(p) for p in (GAME/'mods').glob('*.jar')}
    assert mods==baseline['activeMods'],'Ordinary active Mod set or hashes differ'
    controls=baseline['instrumentationEntryPointsAbsent']
    assert not any((GAME/'config'/n).exists() for n in controls)
    assert not (GAME/'aqualumen-benchmark/request.properties').exists()
    assert not (GAME/'aqualumen-benchmark/opaque-test-journal.json').exists()
    save=GAME/'saves/新規ワールド'
    paths=list(save.rglob('*'))
    assert not save.is_symlink() and not any(p.is_symlink() for p in paths)
    tree={str(p.relative_to(save)):sha(p) for p in paths if p.is_file()}
    assert tree==baseline['ordinarySavedFilesSHA256'],'Ordinary saved tree changed during TEST'
    assert 'shaderPack=Aqualumen-0.6.0.zip' in (GAME/'config/iris.properties').read_text()
    assert sha(GAME/'shaderpacks/Aqualumen-0.6.0.zip')=='6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73'
    return dict(schema='aqualumen-legacy-branch-restoration-v1',configSHA256=config,
        activeMods=mods,entryPointsAbsent=controls,requestAbsent=True,
        ordinarySavedFileCount=len(tree),ordinarySavedFilesEqualFreshPostSaveBaseline=True,
        ordinaryWorldRestored=False,ordinaryWorldAutomation=False,ordinaryFreshHandoffProven=False,
        scope='On-disk verification before normal relaunch, not a new live-client or save/entity-integrity assertion.')

if __name__=='__main__':
    print(json.dumps(audit(sys.argv[1]),indent=2,sort_keys=True))
