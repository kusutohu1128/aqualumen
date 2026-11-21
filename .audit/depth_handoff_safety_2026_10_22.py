from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

root = Path('/home/kusutohu/repos/aqualumen')
sys.path.insert(0, str(root / 'tools'))
import water_paired_runtime as runtime
from water_hit_depth_runtime import lab_java_processes

report = root / 'reports/2026-10-22-water-hit-depth'
closure_path = report / 'CLOSURE.json'
closure = json.loads(closure_path.read_text())
baseline = json.loads((report / 'runtime-candidate3/baseline.json').read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert not lab_java_processes(runtime.GAME)
assert runtime.prior.ordinary_tree() == baseline['ordinarySave']
assert {path.name: sha(path) for path in (runtime.GAME / 'mods').glob('*.jar')} == baseline['mods']
assert {name: sha(runtime.GAME / name) for name in runtime.CONFIG} == baseline['config']
assert sha(runtime.GAME.parent / 'instance.cfg') == baseline['instanceSHA256']
assert 'shaderPack=Aqualumen-0.6.0.zip' in (runtime.GAME / 'config/iris.properties').read_text().splitlines()
assert not (runtime.GAME / 'aqualumen-benchmark/request.properties').exists()
assert not any(path.name.startswith('aqualumen-') and (path.name.endswith('.enabled') or
    'observe' in path.name and path.suffix == '.properties') for path in (runtime.GAME / 'config').iterdir())
assert all(sha(root / name) == pin for name, pin in closure['originalSourcePins'].items())
assert all(sha(root / name) == pin for name, pin in closure['previousFrozenArchivePins'].items())
assert all(sha(root / 'tools' / name) == pin for name, pin in closure['currentToolSHA256'].items())
assert all(sha(report / (name + '.json')) == pin for name, pin in closure['auditSHA256'].items())
receipt = dict(utc=datetime.now(timezone.utc).isoformat(), scope='Read-only final handoff safety refresh; no new game/GPU run',
               closureSHA256=sha(closure_path), labJavaAbsent=True, ordinarySaveExact=True, ordinarySaveRestored=False,
               configsExact=True, modsExact=True, instanceExact=True, ordinaryPack='Aqualumen-0.6.0.zip', ordinaryPhysics='0.2.0',
               testControlsAbsent=True, originalSourcePinsExact=True, frozenArchivePinsExact=True, currentToolPinsExact=True,
               savedAuditPinsExact=True, passed=True)
with (report / 'HANDOFF-SAFETY.json').open('x') as stream:
    json.dump(receipt, stream, indent=2)
print(json.dumps(receipt))
