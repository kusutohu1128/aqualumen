from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZipFile

root = Path('/home/kusutohu/repos/aqualumen')
report = root / 'reports/2026-10-23-land-shadows'
game = Path('/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft')
base = game / 'shaderpacks/Aqualumen-0.6.0.zip'
expected = '6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert sha(base) == expected, 'Ordinary pack differs; stop rather than infer a baseline'
report.mkdir(exist_ok=False)
frozen = report / 'ordinary-0.6.zip'
shutil.copyfile(base, frozen)
assert sha(frozen) == expected
with ZipFile(frozen) as archive:
    names = archive.namelist()
    assert len(names) == len(set(names))
    assert all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in names)
    archive.extractall(report / 'ordinary-source')
pins = {path.relative_to(root).as_posix(): sha(path) for path in sorted((root / 'shaders').rglob('*')) if path.is_file()}
state = dict(utc=datetime.now(timezone.utc).isoformat(), ordinaryArchive=str(base), ordinaryArchiveSHA256=expected,
             originalRootShaderPins=pins,
             observedIrisPropertiesSHA256=sha(game / 'config/iris.properties'),
             liveClientPolicy='Do not quit, reload, teleport, automate, alter active selection, or restore over user changes.',
             intendedOutput='Standalone land-shadow preview derived from exact ordinary0.6. No water algorithm or caster edits.',
             ordinaryWorldSnapshot=False)
with (report / 'BASELINE.json').open('x') as stream:
    json.dump(state, stream, indent=2)
print(json.dumps(dict(report=str(report), archiveSHA256=expected, rootShaderFiles=len(pins))))
