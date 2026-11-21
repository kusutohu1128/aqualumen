"""Record final CPU exits and immutable runtime/native source bindings."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('/home/kusutohu/repos/aqualumen')
OUT = ROOT / 'reports/2026-10-22-joint-paired-water'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
result = subprocess.run(['python3', '-m', 'unittest', 'discover', '-s', 'tools', '-p', 'test_water_paired*.py', '-v'],
                        cwd=ROOT, capture_output=True, text=True)
with (OUT / 'cpu-tests.log').open('x') as stream:
    stream.write(result.stdout + result.stderr)
native = json.loads((OUT / 'native-final/receipt.json').read_text())
if sha(ROOT / 'tools/water_paired_native.cpp') != native['native_source_sha256']:
    raise ValueError('Integrated native source differs from actual tested source')
import sys
sys.path.insert(0, str(ROOT / 'tools'))
import water_paired_runtime as runtime
runtime.prior.stopped()
runtime.owned_paths()
before = json.loads((OUT / 'runtime/baseline.json').read_text())
if runtime.prior.ordinary_tree() != before['ordinarySave']:
    raise ValueError('Ordinary save changed')
if {name: sha(runtime.GAME / name) for name in runtime.CONFIG} != before['config']:
    raise ValueError('Normal config changed')
if {p.name: sha(p) for p in (runtime.GAME / 'mods').glob('*.jar')} != before['mods']:
    raise ValueError('Normal Mod set changed')
if sha(runtime.GAME.parent / 'instance.cfg') != before['instanceSHA256']:
    raise ValueError('Normal instance changed')
log = runtime.GAME / 'logs/latest.log'
text = log.read_text()
if 'Stopping!' not in text:
    raise ValueError('Client clean stop missing')
with (OUT / 'receiver-runtime.log').open('x') as stream:
    stream.write('\n'.join(line for line in text.splitlines() if '[Aqualumen Receiver]' in line) + '\n')
sources = sorted((ROOT / 'tools/paired-water-probe').rglob('*.java')) + [ROOT / 'tools/build-paired-water-probe.sh']
sources += sorted((ROOT / 'tools').glob('*water_paired*'))
receipt = dict(schema='aqualumen-paired-water-closure-v1', cpuExitCode=result.returncode,
               nativeSourceMatchesTested=True, javaAbsent=True, normalConfigExact=True, normalModsExact=True,
               instanceExact=True, ordinarySaveExact=True, ordinarySaveRestored=False, cleanStopObserved=True,
               actualMinecraftRerunAfterStagingOnlyRecoveryPatch=False,
               logSHA256=sha(log), sources={str(p.relative_to(ROOT)): sha(p) for p in sources if p.is_file()},
               observerCpuAssertions=53, observerBuildExitCode=0,
               actualRuntimeObserverSHA256=before['testMods'][runtime.PROBE.name],
               remaining=['SSR1 controlled fixture', 'Actual Iris nonwater blend-clear fixture',
                          'Optical/geometry causal experiment', 'Natural moving-wave physical/visual acceptance'])
with (OUT / 'CLOSURE.json').open('x') as stream:
    json.dump(receipt, stream, indent=2)
print(json.dumps(dict(cpuExitCode=result.returncode, normalRuntimeExact=True, javaAbsent=True)))
raise SystemExit(result.returncode)
