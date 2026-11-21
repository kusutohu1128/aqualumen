"""Reversible, opt-in paired-water experiment in the existing Lab/V2 only.

Commands are separate so every launch/capture can be inspected before continuing.
Never rolls saves back and never kills Minecraft. Existing Evidence is immutable.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

import display_water_runtime as prior

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-22-joint-paired-water/runtime'
GAME = prior.GAME
PACK = 'Aqualumen-PairedWater-2026-10-22.zip'
PROBE = ROOT / 'build/aqualumen-paired-water-probe-0.1.0.jar'
BENCH = ROOT / 'build/aqualumen-benchmark-0.3.9-projection-guards.jar'
PHYSICS = ROOT / 'build/aqualumen-physics-0.3.0-plant-owner-probe-v100.jar'
PINNED = {BENCH.name: 'ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29',
          PHYSICS.name: 'd3b07b3f5e28f0c7bc5346f44391166051143662e087313d24e49008854cd16c'}
REQUEST = 'config/aqualumen-paired-water-observe.properties'
CONFIG = prior.NAMES
RUN_SUFFIX = '20261022'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    with (OUT / name).open('x') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, sort_keys=True)


def props(path, values, exclusive=False):
    with path.open('x' if exclusive else 'w') as stream:
        stream.write(''.join(str(k) + '=' + str(v) + '\n' for k, v in values.items()))


def baseline():
    return json.loads((OUT / 'baseline.json').read_text())


def owned_paths():
    require(GAME.resolve() == GAME and GAME.parent.name == 'Aqualumen Lab', 'Lab path redirected')
    for relative in ('mods', 'shaderpacks', 'config', 'saves', 'saves/' + prior.WORLD, 'aqualumen-benchmark'):
        path = GAME / relative
        require(path.is_dir() and not path.is_symlink() and path.resolve() == path, 'Runtime directory redirected: ' + relative)
    for name in (*CONFIG, '../instance.cfg', 'saves/' + prior.WORLD + '/aqualumen-world.properties'):
        path = GAME / name
        require(path.is_file() and not path.is_symlink(), 'Runtime input redirected: ' + name)
    for folder in ('mods', 'shaderpacks', 'config'):
        require(not any(p.is_symlink() for p in (GAME / folder).iterdir()), 'Symlinked runtime child: ' + folder)


def world_marker():
    marker = dict(line.split('=', 1) for line in (GAME / 'saves' / prior.WORLD / 'aqualumen-world.properties').read_text().splitlines())
    require(marker == dict(schema='2', world_id=prior.WORLD_ID, seed='308060', generator='minecraft:noise/overworld', minecraft='1.21.1'), 'V2 marker differs')


def expected_config(pack_hash):
    return dict(schema='2', world=prior.WORLD, world_id=prior.WORLD_ID, expected_pack=PACK,
                expected_pack_sha256=pack_hash, width='1600', height='900', render_chunks='12',
                simulation_chunks='6', capture_motion='false')


def staging_path(target):
    return target.with_name('.' + target.name + '.paired-20261022.pending')


def install_new(source, target, expected_hash):
    temporary = staging_path(target)
    require(not target.exists() and not target.is_symlink() and not temporary.exists() and not temporary.is_symlink(), 'Install target exists')
    with temporary.open('xb') as stream:
        stream.write(source.read_bytes())
        stream.flush()
        os.fsync(stream.fileno())
    require(sha(temporary) == expected_hash, 'Incomplete staged install; retain for recovery')
    os.link(temporary, target)
    temporary.unlink()


def setup(pack, native):
    prior.stopped()
    prior.verify_previous_exit()
    owned_paths()
    require(not OUT.exists(), 'Existing runtime Evidence; do not overwrite')
    require(pack.is_file() and PROBE.is_file(), 'New paired pack/probe missing')
    proof = json.loads(native.read_text())
    require(proof.get('schema') == 'aqualumen-paired-water-qualification-v1'
            and proof.get('packSHA256') == sha(pack) and 'NVIDIA' in proof.get('renderer', '')
            and proof.get('compileExitCode') == 0 and proof.get('nativeExitCode') == 0
            and proof.get('C0Exact') is True and proof.get('classificationPassed') is True,
            'Matching NVIDIA compile/passivity/classification proof missing')
    for entry in proof.get('evidence', []):
        source = ROOT / entry['path']
        require(source.is_file() and not source.is_symlink() and sha(source) == entry['sha256'], 'Qualification evidence changed')
    require(len(proof.get('evidence', [])) >= 3, 'Qualification evidence references missing')
    require({p.name: sha(p) for p in (BENCH, PHYSICS)} == PINNED, 'Pinned test Mod changed')
    active = {p.name: sha(p) for p in (GAME / 'mods').glob('*.jar')}
    require(set(active) == {'aqualumen-physics-0.2.0.jar', 'iris-fabric-1.8.8+mc1.21.1.jar',
                           'sodium-fabric-0.6.9+mc1.21.1.jar'}, 'Not ordinary three-Mod baseline')
    require('shaderPack=Aqualumen-0.6.0.zip' in (GAME / 'config/iris.properties').read_text(), 'Not ordinary pack')
    world_marker()
    controls = [p for p in (GAME / 'config').iterdir() if p.name.startswith('aqualumen-')
                and (p.name.endswith('.enabled') or 'observe' in p.name and p.suffix == '.properties')]
    require(not controls and not (GAME / 'aqualumen-benchmark/request.properties').exists(), 'Prior TEST control still active')
    require(not (GAME / 'shaderpacks' / PACK).exists(), 'Pack already installed')
    require(all(not (GAME / 'mods' / p.name).exists() for p in (BENCH, PHYSICS, PROBE)), 'Test target already exists')
    planned_targets = [GAME / 'mods' / p.name for p in (BENCH, PHYSICS, PROBE)] + [GAME / 'shaderpacks' / PACK]
    require(all(not staging_path(p).exists() and not staging_path(p).is_symlink() for p in planned_targets), 'Prior staged artifact exists')
    iris = (GAME / 'config/iris.properties').read_text()
    require(iris.count('shaderPack=Aqualumen-0.6.0.zip') == 1, 'Iris pack anchor differs')
    iris = iris.replace('shaderPack=Aqualumen-0.6.0.zip', 'shaderPack=' + PACK)
    lines = (GAME / 'options.txt').read_text().splitlines()
    changes = dict(renderDistance='12', simulationDistance='6', maxFps='120', enableVsync='false',
                   fullscreen='false', pauseOnLostFocus='false', overrideWidth='1600', overrideHeight='900')
    for key in changes:
        require(sum(line.startswith(key + ':') for line in lines) == 1, 'Option anchor missing/duplicate: ' + key)
    lines = [line.split(':', 1)[0] + ':' + changes[line.split(':', 1)[0]]
             if line.split(':', 1)[0] in changes else line for line in lines]
    original_save = prior.ordinary_tree()
    backup = Path(tempfile.mkdtemp(prefix='aqualumen-paired-water-', dir=Path.home() / '.cache'))
    backup.chmod(0o700)
    OUT.mkdir()
    for name in (*CONFIG, '../instance.cfg'):
        target = backup / ('instance.cfg' if name.startswith('../') else name)
        target.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy2(GAME / name, target)
        require(sha(target) == sha(GAME / name), 'Backup copy differs; normal runtime untouched')
    inputs = {p.name: sha(p) for p in (BENCH, PHYSICS, PROBE)}
    save('baseline.json', dict(backup=str(backup), config={name: sha(GAME / name) for name in CONFIG},
         runtimeToolSHA256=sha(Path(__file__)),
         mods=active, ordinarySave=original_save, instanceSHA256=sha(GAME.parent / 'instance.cfg'),
         testMods=inputs, packSHA256=sha(pack), nativeProofSHA256=sha(native),
         nativeUntestedRoutes=proof.get('untestedRoutes'), nativeTestedRoutes=proof.get('testedRoutes'),
         qualification='wave evaluator frozen at 17s; ripples disabled; clouds/live lighting not frozen; no performance acceptance'))
    shutil.move(GAME / 'mods/aqualumen-physics-0.2.0.jar', backup / 'aqualumen-physics-0.2.0.jar')
    for source in (BENCH, PHYSICS, PROBE):
        install_new(source, GAME / 'mods' / source.name, inputs[source.name])
    install_new(pack, GAME / 'shaderpacks' / PACK, sha(pack))
    (GAME / 'config/iris.properties').write_text(iris)
    (GAME / 'options.txt').write_text('\n'.join(lines) + '\n')
    props(GAME / 'config/aqualumen-benchmark.properties', expected_config(sha(pack)))
    with (GAME / 'config/aqualumen-benchmark.enabled').open('x') as stream:
        stream.write('UUID guarded paired water TEST only\n')
    save('prepared.json', dict(testMods=inputs, pack=PACK, packSHA256=sha(pack), saveUnchanged=prior.ordinary_tree() == original_save))


def prepared():
    owned_paths()
    world_marker()
    data = baseline()
    receipt = json.loads((OUT / 'prepared.json').read_text())
    require(receipt['packSHA256'] == data['packSHA256'] and receipt['testMods'] == data['testMods'], 'Prepared receipt differs')
    require(sha(GAME / 'shaderpacks' / PACK) == data['packSHA256'], 'Pack identity changed')
    expected_mods = {name: value for name, value in data['mods'].items() if name != 'aqualumen-physics-0.2.0.jar'} | data['testMods']
    require({p.name: sha(p) for p in (GAME / 'mods').glob('*.jar')} == expected_mods, 'Installed Mod set changed')
    require(prior_control_properties(GAME / 'config/aqualumen-benchmark.properties') == expected_config(data['packSHA256']), 'TEST configuration differs')
    require((GAME / 'config/aqualumen-benchmark.enabled').read_text() == 'UUID guarded paired water TEST only\n', 'TEST opt-in differs')
    require('shaderPack=' + PACK in (GAME / 'config/iris.properties').read_text().splitlines(), 'Wrong selected pack')
    require(prior.ordinary_tree() == data['ordinarySave'], 'Ordinary save changed')


def prior_control_properties(path):
    return dict(line.split('=', 1) for line in path.read_text().splitlines() if line and not line.startswith('#'))


def live_owned():
    pids = subprocess.check_output(['pgrep', '-x', 'java'], text=True).split()
    require(len(pids) == 1 and Path(os.readlink('/proc/' + pids[0] + '/cwd')) == GAME, 'Owned Lab Java identity differs')
    prepared()


def launch():
    prior.stopped()
    prepared()
    data = baseline()
    require('shaderPack=' + PACK in (GAME / 'config/iris.properties').read_text(), 'Pack not selected')
    previous = (GAME / 'logs/latest.log').read_bytes()
    save('launcher-start.json', dict(world_id=prior.WORLD_ID, pack=PACK,
         previousLog=dict(bytes=len(previous), sha256=hashlib.sha256(previous).hexdigest())))
    with (Path(data['backup']) / 'launcher-private.log').open('xb') as output:
        os.chmod(output.name, 0o600)
        result = subprocess.run(['flatpak', 'run', '--command=prismrun', 'org.prismlauncher.PrismLauncher',
             '--launch', 'Aqualumen Lab', '--world', prior.WORLD], env=dict(os.environ, DISPLAY=':1'),
             stdout=output, stderr=subprocess.STDOUT)
    save('launcher-exit.json', dict(exitCode=result.returncode))


def scene(name):
    live_owned()
    prior.require_current_pipeline((GAME / 'logs/latest.log').read_bytes(), json.loads((OUT / 'launcher-start.json').read_text())['previousLog'])
    run_id = 'paired-water-' + name + '-' + RUN_SUFFIX
    subprocess.run(['python3', 'tools/benchmark-control.py', 'start', '--run-id', run_id,
                    '--scenes', name, '--warmup', '5', '--sample', '5'], cwd=ROOT, check=True)


def observe(scene_name):
    live_owned()
    run_id = 'paired-water-' + scene_name + '-' + RUN_SUFFIX
    status = json.loads((GAME / 'aqualumen-benchmark/status.json').read_text())
    require(status['state'] == 'complete' and status['run_id'] == run_id, 'Exact scene not complete')
    request_id = str(uuid.uuid4())
    path = GAME / REQUEST
    require(not path.exists(), 'Prior observer request still present')
    props(path, dict(request_id=request_id, world_id=prior.WORLD_ID, width='1600', height='900', scene=scene_name,
                    recorder_run_id=run_id), exclusive=True)
    save(scene_name + '-capture-request.json', dict(request_id=request_id, scene=scene_name, recorder_run_id=run_id))
    print(request_id)


def quit_client():
    live_owned()
    subprocess.run(['python3', 'tools/benchmark-control.py', 'quit'], cwd=ROOT, check=True)


def collect(scene_name):
    live_owned()
    request = json.loads((OUT / (scene_name + '-capture-request.json')).read_text())
    request_id = str(uuid.UUID(request['request_id']))
    source = GAME / 'aqualumen-benchmark/paired-water-observations' / request_id
    require(source.is_dir() and not source.is_symlink(), 'Capture not ready')
    manifest = json.loads((source / 'manifest.json').read_text())
    require(manifest.get('requestId') == request_id and manifest.get('recorderRunId') == request['recorder_run_id']
            and manifest.get('packSha256') == baseline()['packSHA256'], 'Capture identity differs')
    require(manifest.get('available') is True and manifest.get('beforeReadStateRestored') is True
            and manifest.get('afterReadStateRestored') is True and manifest.get('quadInvocationReturnedObserved') is True,
            'Capture failed, not paired acceptance: ' + str(manifest.get('reason')))
    require(manifest.get('width') == 1600 and manifest.get('height') == 900
            and 'NVIDIA' in manifest.get('glRenderer', '') and sum(manifest['routeCounts'][1:]) > 0, 'Capture extent/renderer/water differs')
    for entry in manifest['files'].values():
        name = entry['name']
        require(Path(name).name == name, 'Unsafe artifact name')
        path = source / name
        require(path.is_file() and not path.is_symlink() and path.stat().st_size == entry['bytes']
                and sha(path) == entry['sha256'], 'Partial capture artifact')
    target = OUT / (scene_name + '-paired-capture')
    require(not target.exists(), 'Existing capture Evidence')
    shutil.copytree(source, target)
    run = GAME / 'aqualumen-benchmark/runs' / request['recorder_run_id']
    run_manifest = json.loads((run / 'run.json').read_text())
    require(run_manifest['world_id'] == prior.WORLD_ID and run_manifest['pack_sha256'] == baseline()['packSHA256']
            and run_manifest['shader_active'] and not run_manifest['shader_fallback'], 'Scene pack activation differs')
    shutil.copytree(run, OUT / (scene_name + '-scene'))
    control = GAME / REQUEST
    require(prior_control_properties(control)['request_id'] == request_id, 'Observer request changed')
    shutil.move(control, OUT / (scene_name + '-consumed-observer.properties'))
    print('Archived one same-FINAL paired capture and raw scene Evidence')


def restore():
    prior.stopped()
    owned_paths()
    data = baseline()
    require(prior.ordinary_tree() == data['ordinarySave'], 'Ordinary save changed; never roll it back')
    backup = Path(data['backup'])
    require(backup.resolve() == backup and not backup.is_symlink(), 'Backup redirected')
    for name, value in data['config'].items():
        path = backup / name
        require(path.is_file() and not path.is_symlink() and sha(path) == value, 'Backup config changed')
    require(sha(backup / 'instance.cfg') == data['instanceSHA256'], 'Backup instance changed')
    normal = 'aqualumen-physics-0.2.0.jar'
    normal_paths = [p for p in (backup / normal, GAME / 'mods' / normal) if p.exists()]
    require(normal_paths and all(not p.is_symlink() and sha(p) == data['mods'][normal] for p in normal_paths), 'Normal physics recovery source differs')
    expected_jars = set(data['mods']) | set(data['testMods'])
    require({p.name for p in (GAME / 'mods').glob('*.jar')} <= expected_jars, 'Unexpected new Mod; do not mutate')
    for name, value in data['testMods'].items():
        for path in (GAME / 'mods' / name, backup / name):
            require(not path.exists() or path.is_file() and not path.is_symlink() and sha(path) == value, 'TEST Mod changed')
        require(not ((GAME / 'mods' / name).exists() and (backup / name).exists()), 'Recovery destination conflict')
    for path in (GAME / 'shaderpacks' / PACK, backup / PACK):
        require(not path.exists() or path.is_file() and not path.is_symlink() and sha(path) == data['packSHA256'], 'TEST pack changed')
    require(not ((GAME / 'shaderpacks' / PACK).exists() and (backup / PACK).exists()), 'Pack recovery conflict')
    for name in ('config/aqualumen-benchmark.enabled', REQUEST):
        path = GAME / name
        require(not path.exists() or path.is_file() and not path.is_symlink() and not (backup / path.name).exists(), 'Control recovery conflict')
    staged = [staging_path(GAME / 'mods' / name) for name in data['testMods']] + [staging_path(GAME / 'shaderpacks' / PACK)]
    for path in staged:
        require(not path.exists() or path.is_file() and not path.is_symlink() and not (backup / path.name).exists(), 'Staging recovery conflict')
    require(not (GAME / 'aqualumen-benchmark/request.properties').exists(), 'Pending client request')
    for name in data['testMods']:
        if (GAME / 'mods' / name).exists():
            shutil.move(GAME / 'mods' / name, backup / name)
    if not (GAME / 'mods' / normal).exists():
        shutil.move(backup / normal, GAME / 'mods' / normal)
    for name in CONFIG:
        shutil.copy2(backup / name, GAME / name)
    shutil.copy2(backup / 'instance.cfg', GAME.parent / 'instance.cfg')
    for name in ('config/aqualumen-benchmark.enabled', REQUEST):
        path = GAME / name
        if path.exists():
            shutil.move(path, backup / path.name)
    if (GAME / 'shaderpacks' / PACK).exists():
        shutil.move(GAME / 'shaderpacks' / PACK, backup / PACK)
    for path in staged:
        if path.exists():
            shutil.move(path, backup / path.name)
    checks = dict(normalConfigExact={name: sha(GAME / name) for name in CONFIG} == data['config'],
          normalModsExact={p.name: sha(p) for p in (GAME / 'mods').glob('*.jar')} == data['mods'],
          instanceExact=sha(GAME.parent / 'instance.cfg') == data['instanceSHA256'],
          ordinarySaveExact=prior.ordinary_tree() == data['ordinarySave'], ordinarySaveRestored=False,
          ordinaryPack='Aqualumen-0.6.0.zip', ordinaryPhysics='0.2.0', testArtifactsMovedTo=str(backup))
    require(all(checks[key] for key in ('normalConfigExact', 'normalModsExact', 'instanceExact', 'ordinarySaveExact')), 'Restoration mismatch')
    if not (OUT / 'restored.json').exists():
        save('restored.json', checks)
    print('Normal 0.6 / physics 0.2 restored exactly; ordinary save unchanged, no rollback')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('setup', 'launch', 'scene', 'observe', 'collect', 'quit', 'restore'))
    parser.add_argument('--pack', type=Path)
    parser.add_argument('--native', type=Path, help='Parent qualification.json binding native receipt and compile exits, not native fixture receipt.json')
    parser.add_argument('--scene', choices=('underwater-up-near', 'underwater-up-deep'), default='underwater-up-near')
    args = parser.parse_args()
    if args.action == 'setup':
        require(args.pack is not None and args.native is not None, '--pack and --native required')
        setup(args.pack.resolve(), args.native.resolve())
    elif args.action == 'scene':
        scene(args.scene)
    elif args.action == 'observe':
        observe(args.scene)
    elif args.action == 'collect':
        collect(args.scene)
    else:
        {'launch': launch, 'quit': quit_client, 'restore': restore}[args.action]()


if __name__ == '__main__':
    main()
