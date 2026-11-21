from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

root = Path('/home/kusutohu/repos/aqualumen')
sys.path.insert(0, str(root / 'tools'))
from land_shadow_run import save, sha
from water_hit_depth_runtime import lab_java_processes
import water_paired_runtime as runtime

report = root / 'reports/2026-10-23-land-shadows'
initial = json.loads((report / 'BASELINE.json').read_text())
assert all(sha(root / name) == value for name, value in initial['originalRootShaderPins'].items())
candidate = json.loads((report / 'candidate2-checks/receipt.json').read_text())
assert all(sha(root / name) == value for name, value in candidate['sourcePins'].items())
runtime_sources = json.loads((report / 'runtime-tool-checks2/receipt.json').read_text())
assert all(sha(root / name) == value for name, value in runtime_sources['sourcePins'].items())
archive = report / 'Aqualumen-LandShadows-Preview-2026-10-23.zip'
assert sha(archive) == 'ea3cbd1e19453aabc1807df7016549001379714a47e57187b3b72a31be0e6652'
manifest = json.loads(archive.with_name(archive.name + '.manifest.json').read_text())
with ZipFile(archive) as bundle:
    assert {name: hashlib.sha256(bundle.read(name)).hexdigest() for name in bundle.namelist()} == manifest['output_entry_sha256']
native = json.loads((report / 'native-candidate2/capture/RESULT.json').read_text())
assert len(native['scenarios']) == 26 and all(item['wrongReceiverPixels'] == 0 for item in native['scenarios'])
motion = json.loads((report / 'motion2-checks/land/RESULT.json').read_text())
assert all(motion[key] for key in ('endpointContrastPassed', 'monotonicPassed', 'maximumStepPassed'))
for role in ('ordinary', 'candidate'):
    observation = json.loads((report / 'runtime1' / (role + '-collected.json')).read_text())
    source = report / 'runtime1' / (role + '-run')
    assert all(sha(source / name) == value for name, value in observation['files'].items())
    assert observation['actualMinecraft'] and observation['shaderActive'] and not observation['shaderFallback']
    assert json.loads((report / 'runtime1' / (role + '-launcher-exit.json')).read_text())['exitCode'] == 0
baseline = json.loads((report / 'runtime1/baseline.json').read_text())
game = runtime.GAME
assert not lab_java_processes(game)
assert all(sha(game / name) == value for name, value in baseline['config'].items())
assert {path.relative_to(game / 'mods').as_posix(): sha(path) for path in (game / 'mods').rglob('*') if path.is_file()} == baseline['mods']
assert runtime.prior.ordinary_tree() == baseline['ordinarySave']
assert sha(game.parent / 'instance.cfg') == baseline['instanceSHA256']
assert not (game / 'config/aqualumen-benchmark.enabled').exists()
assert not (game / 'aqualumen-benchmark/request.properties').exists()
assert not (game / 'aqualumen-benchmark/opaque-fixture-journal.json').exists()
assert sha(game / 'shaderpacks' / archive.name) == sha(archive)
whitespace = []
for name in candidate['sourcePins']:
    result = subprocess.run(['rtk', 'proxy', 'git', 'diff', '--no-index', '--check', '/dev/null', str(root / name)], capture_output=True, text=True)
    assert result.returncode in (0, 1) and not result.stdout and not result.stderr, name
    whitespace.append(dict(path=name, exitCode=result.returncode, diagnostics=''))
refs = ('qualification.json', 'candidate2-checks/receipt.json', 'native-candidate2/receipt.json',
        'motion2-checks/receipt.json', 'negative-controls1/receipt.json', 'runtime-tool-checks2/receipt.json',
        'capture-protocol.json', 'runtime1/ordinary-collected.json', 'runtime1/candidate-collected.json',
        'runtime1/restored.json', 'CODEX-FINAL-REVIEW.md', 'VISUAL-RESTORE-REVIEW.md',
        'claude-design/receipt.json', 'claude-crossjudge/receipt.json', 'claude-review/receipt.json')
save(report / 'closure.json', dict(utc=datetime.now(timezone.utc).isoformat(),
     packSHA256=sha(archive), originalRootShaderFilesPreserved=len(initial['originalRootShaderPins']),
     originalArchivePayloadsPreserved=manifest['preserved_original_entries'],
     nonopaqueExpansionsPreserved=len(manifest['preserved_nonopaque_expansions']),
     cpuPackTests=28, cpuRuntimeTests=30, nativeFixedCases=26, nativeWrongSelectedPixels=0,
     fixedLightReceiverPositions=513, maximumVisibilityStep=motion['maximumAbsoluteVisibilityStep'],
     actualMinecraftScenesPerRole=3, actualMinecraftRoleCount=2, visualCompatibilityOnly=True,
     normalConfigurationExact=True, normalModsExact=True, normalInstanceExact=True,
     ordinarySaveFiles=len(baseline['ordinarySave']), ordinarySaveUnchanged=True, ordinarySaveRolledBack=False,
     benchmarkDisabled=True, labStopped=True, inactivePreviewInstalled=True,
     whitespaceChecks=whitespace, evidence={name: sha(report / name) for name in refs},
     finalClaudeReviewCompleted=False, crossFamilyFinalTrailReviewCompleted=False,
     generalNaturalVisualAccepted=False, performanceAccepted=False, releaseApproved=False,
     commitOrPRCreated=False))
print('Closure verified. Inactive preview installed; exact normal state; bounded GPU/Iris evidence, not general release approval.')
