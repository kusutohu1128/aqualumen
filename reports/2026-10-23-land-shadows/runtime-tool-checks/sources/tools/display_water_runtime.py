"""Reversible Lab-only display/water comparison in the approved disposable world."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-11-display-water'
GAME = Path.home() / '.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances/Aqualumen Lab/minecraft'
WORLD = 'AqualumenNaturalV2'
WORLD_ID = 'b22dbccb-2970-41e6-847f-f183b1ec923d'
NAMES = ('options.txt', 'config/iris.properties', 'config/aqualumen-benchmark.properties')
MODS = {'aqualumen-benchmark-0.3.9-projection-guards.jar': 'ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29',
        'aqualumen-physics-0.3.0.jar': '958a34a9195f260921a43ea296a4968ef691339aac2b038129702d4ca572a310'}
PACKS = {'control': 'Aqualumen-DisplayWater-Control-2026-10-11.zip',
         'candidate': 'Aqualumen-DisplayWater-2026-10-11.zip'}
SCENES = ['ocean-day', 'ocean-dusk', 'underwater-up-near', 'underwater-up-deep', 'underwater-up-tilt', 'moving-view']
RUN_SUFFIX = '20261011-v1'
HEIGHT = 900
SAMPLE_SECONDS = 5
NATIVE_CHECK = OUT / 'native-check.log'
BENCH_PATH = None
PHYS_PATH = None
CHECK_RECEIPT = '13 program pairs compiled and linked'
RECOVER_STOPPED_PACKET = None
REFLECTION_NORMAL_COMPARISON = False
INTERFACE_NORMAL_COMPARISON = False


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stopped():
    result = subprocess.run(['pgrep', '-x', 'java'], stdout=subprocess.DEVNULL)
    require(result.returncode == 1, 'A Java process is live; do not alter runtime files')


def ordinary_tree():
    save = GAME / 'saves/新規ワールド'
    require(save.is_dir() and not save.is_symlink(), 'Ordinary save missing or redirected')
    paths = list(save.rglob('*'))
    require(not any(path.is_symlink() for path in paths), 'Ordinary save contains symlinks')
    return {path.relative_to(save).as_posix(): sha(path) for path in paths if path.is_file()}


def record(name, value):
    with (OUT / name).open('x') as output:
        json.dump(value, output, indent=2, sort_keys=True)


def baseline():
    return json.loads((OUT / 'runtime-baseline.json').read_text())


def verify_previous_exit():
    stopped()
    log = GAME / 'logs/latest.log'
    if 'Stopping!' in log.read_text():
        return
    require(RECOVER_STOPPED_PACKET in {'receiver-wide-batch-v30','underwater-raw-exit-v89'},
            'Clean client exit unproven; explicit owned recovery required')
    prior = ROOT / 'reports/2026-10-11-display-water' / RECOVER_STOPPED_PACKET
    failure = json.loads((prior / 'runtime-failure.json').read_text())
    parser_failure = RECOVER_STOPPED_PACKET == 'underwater-raw-exit-v89'
    reason = 'Iris vec4 clear-color directive parsing failed' if parser_failure else 'Receiver upload extent invalid'
    require(failure == dict(world_id=WORLD_ID, latestLogSHA256=sha(log), reason=reason,
            javaAbsentVerified=True, benchmarkStarted=False, launcherTerminatedAfterClientExit=True), 'Owned failure receipt differs')
    if parser_failure:
        require('expected 4 arguments to a vec4 constructor, got 1' in log.read_text()
                and 'DispatchingDirectiveHolder.processDirective' in log.read_text(), 'Owned Iris parser failure differs')
        launch = json.loads((prior / 'candidate-launcher-start.json').read_text())
        require(launch['world_id'] == WORLD_ID
                and launch['pack'] == 'Aqualumen-RawExitDirectionDiagnostic-v89-2026-10-11.zip',
                'Owned parser-failure launch identity differs')
    else:
        require('java.lang.IllegalArgumentException: Receiver upload extent invalid' in log.read_text()
                and 'Stopping worker threads' in log.read_text(), 'Owned client terminal state unproven')
    require(json.loads((prior / 'candidate-launcher-exit.json').read_text()) == dict(exitCode=143), 'Owned failed launcher is not terminal')
    restored = json.loads((prior / 'runtime-restored.json').read_text())
    require(restored == dict(normalConfigExact=True, normalModsExact=True, ordinarySaveExact=True,
            instanceConfigChangedByLauncher=False, ordinarySaveRestored=False), 'Owned failed runtime restoration unproven')
    previous = json.loads((prior / 'runtime-baseline.json').read_text())
    require({name: sha(GAME / name) for name in NAMES} == previous['config']
            and {path.name: sha(path) for path in (GAME / 'mods').glob('*.jar')} == previous['mods']
            and sha(GAME.parent / 'instance.cfg') == previous['instanceConfigSHA256']
            and ordinary_tree() == previous['ordinarySave'], 'Restored environment differs from owned pre-failure baseline')


def setup():
    stopped()
    require(not (OUT / 'runtime-baseline.json').exists(), 'Runtime baseline already exists')
    require_scene_capability()
    require(CHECK_RECEIPT in NATIVE_CHECK.read_text(), 'Native checks missing')
    verify_previous_exit()
    marker = dict(line.split('=', 1) for line in (GAME / 'saves' / WORLD / 'aqualumen-world.properties').read_text().splitlines())
    require(marker == dict(schema='2', world_id=WORLD_ID, seed='308060', generator='minecraft:noise/overworld', minecraft='1.21.1'), 'Unapproved world')
    require(not (GAME / 'aqualumen-benchmark/request.properties').exists(), 'Pending request exists')
    active = {path.name: sha(path) for path in (GAME / 'mods').glob('*.jar')}
    require(set(active) == {'aqualumen-physics-0.2.0.jar', 'iris-fabric-1.8.8+mc1.21.1.jar', 'sodium-fabric-0.6.9+mc1.21.1.jar'}, 'Unexpected active Mods')
    controls = [path for path in (GAME / 'config').iterdir() if path.name.startswith('aqualumen-') and (path.name.endswith('.enabled') or 'observe' in path.name and path.suffix == '.properties')]
    require(not controls, 'Development entry points already enabled')
    require('shaderPack=Aqualumen-0.6.0.zip' in (GAME / 'config/iris.properties').read_text(), 'Unexpected ordinary pack')
    with ZipFile(ROOT / 'reports/2026-10-06-water-legacy-branch/actual-test-mods.zip') as archive:
        local_names = {path.name for path in (BENCH_PATH, PHYS_PATH) if path is not None}
        blobs = {name: archive.read(name) for name in MODS if name not in local_names}
    if BENCH_PATH is not None:
        blobs[BENCH_PATH.name] = BENCH_PATH.read_bytes()
    if PHYS_PATH is not None:
        blobs[PHYS_PATH.name] = PHYS_PATH.read_bytes()
    require({name: hashlib.sha256(blob).hexdigest() for name, blob in blobs.items()} == MODS, 'Archived test Mod hashes changed')
    backup = Path(tempfile.mkdtemp(prefix='aqualumen-display-water-', dir=Path.home() / '.cache'))
    os.chmod(backup, 0o700)
    for name in NAMES:
        (backup / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(GAME / name, backup / name)
    shutil.copy2(GAME.parent / 'instance.cfg', backup / 'instance.cfg')
    record('runtime-baseline.json', dict(backup=str(backup), config={name: sha(GAME / name) for name in NAMES},
           mods=active, ordinarySave=ordinary_tree(), instanceConfigSHA256=sha(GAME.parent / 'instance.cfg')))
    if HEIGHT != 900:
        instance = (backup / 'instance.cfg').read_text()
        require(instance.count('MinecraftWinHeight=900') == 1, 'Unexpected instance height')
        (GAME.parent / 'instance.cfg').write_text(instance.replace('MinecraftWinHeight=900', 'MinecraftWinHeight='+str(HEIGHT)))
    with ZipFile(ROOT / 'dist' / PACKS['candidate']) as source:
        with ZipFile(OUT / PACKS['control'], 'x', compression=ZIP_DEFLATED) as target:
            for entry in source.infolist():
                if INTERFACE_NORMAL_COMPARISON:
                    content = source.read(entry.filename)
                    if entry.filename == 'shaders/gbuffers_water.fsh':
                        define = b'#define AQUALUMEN_INTERFACE_NORMAL_COMPARISON\n'
                        require(content.count(define) == 1, 'Interface normal control define is not unique')
                        content = content.replace(define, b'')
                    target.writestr(entry, content)
                elif REFLECTION_NORMAL_COMPARISON:
                    content = source.read(entry.filename)
                    if entry.filename == 'shaders/gbuffers_water.fsh':
                        call = b'    if (underwater && upperSurface)\n        n=waterReflectionNormal(n,geometricNormal,v);\n'
                        require(content.count(call) == 1, 'Reflection normal control call is not unique')
                        content = content.replace(call, b'')
                    target.writestr(entry, content)
                elif entry.filename not in {'shaders/composite1.vsh', 'shaders/composite1.fsh', 'shaders/composite2.vsh', 'shaders/composite2.fsh'}:
                    target.writestr(entry, source.read(entry.filename))
    for role, name in PACKS.items():
        source = OUT / name if role == 'control' else ROOT / 'dist' / name
        with (GAME / 'shaderpacks' / name).open('xb') as target:
            target.write(source.read_bytes())
    shutil.move(GAME / 'mods/aqualumen-physics-0.2.0.jar', backup / 'aqualumen-physics-0.2.0.jar')
    for name, blob in blobs.items():
        with (GAME / 'mods' / name).open('xb') as target:
            target.write(blob)
    print('Prepared reversible Lab-only comparison; ordinary saves untouched')


def require_scene_capability():
    if set(SCENES).intersection({'ocean-sun-day','ocean-sun-dusk'}):
        name='aqualumen-benchmark-0.3.9-sun-views-v3.jar'
        require(BENCH_PATH is not None and BENCH_PATH.name==name
                and MODS.get(name)=='167a957c559e1c5415838d60f5cd84b91dfa1f16511015caa60dcb24675e89e3',
                'Dedicated Sun scenes require the qualified Sun-view benchmark')


def select(role):
    stopped()
    data = baseline()
    require(ordinary_tree() == data['ordinarySave'], 'Ordinary save changed')
    require({name: sha(GAME / 'mods' / name) for name in MODS} == MODS, 'Test Mods changed')
    iris = (Path(data['backup']) / 'config/iris.properties').read_text()
    iris = iris.replace('shaderPack=Aqualumen-0.6.0.zip', 'shaderPack=' + PACKS[role])
    (GAME / 'config/iris.properties').write_text(iris)
    options = (Path(data['backup']) / 'options.txt').read_text().splitlines()
    changes = {'renderDistance': '12', 'simulationDistance': '6', 'maxFps': '120', 'enableVsync': 'false', 'fullscreen': 'false', 'pauseOnLostFocus': 'false',
               'overrideWidth': '1600', 'overrideHeight': str(HEIGHT)}
    for index, line in enumerate(options):
        key = line.split(':', 1)[0]
        if key in changes:
            options[index] = key + ':' + changes.pop(key)
    require(not changes, 'Expected normal options missing')
    (GAME / 'options.txt').write_text('\n'.join(options) + '\n')
    values = dict(schema='2', world=WORLD, world_id=WORLD_ID, expected_pack=PACKS[role],
                  expected_pack_sha256=sha(GAME / 'shaderpacks' / PACKS[role]), width='1600', height=str(HEIGHT), render_chunks='12', simulation_chunks='6')
    if BENCH_PATH is not None:
        values['capture_motion'] = 'true'
    (GAME / 'config/aqualumen-benchmark.properties').write_text('\n'.join(key+'='+value for key, value in values.items())+'\n')
    (GAME / 'config/aqualumen-benchmark.enabled').write_text('Approved disposable V2 only\n')
    record(role+'-runtime-inputs.json', values)


def require_current_pipeline(log, previous):
    require(hashlib.sha256(log[:previous['bytes']]).hexdigest() != previous['sha256'],
            'Latest log still belongs to the previous client')
    text = log.decode('utf-8', errors='replace')
    server = text.find('Preparing start region for dimension minecraft:overworld')
    pipeline = text.find('Creating pipeline for dimension minecraft:overworld', max(0, server))
    require(server >= 0 and pipeline > server, 'Current singleplayer world pipeline is not loaded yet')


def start(role):
    require(subprocess.run(['pgrep', '-x', 'java'], stdout=subprocess.DEVNULL).returncode == 0, 'TEST client is not live')
    require('shaderPack='+PACKS[role] in (GAME / 'config/iris.properties').read_text(), 'Wrong selected pack')
    launch = json.loads((OUT / (role+'-launcher-start.json')).read_text())
    require(launch['world_id'] == WORLD_ID and launch['pack'] == PACKS[role], 'Owned launch identity differs')
    require_current_pipeline((GAME / 'logs/latest.log').read_bytes(), launch['previousLog'])
    subprocess.run(['python3', 'tools/benchmark-control.py', 'start', '--run-id', 'display-water-'+role+'-'+RUN_SUFFIX,
                    '--scenes', *SCENES,
                    '--warmup', '5', '--sample', str(SAMPLE_SECONDS), '--auto-quit'], cwd=ROOT, check=True)


def profile_start(role):
    launch_receipt = json.loads((OUT / (role+'-launcher-start.json')).read_text())
    require(launch_receipt['world_id'] == WORLD_ID and
            launch_receipt['pack'] == PACKS[role], 'Profile launch identity differs')
    status = json.loads((GAME / 'aqualumen-benchmark/status.json').read_text())
    run_id = 'display-water-'+role+'-'+RUN_SUFFIX
    require(status['run_id'] == run_id and status['state'] in {'warmup', 'sampling'},
            'Profile requires the owned active sampling run')
    processes = subprocess.check_output(['pgrep', '-x', 'java'], text=True).split()
    require(len(processes) == 1, 'Profile requires exactly one owned Java process')
    pid = processes[0]
    require(Path(os.readlink('/proc/'+pid+'/cwd')) == GAME, 'Java does not own the Lab cwd')
    private = GAME / 'aqualumen-benchmark/profiles' / run_id
    private.mkdir(parents=True, mode=0o700)
    os.chmod(private, 0o700)
    jcmd = GAME.parents[2] / 'java/java-runtime-delta/bin/jcmd'
    relative = (private / 'recording.jfr').relative_to(GAME)
    result = subprocess.run([str(jcmd), pid, 'JFR.start', 'name=AqualumenOwned',
        'settings=profile', 'duration=30s', 'dumponexit=true', 'filename='+str(relative)],
        capture_output=True, text=True)
    response = result.stdout + result.stderr
    with (private / 'start-response.txt').open('x') as receipt:
        os.chmod(receipt.name, 0o600)
        receipt.write(response)
    require(result.returncode == 0 and 'Started recording ' in result.stdout,
            'JFR did not confirm recording startup; raw response retained privately')
    record(role+'-profile-start.json', dict(pid=int(pid), run_id=run_id,
        private_directory=str(private), recording_start_confirmed=True,
        recording_finalized=False, benchmark_timings_include_profiling=True))
    print('Owned JFR startup confirmed; finalized recording still requires verification')


def launch(role):
    stopped()
    data = baseline()
    require('shaderPack='+PACKS[role] in (GAME / 'config/iris.properties').read_text(), 'Wrong selected pack')
    private = Path(data['backup']) / (role+'-launcher-private.log')
    descriptor = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as output:
        previous = (GAME / 'logs/latest.log').read_bytes()
        record(role+'-launcher-start.json', dict(world_id=WORLD_ID, pack=PACKS[role],
            previousLog=dict(bytes=len(previous), sha256=hashlib.sha256(previous).hexdigest())))
        result = subprocess.run(['flatpak', 'run', '--command=prismrun', 'org.prismlauncher.PrismLauncher', '--launch', 'Aqualumen Lab', '--world', WORLD],
                                env=dict(os.environ, DISPLAY=':1'), stdout=output, stderr=subprocess.STDOUT)
    record(role+'-launcher-exit.json', dict(exitCode=result.returncode))
    print('Owned TEST launcher exited', result.returncode)


def collect(role):
    source = GAME / 'aqualumen-benchmark/runs' / ('display-water-'+role+'-'+RUN_SUFFIX)
    require((source / 'run.json').is_file(), 'Complete run manifest missing')
    manifest = json.loads((source / 'run.json').read_text())
    require(manifest['world_id'] == WORLD_ID and manifest['pack_name'] == PACKS[role], 'Run identity mismatch')
    require(manifest['shader_active'] and not manifest['shader_fallback'], 'Iris activation failed')
    require('NVIDIA' in manifest['gl_renderer'], 'Not an NVIDIA runtime')
    require(manifest['pack_sha256'] == sha(GAME / 'shaderpacks' / PACKS[role]), 'Pack differs from installed bytes')
    for scene in SCENES:
        sample = json.loads((source / (scene+'.json')).read_text())
        require(sample['scenario'] == scene and sample['frames'] > 0 and sample['shader_active'] and not sample['shader_fallback'], 'Incomplete scene')
        require((source / (scene+'.png')).is_file() and (source / (scene+'.csv')).is_file(), 'Raw image/timing missing')
    target = OUT / (role+'-runtime')
    require(not target.exists(), 'Do not overwrite evidence')
    shutil.copytree(source, target)
    receiver_lines = [line for line in (GAME / 'logs/latest.log').read_text().splitlines()
                      if '[STDOUT]: [Aqualumen Receiver] ' in line]
    if receiver_lines:
        with (OUT / (role+'-receiver-runtime.log')).open('x') as receipt:
            receipt.write('\n'.join(receiver_lines)+'\n')
    print('Archived', target)


def restore():
    stopped()
    data = baseline()
    require(ordinary_tree() == data['ordinarySave'], 'Ordinary save changed; do not restore old save')
    backup = Path(data['backup'])
    for name in MODS:
        require(sha(GAME / 'mods' / name) == MODS[name], 'Installed test Mod changed')
    require(not (GAME / 'aqualumen-benchmark/request.properties').exists(), 'Unacknowledged request remains')
    for name in MODS:
        shutil.move(GAME / 'mods' / name, backup / name)
    shutil.move(backup / 'aqualumen-physics-0.2.0.jar', GAME / 'mods/aqualumen-physics-0.2.0.jar')
    for name in NAMES:
        shutil.copy2(backup / name, GAME / name)
    if (backup / 'instance.cfg').is_file():
        shutil.copy2(backup / 'instance.cfg', GAME.parent / 'instance.cfg')
    (GAME / 'config/aqualumen-benchmark.enabled').unlink(missing_ok=True)
    require({name: sha(GAME / name) for name in NAMES} == data['config'], 'Normal configuration differs')
    require({path.name: sha(path) for path in (GAME / 'mods').glob('*.jar')} == data['mods'], 'Normal Mods differ')
    record('runtime-restored.json', dict(normalConfigExact=True, normalModsExact=True, ordinarySaveExact=ordinary_tree() == data['ordinarySave'],
           instanceConfigChangedByLauncher=sha(GAME.parent / 'instance.cfg') != data['instanceConfigSHA256'], ordinarySaveRestored=False))
    print('Normal config/Mods restored exactly; no save rollback')


def collect_failed(role):
    stopped()
    run_id = 'display-water-'+role+'-'+RUN_SUFFIX
    source = GAME / 'aqualumen-benchmark/runs' / run_id
    manifest = json.loads((source / 'run.json').read_text())
    failure = json.loads((source / 'aborted.json').read_text())
    require(manifest['world_id'] == WORLD_ID and manifest['pack_name'] == PACKS[role], 'Failed run identity mismatch')
    require(manifest['shader_active'] and not manifest['shader_fallback'] and 'NVIDIA' in manifest['gl_renderer'], 'Failed run activation unproven')
    require(manifest['pack_sha256'] == sha(GAME / 'shaderpacks' / PACKS[role]), 'Failed run pack bytes differ')
    require(failure['run_id'] == run_id and failure['status'] == 'aborted' and failure['fixture_cleanup_complete'], 'Unowned or unclean failed run')
    target = OUT / (role+'-aborted-runtime')
    require(not target.exists(), 'Do not overwrite failed evidence')
    shutil.copytree(source, target)
    receiver_lines = [line for line in (GAME / 'logs/latest.log').read_text().splitlines()
                      if '[STDOUT]: [Aqualumen Receiver] ' in line]
    if receiver_lines:
        with (OUT / (role+'-receiver-runtime.log')).open('x') as receipt:
            receipt.write('\n'.join(receiver_lines)+'\n')
    print('Archived failed run, not runtime acceptance:', target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['setup', 'select', 'launch', 'start', 'profile-start', 'collect', 'collect-failed', 'restore'])
    parser.add_argument('--role', choices=PACKS, default='control')
    parser.add_argument('--recover-stopped-packet', choices=['receiver-wide-batch-v30','underwater-raw-exit-v89'])
    packet_option = parser.add_argument('--packet', choices=['initial', 'solar-tir-v2', 'native-motion-v3', 'ssr-diagnostic-v4', 'sun-views-v5', 'wide-glare-v6', 'wide-glare-v7', 'receiver-bridge-v8', 'receiver-lighting-v9', 'receiver-lighting-detail-v10', 'receiver-lighting-depth-v11', 'receiver-prepare-v12', 'receiver-prepare-bound-v13', 'receiver-owned-sodium-v14', 'receiver-owned-sodium-columns-v15', 'receiver-owned-sodium-material-v16', 'receiver-owned-sodium-diagnostic-v17', 'receiver-owned-sodium-face-v18', 'receiver-owned-encoder-v20', 'receiver-terrain-input-v21'], default='initial')
    packet_option.choices.extend(['receiver-source-point-v22', 'receiver-source-point-core-v23', 'receiver-source-point-compiled-v24', 'receiver-source-volume-v25', 'receiver-source-volume-bound-v26', 'receiver-source-updates-v27'])
    packet_option.choices.append('receiver-partial-macro-v29')
    packet_option.choices.append('receiver-wide-batch-v30')
    packet_option.choices.append('receiver-wide-batch-v31')
    packet_option.choices.append('receiver-phase-cache-v32')
    packet_option.choices.append('receiver-interface-crest-v33')
    packet_option.choices.append('receiver-residual-normal-v34')
    packet_option.choices.append('receiver-outcome-v35')
    packet_option.choices.append('receiver-rejection-v36')
    packet_option.choices.append('receiver-live-runs-v42')
    packet_option.choices.append('receiver-stage-profile-v43')
    packet_option.choices.append('receiver-lazy-solid-v44')
    packet_option.choices.append('receiver-stack-profile-v45')
    packet_option.choices.append('receiver-stack-profile-v46')
    packet_option.choices.append('receiver-coordinate-hash-v47')
    packet_option.choices.append('receiver-typed-geometry-v48')
    packet_option.choices.append('receiver-indexed-cache-v49')
    packet_option.choices.append('receiver-field-metadata-v50')
    packet_option.choices.append('receiver-wide-rejection-v51')
    packet_option.choices.append('receiver-unknown-kinds-v52')
    packet_option.choices.append('receiver-plant-model-v53')
    packet_option.choices.append('receiver-plant-packed-v54')
    packet_option.choices.append('receiver-plant-alpha-v55')
    packet_option.choices.append('receiver-plant-atlas-metadata-v56')
    packet_option.choices.append('receiver-plant-alpha-rgba-v57')
    packet_option.choices.append('receiver-plant-live-gpu-v59')
    packet_option.choices.append('receiver-plant-fluid-v61')
    packet_option.choices.append('receiver-plant-region-v69')
    packet_option.choices.append('receiver-natural-review-v76')
    packet_option.choices.append('receiver-natural-sun-v77')
    packet_option.choices.append('underwater-normal-comparison-v80')
    packet_option.choices.append('receiver-owner-profile-v81')
    packet_option.choices.append('receiver-owner-profile-v82')
    packet_option.choices.append('receiver-classification-v83')
    packet_option.choices.append('receiver-pack-predicate-v84')
    packet_option.choices.append('receiver-plant-material-v85')
    packet_option.choices.append('receiver-plant-material-v86')
    packet_option.choices.append('underwater-interface-v87')
    packet_option.choices.append('underwater-exit-direction-v88')
    packet_option.choices.append('underwater-raw-exit-v89')
    packet_option.choices.append('underwater-raw-exit-v90')
    packet_option.choices.append('underwater-coupled-normal-v91')
    packet_option.choices.append('underwater-coupled-beauty-v92')
    packet_option.choices.append('underwater-raw-receiver-v93')
    packet_option.choices.append('underwater-raw-rejection-v94')
    packet_option.choices.append('underwater-raw-unknown-v95')
    packet_option.choices.append('receiver-plant-owner-bounds-v96')
    packet_option.choices.append('receiver-plant-window-v97')
    packet_option.choices.append('receiver-plant-tiled-v98')
    packet_option.choices.append('receiver-plant-fluid-publication-v99')
    packet_option.choices.append('receiver-plant-owner-halo-v100')
    args = parser.parse_args()
    require(args.recover_stopped_packet is None or args.action == 'setup' and
            (args.recover_stopped_packet,args.packet) in {
                ('receiver-wide-batch-v30','receiver-wide-batch-v31'),
                ('underwater-raw-exit-v89','underwater-raw-exit-v90')},
            'Owned recovery is restricted to the exact successor setup')
    RECOVER_STOPPED_PACKET = args.recover_stopped_packet
    requested_packet = args.packet
    plant_owner_halo_packet = requested_packet == 'receiver-plant-owner-halo-v100'
    if plant_owner_halo_packet:
        requested_packet = 'receiver-plant-fluid-publication-v99'
    plant_fluid_publication_packet = requested_packet == 'receiver-plant-fluid-publication-v99'
    if plant_fluid_publication_packet:
        requested_packet = 'receiver-plant-tiled-v98'
    plant_tiled_packet = requested_packet == 'receiver-plant-tiled-v98'
    if plant_tiled_packet:
        requested_packet = 'receiver-plant-window-v97'
    plant_window_packet = requested_packet == 'receiver-plant-window-v97'
    if plant_window_packet:
        requested_packet = 'receiver-plant-owner-bounds-v96'
    plant_owner_bounds_packet = requested_packet == 'receiver-plant-owner-bounds-v96'
    if plant_owner_bounds_packet:
        requested_packet = 'underwater-raw-unknown-v95'
    raw_unknown_packet = requested_packet == 'underwater-raw-unknown-v95'
    if raw_unknown_packet:
        requested_packet = 'underwater-raw-rejection-v94'
    raw_rejection_packet = requested_packet == 'underwater-raw-rejection-v94'
    if raw_rejection_packet:
        requested_packet = 'underwater-raw-receiver-v93'
    raw_receiver_packet = requested_packet == 'underwater-raw-receiver-v93'
    if raw_receiver_packet:
        requested_packet = 'underwater-coupled-beauty-v92'
    coupled_beauty_packet = requested_packet == 'underwater-coupled-beauty-v92'
    if coupled_beauty_packet:
        requested_packet = 'underwater-coupled-normal-v91'
    coupled_normal_packet = requested_packet == 'underwater-coupled-normal-v91'
    if coupled_normal_packet:
        requested_packet = 'underwater-raw-exit-v90'
    raw_exit_retry = requested_packet == 'underwater-raw-exit-v90'
    if raw_exit_retry:
        requested_packet = 'underwater-raw-exit-v89'
    raw_exit_packet = requested_packet == 'underwater-raw-exit-v89'
    if raw_exit_packet:
        requested_packet = 'underwater-exit-direction-v88'
    exit_direction_packet = requested_packet == 'underwater-exit-direction-v88'
    if exit_direction_packet:
        requested_packet = 'underwater-interface-v87'
    interface_packet = requested_packet == 'underwater-interface-v87'
    if interface_packet:
        requested_packet = 'receiver-plant-material-v86'
    plant_material_region_packet = requested_packet == 'receiver-plant-material-v86'
    if plant_material_region_packet:
        requested_packet = 'receiver-plant-material-v85'
    plant_material_packet = requested_packet == 'receiver-plant-material-v85'
    if plant_material_packet:
        requested_packet = 'receiver-plant-region-v69'
    pack_predicate_packet = requested_packet == 'receiver-pack-predicate-v84'
    if pack_predicate_packet:
        requested_packet = 'receiver-classification-v83'
    classification_packet = requested_packet == 'receiver-classification-v83'
    if classification_packet:
        requested_packet = 'receiver-owner-profile-v81'
    owner_profile_retry = requested_packet == 'receiver-owner-profile-v82'
    owner_profile_packet = requested_packet in {'receiver-owner-profile-v81', 'receiver-owner-profile-v82'}
    if owner_profile_packet:
        requested_packet = 'receiver-natural-sun-v77'
    reflection_normal_packet = requested_packet == 'underwater-normal-comparison-v80'
    if reflection_normal_packet:
        requested_packet = 'receiver-natural-sun-v77'
    natural_sun_packet = requested_packet == 'receiver-natural-sun-v77'
    if natural_sun_packet:
        requested_packet = 'receiver-natural-review-v76'
    natural_review_packet = requested_packet == 'receiver-natural-review-v76'
    if natural_review_packet:
        requested_packet = 'receiver-plant-region-v69'
    plant_region_packet = requested_packet == 'receiver-plant-region-v69'
    if plant_region_packet:
        requested_packet = 'receiver-plant-fluid-v61'
    plant_fluid_packet = requested_packet == 'receiver-plant-fluid-v61'
    if plant_fluid_packet:
        requested_packet = 'receiver-plant-live-gpu-v59'
    plant_live_gpu_packet = requested_packet == 'receiver-plant-live-gpu-v59'
    if plant_live_gpu_packet:
        requested_packet = 'receiver-plant-alpha-rgba-v57'
    plant_alpha_rgba_packet = requested_packet == 'receiver-plant-alpha-rgba-v57'
    plant_atlas_metadata_packet = requested_packet in {'receiver-plant-atlas-metadata-v56', 'receiver-plant-alpha-rgba-v57'}
    plant_alpha_packet = requested_packet in {'receiver-plant-alpha-v55', 'receiver-plant-atlas-metadata-v56', 'receiver-plant-alpha-rgba-v57'}
    plant_packed_packet = requested_packet in {'receiver-plant-packed-v54', 'receiver-plant-alpha-v55', 'receiver-plant-atlas-metadata-v56', 'receiver-plant-alpha-rgba-v57'}
    plant_model_packet = requested_packet in {'receiver-plant-model-v53', 'receiver-plant-packed-v54', 'receiver-plant-alpha-v55', 'receiver-plant-atlas-metadata-v56', 'receiver-plant-alpha-rgba-v57'}
    if plant_model_packet:
        requested_packet = 'receiver-unknown-kinds-v52'
    unknown_kinds_packet = requested_packet == 'receiver-unknown-kinds-v52'
    wide_rejection_packet = requested_packet == 'receiver-wide-rejection-v51'
    field_metadata_packet = requested_packet in {'receiver-field-metadata-v50', 'receiver-wide-rejection-v51', 'receiver-unknown-kinds-v52'}
    indexed_cache_packet = requested_packet == 'receiver-indexed-cache-v49'
    typed_geometry_packet = requested_packet == 'receiver-typed-geometry-v48'
    coordinate_hash_packet = requested_packet == 'receiver-coordinate-hash-v47'
    stack_profile_retry = requested_packet == 'receiver-stack-profile-v46'
    stack_profile_packet = requested_packet in {'receiver-stack-profile-v45', 'receiver-stack-profile-v46'}
    lazy_solid_packet = requested_packet in {'receiver-lazy-solid-v44', 'receiver-stack-profile-v45', 'receiver-stack-profile-v46', 'receiver-coordinate-hash-v47', 'receiver-typed-geometry-v48', 'receiver-indexed-cache-v49', 'receiver-field-metadata-v50', 'receiver-wide-rejection-v51', 'receiver-unknown-kinds-v52'}
    if lazy_solid_packet:
        requested_packet = 'receiver-stage-profile-v43'
    if requested_packet in {'receiver-partial-macro-v29','receiver-wide-batch-v30','receiver-wide-batch-v31','receiver-phase-cache-v32','receiver-interface-crest-v33','receiver-residual-normal-v34','receiver-outcome-v35','receiver-rejection-v36','receiver-live-runs-v42','receiver-stage-profile-v43'}:
        args.packet = 'receiver-owned-sodium-face-v18'
    if requested_packet in {'receiver-owned-encoder-v20', 'receiver-terrain-input-v21', 'receiver-source-point-v22', 'receiver-source-point-core-v23', 'receiver-source-point-compiled-v24', 'receiver-source-volume-v25', 'receiver-source-volume-bound-v26', 'receiver-source-updates-v27'}:
        args.packet = 'receiver-owned-sodium-face-v18'
    if args.packet == 'solar-tir-v2':
        NATIVE_CHECK = OUT / 'native-check-solar-domain.log'
        OUT = OUT / 'solar-tir-v2'
        OUT.mkdir(exist_ok=True)
        HEIGHT = 800
        RUN_SUFFIX = '20261011-v2'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-SolarTIR-v2-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-SolarTIR-v2-2026-10-11.zip'}
    if args.packet in {'native-motion-v3', 'ssr-diagnostic-v4', 'sun-views-v5', 'wide-glare-v6', 'wide-glare-v7', 'receiver-bridge-v8', 'receiver-lighting-v9', 'receiver-lighting-detail-v10', 'receiver-lighting-depth-v11', 'receiver-prepare-v12', 'receiver-prepare-bound-v13', 'receiver-owned-sodium-v14', 'receiver-owned-sodium-columns-v15', 'receiver-owned-sodium-material-v16', 'receiver-owned-sodium-diagnostic-v17', 'receiver-owned-sodium-face-v18'}:
        NATIVE_CHECK = OUT / ('native-check-ssr-diagnostic.log' if args.packet == 'ssr-diagnostic-v4' else 'native-check-solar-domain.log')
        OUT = OUT / args.packet
        OUT.mkdir(exist_ok=True)
        HEIGHT = 800
        RUN_SUFFIX = '20261011-v3'
        SCENES = ['underwater-up-moving', 'underwater-up-near', 'moving-view']
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-NativeMotion-v3-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-NativeMotion-v3-2026-10-11.zip'}
        BENCH_PATH = ROOT / 'build/aqualumen-benchmark-0.3.9-native-motion-v2.jar'
        MODS = {BENCH_PATH.name: 'eb54a151eeb688d89fb18527b18b0765ed182e30fbfba7beaa8740efe99c15d1',
                'aqualumen-physics-0.3.0.jar': MODS['aqualumen-physics-0.3.0.jar']}
        if args.packet == 'ssr-diagnostic-v4':
            RUN_SUFFIX = '20261011-v4'
            CHECK_RECEIPT = 'PASS compile/link only; no compute dispatch, draw, readback, regression or visual acceptance'
            SCENES = ['underwater-up-moving', 'underwater-up-near']
            PACKS = {'control': 'Aqualumen-TEST-UnderwaterSSR-Control-v4-2026-10-11.zip',
                     'candidate': 'Aqualumen-TEST-UnderwaterSSR-v4-2026-10-11.zip'}
        if args.packet in {'sun-views-v5', 'wide-glare-v6', 'wide-glare-v7'}:
            NATIVE_CHECK = OUT.parent / 'native-check-reflection-join.log'
            RUN_SUFFIX = '20261011-v5'
            SCENES = ['ocean-sun-day', 'ocean-sun-dusk']
            PACKS = {'control': 'Aqualumen-DisplayWater-Control-SunViews-v5-2026-10-11.zip',
                     'candidate': 'Aqualumen-DisplayWater-SunViews-v5-2026-10-11.zip'}
            BENCH_PATH = ROOT / 'build/aqualumen-benchmark-0.3.9-sun-views-v3.jar'
            MODS = {BENCH_PATH.name: '167a957c559e1c5415838d60f5cd84b91dfa1f16511015caa60dcb24675e89e3',
                    'aqualumen-physics-0.3.0.jar': MODS['aqualumen-physics-0.3.0.jar']}
            if args.packet == 'wide-glare-v6':
                NATIVE_CHECK = OUT.parent / 'native-check-wide-glare.log'
                RUN_SUFFIX = '20261011-v6'
                SCENES += ['underwater-up-moving']
                PACKS = {'control': 'Aqualumen-DisplayWater-Control-WideGlare-v6-2026-10-11.zip',
                         'candidate': 'Aqualumen-DisplayWater-WideGlare-v6-2026-10-11.zip'}
            if args.packet == 'wide-glare-v7':
                NATIVE_CHECK = OUT.parent / 'native-check-six-sigma.log'
                RUN_SUFFIX = '20261011-v7'
                SCENES += ['underwater-up-moving']
                PACKS = {'control': 'Aqualumen-DisplayWater-Control-WideGlare-v7-2026-10-11.zip',
                         'candidate': 'Aqualumen-DisplayWater-WideGlare-v7-2026-10-11.zip'}
        if args.packet == 'receiver-bridge-v8':
            NATIVE_CHECK = OUT.parent / 'native-check-receiver-bridge.log'
            RUN_SUFFIX = '20261011-v8'
            SCENES = ['underwater-up-moving', 'underwater-up-near']
            PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverBridge-v8-2026-10-11.zip',
                     'candidate': 'Aqualumen-DisplayWater-ReceiverBridge-v8-2026-10-11.zip'}
            PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-bridge-v1.jar'
            MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                    PHYS_PATH.name: 'ec3ef58baa59528395efe3cdba4ac2fb10a7b8d43d0629d2e03c581f3937fdc1'}
        if args.packet in {'receiver-lighting-v9', 'receiver-lighting-detail-v10', 'receiver-lighting-depth-v11'}:
            NATIVE_CHECK = OUT.parent / 'native-check-shared-receiver-shading-final.log'
            RUN_SUFFIX = '20261011-v9'
            SCENES = ['underwater-up-moving', 'underwater-up-near']
            PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverLighting-v9-2026-10-11.zip',
                     'candidate': 'Aqualumen-DisplayWater-ReceiverLighting-v9-2026-10-11.zip'}
            PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-lighting-v6.jar'
            MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                    PHYS_PATH.name: '721d79e079355c4bd8fcd50aafb5529689b04d1c6749aa45e3d6fac8ae1eae65'}
            if args.packet == 'receiver-lighting-detail-v10':
                RUN_SUFFIX = '20261011-v10'
                SCENES = ['underwater-up-near']
                PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverLightingDetail-v10-2026-10-11.zip',
                         'candidate': 'Aqualumen-DisplayWater-ReceiverLightingDetail-v10-2026-10-11.zip'}
                PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-lighting-v7.jar'
                MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                        PHYS_PATH.name: '350ebe55d22b05ca462f09a3e66548ec8a838d68ccc4e1c4a88dd98b07d913f8'}
            if args.packet == 'receiver-lighting-depth-v11':
                RUN_SUFFIX = '20261011-v11'
                SCENES = ['underwater-up-near']
                PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverLightingDepth-v11-2026-10-11.zip',
                         'candidate': 'Aqualumen-DisplayWater-ReceiverLightingDepth-v11-2026-10-11.zip'}
                PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-lighting-v8.jar'
                MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                        PHYS_PATH.name: 'c20e3b8d9302bd754812ea15d90069b62703a03dbe0c80f543027bf79126ee35'}
        if args.packet in {'receiver-prepare-v12', 'receiver-prepare-bound-v13', 'receiver-owned-sodium-v14', 'receiver-owned-sodium-columns-v15', 'receiver-owned-sodium-material-v16', 'receiver-owned-sodium-diagnostic-v17', 'receiver-owned-sodium-face-v18'}:
            NATIVE_CHECK = OUT.parent / 'native-prepare-source-full.log'
            CHECK_RECEIPT = '14 program pairs compiled and linked'
            RUN_SUFFIX = '20261011-v12'
            SCENES = ['underwater-up-near']
            PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverPrepare-v12-2026-10-11.zip',
                     'candidate': 'Aqualumen-DisplayWater-ReceiverPrepare-v12-2026-10-11.zip'}
            PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-prepare-v10.jar'
            MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                    PHYS_PATH.name: '0eed28eefe7dd35fdc80ae3d88b8146557c7966a52dfe5762ede18ab3f914e51'}
            if args.packet == 'receiver-prepare-bound-v13':
                RUN_SUFFIX = '20261011-v13'
                PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverPrepareBound-v13-2026-10-11.zip',
                         'candidate': 'Aqualumen-DisplayWater-ReceiverPrepareBound-v13-2026-10-11.zip'}
                PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-prepare-v11.jar'
                MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                        PHYS_PATH.name: '28e4e04daafb9e728b9804d590a01e132492214c704d6ba42237ccdc768a0c9c'}
            if args.packet in {'receiver-owned-sodium-v14', 'receiver-owned-sodium-columns-v15', 'receiver-owned-sodium-material-v16', 'receiver-owned-sodium-diagnostic-v17', 'receiver-owned-sodium-face-v18'}:
                RUN_SUFFIX = '20261011-v14'
                PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverOwnedSodium-v14-2026-10-11.zip',
                         'candidate': 'Aqualumen-DisplayWater-ReceiverOwnedSodium-v14-2026-10-11.zip'}
                PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-sodium-v13.jar'
                MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                        PHYS_PATH.name: '066273321a589201219fdffcad046d63594ca375ba681c34f00e49a5abf82967'}
                if args.packet == 'receiver-owned-sodium-columns-v15':
                    RUN_SUFFIX = '20261011-v15'
                    PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverOwnedSodiumColumns-v15-2026-10-11.zip',
                             'candidate': 'Aqualumen-DisplayWater-ReceiverOwnedSodiumColumns-v15-2026-10-11.zip'}
                    PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-sodium-v14.jar'
                    MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                            PHYS_PATH.name: 'bd8da15318cf064a86e01891a277fb4d5e8c34b513e4265c5894839b2cfefdc7'}
                if args.packet == 'receiver-owned-sodium-material-v16':
                    RUN_SUFFIX = '20261011-v16'
                    PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverOwnedSodiumMaterial-v16-2026-10-11.zip',
                             'candidate': 'Aqualumen-DisplayWater-ReceiverOwnedSodiumMaterial-v16-2026-10-11.zip'}
                    PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-sodium-v15.jar'
                    MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                            PHYS_PATH.name: '0fc0a5eda3ac349a6a60f07196734ae41baf368684d62930336ecabf5eacbb5a'}
                if args.packet == 'receiver-owned-sodium-diagnostic-v17':
                    RUN_SUFFIX = '20261011-v17'
                    PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverOwnedSodiumDiagnostic-v17-2026-10-11.zip',
                             'candidate': 'Aqualumen-DisplayWater-ReceiverOwnedSodiumDiagnostic-v17-2026-10-11.zip'}
                    PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-sodium-v16.jar'
                    MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                            PHYS_PATH.name: 'e288daa4a847f8132f4eecf8935357e5043c0077745d87cc642342a433fa00ec'}
                if args.packet == 'receiver-owned-sodium-face-v18':
                    RUN_SUFFIX = '20261011-v18'
                    PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverOwnedSodiumFace-v18-2026-10-11.zip',
                             'candidate': 'Aqualumen-DisplayWater-ReceiverOwnedSodiumFace-v18-2026-10-11.zip'}
                    PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-sodium-v17.jar'
                    MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                            PHYS_PATH.name: 'c6c036ee026666338be17b96a4911078ba2206699daf7e1df93a63ff796ac226'}
    if requested_packet in {'receiver-owned-encoder-v20', 'receiver-terrain-input-v21', 'receiver-source-point-v22', 'receiver-source-point-core-v23', 'receiver-source-point-compiled-v24', 'receiver-source-volume-v25', 'receiver-source-volume-bound-v26', 'receiver-source-updates-v27'}:
        OUT = OUT.parent / requested_packet
        OUT.mkdir(exist_ok=True)
        NATIVE_CHECK = OUT.parent / 'native-atlas-source-v19.log'
        RUN_SUFFIX = '20261011-v20'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverOwnedEncoder-v20-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-ReceiverOwnedEncoder-v20-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-owned-encoder-v21.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '3ece2fdf7d57c2e2348b96b826b7c7c1cdf8949b84197881935fb4f43b03008c'}
        if requested_packet == 'receiver-terrain-input-v21':
            RUN_SUFFIX = '20261011-v21'
            PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverTerrainInput-v21-2026-10-11.zip',
                     'candidate': 'Aqualumen-DisplayWater-ReceiverTerrainInput-v21-2026-10-11.zip'}
            PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-terrain-input-v22.jar'
            MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                    PHYS_PATH.name: '32ea9fec20ece074bff09bf514a0a19c1e832f1b0a8b74daeed8e53a39c4a263'}
        if requested_packet in {'receiver-source-point-v22', 'receiver-source-point-core-v23', 'receiver-source-point-compiled-v24', 'receiver-source-volume-v25', 'receiver-source-volume-bound-v26', 'receiver-source-updates-v27'}:
            RUN_SUFFIX = '20261011-v22'
            PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverSourcePoint-v22-2026-10-11.zip',
                     'candidate': 'Aqualumen-DisplayWater-ReceiverSourcePoint-v22-2026-10-11.zip'}
            PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-source-point-v25.jar'
            MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                    PHYS_PATH.name: '89205c7b790aba0d0e52c80d1b62826b30d9314bf883857614b75f66ce34172d'}
            if requested_packet == 'receiver-source-point-core-v23':
                RUN_SUFFIX = '20261011-v23'
                PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverSourcePointCore-v23-2026-10-11.zip',
                         'candidate': 'Aqualumen-DisplayWater-ReceiverSourcePointCore-v23-2026-10-11.zip'}
                PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-source-point-v26.jar'
                MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                        PHYS_PATH.name: 'e48dd4d99aede6ac0354fcfc4c75be1bef336e6cdeab27d2f54e1bd5bbcc7fdc'}
            if requested_packet == 'receiver-source-point-compiled-v24':
                RUN_SUFFIX = '20261011-v24'
                PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverSourcePointCompiled-v24-2026-10-11.zip',
                         'candidate': 'Aqualumen-DisplayWater-ReceiverSourcePointCompiled-v24-2026-10-11.zip'}
                PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-source-point-v27.jar'
                MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                        PHYS_PATH.name: '8561d08ea746e49d031b03b55a78131d28691a72045f963fad506de63ddd8501'}
            if requested_packet == 'receiver-source-volume-v25':
                RUN_SUFFIX = '20261011-v25'
                PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverSourceVolume-v25-2026-10-11.zip',
                         'candidate': 'Aqualumen-DisplayWater-ReceiverSourceVolume-v25-2026-10-11.zip'}
                PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-source-volume-v30.jar'
                MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                        PHYS_PATH.name: '055265de746322003d98ae1ada06a66ea9cb8d1697a8185440fedef27bd264a2'}
            if requested_packet == 'receiver-source-volume-bound-v26':
                RUN_SUFFIX = '20261011-v26'
                PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverSourceVolumeBound-v26-2026-10-11.zip',
                         'candidate': 'Aqualumen-DisplayWater-ReceiverSourceVolumeBound-v26-2026-10-11.zip'}
                PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-source-volume-bound-v32.jar'
                MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                        PHYS_PATH.name: '6a697d09b98a7bc1130cd42be7b3ecdf2efdc602d46c1df0bfe6fc63cadaf543'}
            if requested_packet == 'receiver-source-updates-v27':
                RUN_SUFFIX = '20261011-v27'
                SCENES = ['underwater-up-near', 'underwater-up-moving']
                PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverSourceUpdates-v27-2026-10-11.zip',
                         'candidate': 'Aqualumen-DisplayWater-ReceiverSourceUpdates-v27-2026-10-11.zip'}
                PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-source-updates-v34.jar'
                MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                        PHYS_PATH.name: '7ce78eec58fb4d52895d7a6aff193f0cf03af09cce44294309c7390a9de1fa16'}
    if requested_packet in {'receiver-partial-macro-v29','receiver-wide-batch-v30','receiver-wide-batch-v31','receiver-phase-cache-v32','receiver-interface-crest-v33','receiver-residual-normal-v34','receiver-outcome-v35','receiver-rejection-v36','receiver-live-runs-v42','receiver-stage-profile-v43'}:
        OUT = OUT.parent / requested_packet
        OUT.mkdir(exist_ok=True)
        NATIVE_CHECK = OUT.parent / 'native-displaced-macro-full-v29.log'
        CHECK_RECEIPT = '14 program pairs compiled and linked'
        RUN_SUFFIX = '20261011-v29'
        SCENES = ['underwater-up-near', 'underwater-up-moving']
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverPartialMacro-v29-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-ReceiverPartialMacro-v29-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-field-session-v39.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: 'bde6a0665b12b1f9afa05a7c4cedf6f70a6b6060994534ed326b73d0ef0e7be6'}
        if requested_packet in {'receiver-wide-batch-v30','receiver-wide-batch-v31','receiver-phase-cache-v32','receiver-interface-crest-v33','receiver-residual-normal-v34','receiver-outcome-v35','receiver-rejection-v36','receiver-live-runs-v42','receiver-stage-profile-v43'}:
            NATIVE_CHECK = OUT.parent / 'native-wide-batch-full-v30.log'
            RUN_SUFFIX = '20261011-v30'
            PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverWideBatch-v30-2026-10-11.zip',
                     'candidate': 'Aqualumen-DisplayWater-ReceiverWideBatch-v30-2026-10-11.zip'}
            PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-wide-session-v42.jar'
            MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                    PHYS_PATH.name: '0f89d0b3068cb9dc74f869997192b7668524fb031dec5cf74eb53fd125c0622f'}
            if requested_packet == 'receiver-wide-batch-v31':
                RUN_SUFFIX = '20261011-v31'
                PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverWideBatch-v31-2026-10-11.zip',
                         'candidate': 'Aqualumen-DisplayWater-ReceiverWideBatch-v31-2026-10-11.zip'}
                PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-wide-session-v43.jar'
                MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                        PHYS_PATH.name: '7009f2c637e8d7710a7e958859b40647e3ccfe6d4743ee74d85574436bae4747'}
            if requested_packet == 'receiver-phase-cache-v32':
                RUN_SUFFIX = '20261011-v32'
                PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverPhaseCache-v32-2026-10-11.zip',
                         'candidate': 'Aqualumen-DisplayWater-ReceiverPhaseCache-v32-2026-10-11.zip'}
                PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-receiver-phase-cache-v44.jar'
                MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                        PHYS_PATH.name: 'e86b72205abf59225184a64fcdaa401aa69651128f0f34830b5bc06b4a85f371'}
            if requested_packet in {'receiver-interface-crest-v33','receiver-residual-normal-v34','receiver-outcome-v35','receiver-rejection-v36','receiver-live-runs-v42','receiver-stage-profile-v43'}:
                NATIVE_CHECK = OUT.parent / 'native-interface-full-v33.log'
                RUN_SUFFIX = '20261011-v33'
                PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverInterfaceCrest-v33-2026-10-11.zip',
                         'candidate': 'Aqualumen-DisplayWater-ReceiverInterfaceCrest-v33-2026-10-11.zip'}
                PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-interface-crest-v45.jar'
                MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                        PHYS_PATH.name: '1e39c551105103fb531be8877d9a2148babf376fd7f6021cf797af24c04f4cef'}
                if requested_packet == 'receiver-residual-normal-v34':
                    NATIVE_CHECK = OUT.parent / 'native-residual-full-v34.log'
                    RUN_SUFFIX = '20261011-v34'
                    PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverResidualNormal-v34-2026-10-11.zip',
                             'candidate': 'Aqualumen-DisplayWater-ReceiverResidualNormal-v34-2026-10-11.zip'}
                if requested_packet == 'receiver-outcome-v35':
                    NATIVE_CHECK = OUT.parent / 'native-receiver-outcome-v35.log'
                    CHECK_RECEIPT = 'PASS compile/link only; no compute dispatch, draw, readback, regression or visual acceptance'
                    RUN_SUFFIX = '20261011-v35'
                    PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverOutcome-v35-2026-10-11.zip',
                             'candidate': 'Aqualumen-DisplayWater-ReceiverOutcome-v35-2026-10-11.zip'}
                if requested_packet == 'receiver-rejection-v36':
                    NATIVE_CHECK = OUT.parent / 'native-receiver-rejection-v36.log'
                    CHECK_RECEIPT = 'PASS compile/link only; no compute dispatch, draw, readback, regression or visual acceptance'
                    RUN_SUFFIX = '20261011-v36'
                    PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverRejection-v36-2026-10-11.zip',
                             'candidate': 'Aqualumen-DisplayWater-ReceiverRejection-v36-2026-10-11.zip'}
                if requested_packet == 'receiver-live-runs-v42':
                    NATIVE_CHECK = OUT.parent / 'native-live-run-full-v42.log'
                    CHECK_RECEIPT = '14 program pairs compiled and linked'
                    RUN_SUFFIX = '20261011-v42'
                    PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverLiveRuns-v42-2026-10-11.zip',
                             'candidate': 'Aqualumen-DisplayWater-ReceiverLiveRuns-v42-2026-10-11.zip'}
                    PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-live-run-field-v50.jar'
                    MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                            PHYS_PATH.name: '9760f625ac38bc89ac0bc42557be563c21b3475c7dde7226a89b262aa72d7a0e'}
                if requested_packet == 'receiver-stage-profile-v43':
                    NATIVE_CHECK = OUT.parent / 'native-live-run-full-v42.log'
                    CHECK_RECEIPT = '14 program pairs compiled and linked'
                    RUN_SUFFIX = '20261011-v43'
                    SAMPLE_SECONDS = 20
                    PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverStageProfile-v43-2026-10-11.zip',
                             'candidate': 'Aqualumen-DisplayWater-ReceiverStageProfile-v43-2026-10-11.zip'}
                    PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-run-stage-profile-v51.jar'
                    MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                            PHYS_PATH.name: 'a7056c83cf4bc081d755bcef0a3e8d0c16927e15bab5f186f95a50cf9e2a5303'}
    if lazy_solid_packet:
        OUT = OUT.parent / 'receiver-lazy-solid-v44'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v44'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverLazySolid-v44-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-ReceiverLazySolid-v44-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-lazy-solid-v52.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '4a3a3b9ae4dc404738f84b57db3272799b2eab6493a5075ded09746c3b80c3df'}
    if stack_profile_packet:
        OUT = OUT.parent / 'receiver-stack-profile-v45'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v45'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverStackProfile-v45-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-ReceiverStackProfile-v45-2026-10-11.zip'}
    if stack_profile_retry:
        OUT = OUT.parent / 'receiver-stack-profile-v46'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v46'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverStackProfile-v46-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-ReceiverStackProfile-v46-2026-10-11.zip'}
    if coordinate_hash_packet:
        OUT = OUT.parent / 'receiver-coordinate-hash-v47'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v47'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverCoordinateHash-v47-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-ReceiverCoordinateHash-v47-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-coordinate-hash-v53.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: 'ddf8326e8bb4f22b77374d4f6f3b65a3432c913feb7ac0e2fd95477cf7ce1701'}
    if typed_geometry_packet:
        OUT = OUT.parent / 'receiver-typed-geometry-v48'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v48'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverTypedGeometry-v48-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-ReceiverTypedGeometry-v48-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-typed-geometry-v54.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '6c3754e48036e4d7edfa08e35f257796bd39134c164761a203716dc36dfbd1a5'}
    if indexed_cache_packet:
        OUT = OUT.parent / 'receiver-indexed-cache-v49'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v49'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverIndexedCache-v49-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-ReceiverIndexedCache-v49-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-indexed-cache-v55.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '0e3a36113c29f54c3bbccb2ff6d7a22e900903f702e12731f205dff54bd4bba9'}
    if field_metadata_packet:
        OUT = OUT.parent / 'receiver-field-metadata-v50'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v50'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverFieldMetadata-v50-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-ReceiverFieldMetadata-v50-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-field-metadata-v56.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: 'caf8ff609a7ee90938e0010c1284cb73565816ba813c758d1dac94362419415d'}
    if wide_rejection_packet:
        OUT = OUT.parent / 'receiver-wide-rejection-v51'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v51'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverWideRejection-v51-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-ReceiverWideRejection-v51-2026-10-11.zip'}
        NATIVE_CHECK = OUT.parent / 'native-receiver-wide-rejection-v51.log'
        CHECK_RECEIPT = 'PASS compile/link only; no compute dispatch, draw, readback, regression or visual acceptance'
    if unknown_kinds_packet:
        OUT = OUT.parent / 'receiver-unknown-kinds-v52'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v52'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-ReceiverUnknownKinds-v52-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-ReceiverUnknownKinds-v52-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-unknown-kinds-receipt-v58.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '606e7c4d90d2924f08e01f443b6a1018409c36d6a6c1732cb9ad3201ff21b726'}
        NATIVE_CHECK = OUT.parent / 'native-unknown-kind-compile-v52.log'
        CHECK_RECEIPT = 'PASS compile/link only; no compute dispatch, draw, readback, regression or visual acceptance'
    if plant_model_packet:
        OUT = OUT.parent / 'receiver-plant-model-v53'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v53'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-PlantModelProbe-v53-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-PlantModelProbe-v53-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-plant-model-probe-v61.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '2c65638171e055d7ccd4810c457dec4f5c4b09553de0988c509445e0b4c194b8'}
        NATIVE_CHECK = OUT.parent / 'native-plant-model-compile-v53.log'
    if plant_packed_packet:
        OUT = OUT.parent / 'receiver-plant-packed-v54'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v54'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-PlantPackedProbe-v54-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-PlantPackedProbe-v54-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-plant-packed-probe-v62.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '123223c0c2beff6d2f96951c96bb2d04ff4c1c585219a02b8a06a3fd9b6a0250'}
        NATIVE_CHECK = OUT.parent / 'native-plant-packed-compile-v54.log'
    if plant_alpha_packet:
        OUT = OUT.parent / 'receiver-plant-alpha-v55'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v55'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-PlantAlphaProbe-v55-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-PlantAlphaProbe-v55-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-plant-alpha-probe-v64.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '1f5774d11c31eeb05b1e9d8ec2a9ef0fd5a16d0d71ddeaec7890860297a66350'}
        NATIVE_CHECK = OUT.parent / 'native-plant-alpha-compile-v55.log'
    if plant_atlas_metadata_packet:
        OUT = OUT.parent / 'receiver-plant-atlas-metadata-v56'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v56'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-PlantAtlasMetadata-v56-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-PlantAtlasMetadata-v56-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-plant-atlas-metadata-v65.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '3e1eb616be15bba0b0da5b52e3fe9f39b60d72ee211be77794b210589a363f7c'}
        NATIVE_CHECK = OUT.parent / 'native-plant-atlas-metadata-compile-v56.log'
    if plant_alpha_rgba_packet:
        OUT = OUT.parent / 'receiver-plant-alpha-rgba-v57'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v57'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-PlantAlphaRGBA-v57-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-PlantAlphaRGBA-v57-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-plant-alpha-rgba-v66.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: 'd6cb5de6bc18f520d8ac374bfb70d6b2f1202e8919ea393dd41dc6e595087b8c'}
        NATIVE_CHECK = OUT.parent / 'native-plant-alpha-rgba-compile-v57.log'
    if plant_live_gpu_packet:
        OUT = OUT.parent / 'receiver-plant-live-gpu-v59'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v59'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-PlantLiveGPU-v59-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-PlantLiveGPU-v59-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-plant-live-gpu-v68.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '18537b00fb3f264d2b9e67684f18b04f7c80db008f8678aa3b6e55cd0fb978ab'}
        NATIVE_CHECK = OUT.parent / 'native-plant-live-gpu-compile-v59.log'
    if plant_fluid_packet:
        OUT = OUT.parent / 'receiver-plant-fluid-v61'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v61'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-PlantFluidOwnership-v61-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-PlantFluidOwnership-v61-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-plant-fluid-ownership-v71.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: 'd856d7aa713c0b3df1aca8fcd7f6ad57166b75fb23dcfde68d7aae095b74a6a1'}
        NATIVE_CHECK = OUT.parent / 'native-plant-fluid-compile-v61.log'
    if plant_region_packet:
        OUT = OUT.parent / 'receiver-plant-region-v69'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v69'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-PlantRegion-v69-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-PlantRegion-v69-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-plant-region-runtime-v76.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '194e41a245d58ab70c4ff065e123e0177d715d98ad605b5e03ba6177f9b79dab'}
        NATIVE_CHECK = OUT.parent / 'native-plant-region-compile-v69.log'
        CHECK_RECEIPT = '14 program pairs compiled and linked'
    if natural_review_packet:
        OUT = OUT.parent / 'receiver-natural-review-v76'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v76'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-NaturalReview-v76-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-NaturalReview-v76-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-plant-draw-state-guard-v82.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '66145213584cfe601fb7dda3974395bfae468c7fd39da8f2851003ef6987c4e8'}
        SCENES = ['ocean-sun-day', 'ocean-sun-dusk', 'underwater-up-near', 'underwater-up-moving']
        SAMPLE_SECONDS = 10
        NATIVE_CHECK = OUT.parent / 'native-natural-review-compile-v76.log'
        CHECK_RECEIPT = 'PASS compile/link only; no compute dispatch, draw, readback, regression or visual acceptance'
    if natural_sun_packet:
        OUT = OUT.parent / 'receiver-natural-sun-v77'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v77'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-NaturalSun-v77-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-NaturalSun-v77-2026-10-11.zip'}
        BENCH_PATH = ROOT / 'build/aqualumen-benchmark-0.3.9-sun-views-v3.jar'
        MODS = {BENCH_PATH.name: '167a957c559e1c5415838d60f5cd84b91dfa1f16511015caa60dcb24675e89e3',
                PHYS_PATH.name: MODS[PHYS_PATH.name]}
    if reflection_normal_packet:
        REFLECTION_NORMAL_COMPARISON = True
        OUT = OUT.parent / 'underwater-normal-comparison-v80'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v80'
        SCENES = ['underwater-up-near', 'underwater-up-moving']
        PACKS = {'control': 'Aqualumen-UnderwaterNormal-Control-v80-2026-10-11.zip',
                 'candidate': 'Aqualumen-UnderwaterNormal-v80-2026-10-11.zip'}
        NATIVE_CHECK = OUT.parent / 'native-underwater-normal-compile-v80.log'
    if owner_profile_packet:
        OUT = OUT.parent / 'receiver-owner-profile-v81'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v81'
        SCENES = ['underwater-up-near', 'underwater-up-moving']
        PACKS = {'control': 'Aqualumen-ReceiverOwner-Control-v81-2026-10-11.zip',
                 'candidate': 'Aqualumen-ReceiverOwner-v81-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-allocation-free-owner-v83.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: 'a4c8cd36d356b87c790438855fae438854b202da6f67ffeec83c7c1b463062e6'}
        NATIVE_CHECK = OUT.parent / 'native-owner-profile-compile-v81.log'
    if owner_profile_retry:
        OUT = OUT.parent / 'receiver-owner-profile-v82'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v82'
        PACKS = {'control': 'Aqualumen-ReceiverOwner-Control-v82-2026-10-11.zip',
                 'candidate': 'Aqualumen-ReceiverOwner-v82-2026-10-11.zip'}
    if classification_packet:
        OUT = OUT.parent / 'receiver-classification-v83'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v83'
        PACKS = {'control': 'Aqualumen-ReceiverClassification-Control-v83-2026-10-11.zip',
                 'candidate': 'Aqualumen-ReceiverClassification-v83-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-classification-switch-v85.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '262851e98b495fc2ecfc672680c209e41ad8b9c987658cd38cdef9ab89244e1b'}
    if pack_predicate_packet:
        OUT = OUT.parent / 'receiver-pack-predicate-v84'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v84'
        PACKS = {'control': 'Aqualumen-ReceiverPackPredicate-Control-v84-2026-10-11.zip',
                 'candidate': 'Aqualumen-ReceiverPackPredicate-v84-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-pack-predicate-v86.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '8e81a80eb5e113279720862a919fd2e26293ff791f077f12586a99def0a46c91'}
    if plant_material_packet:
        OUT = OUT.parent / 'receiver-plant-material-v85'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v85'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-PlantMaterial-v85-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-PlantMaterial-v85-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-plant-material-gpu-v90.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '0ce8e28757d64ba3dbd69ce05fe2a54159d1d0c49a4af8ebf26aa94b40c9ec16'}
        NATIVE_CHECK = OUT.parent / 'native-plant-material-compile-v85.log'
        CHECK_RECEIPT = 'PASS compile/link only; no compute dispatch, draw, readback, regression or visual acceptance'
    if plant_material_region_packet:
        OUT = OUT.parent / 'receiver-plant-material-v86'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v86'
        PACKS = {'control': 'Aqualumen-DisplayWater-Control-PlantMaterial-v86-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-PlantMaterial-v86-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-material-region-gpu-v96.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '7539300e05e961a6befe51984cd5ae5afd77bde3af9ae401423681ffd62e05a0'}
        NATIVE_CHECK = OUT.parent / 'native-plant-material-compile-v86.log'
    if interface_packet:
        OUT = OUT.parent / 'underwater-interface-v87'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v87'
        PACKS = {'control': 'Aqualumen-InterfaceDiagnostic-Control-v87-2026-10-11.zip',
                 'candidate': 'Aqualumen-InterfaceDiagnostic-v87-2026-10-11.zip'}
        NATIVE_CHECK = OUT.parent / 'native-interface-compile-v87.log'
    if exit_direction_packet:
        OUT = OUT.parent / 'underwater-exit-direction-v88'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v88'
        PACKS = {'control': 'Aqualumen-ExitDirectionDiagnostic-Control-v88-2026-10-11.zip',
                 'candidate': 'Aqualumen-ExitDirectionDiagnostic-v88-2026-10-11.zip'}
        NATIVE_CHECK = OUT.parent / 'native-exit-direction-compile-v88.log'
    if raw_exit_packet:
        OUT = OUT.parent / 'underwater-raw-exit-v89'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v89'
        PACKS = {'control': 'Aqualumen-RawExitDirectionDiagnostic-Control-v89-2026-10-11.zip',
                 'candidate': 'Aqualumen-RawExitDirectionDiagnostic-v89-2026-10-11.zip'}
        NATIVE_CHECK = OUT.parent / 'native-raw-exit-direction-compile-v89.log'
    if raw_exit_retry:
        OUT = OUT.parent / 'underwater-raw-exit-v90'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v90'
        PACKS = {'control': 'Aqualumen-RawExitDirectionDiagnostic-Control-v90-2026-10-11.zip',
                 'candidate': 'Aqualumen-RawExitDirectionDiagnostic-v90-2026-10-11.zip'}
        NATIVE_CHECK = OUT.parent / 'native-raw-exit-direction-compile-v90.log'
    if coupled_normal_packet:
        OUT = OUT.parent / 'underwater-coupled-normal-v91'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v91'
        PACKS = {'control': 'Aqualumen-CoupledNormalDiagnostic-Control-v91-2026-10-11.zip',
                 'candidate': 'Aqualumen-CoupledNormalDiagnostic-v91-2026-10-11.zip'}
        NATIVE_CHECK = OUT.parent / 'native-coupled-normal-compile-v91.log'
    if coupled_beauty_packet:
        OUT = OUT.parent / 'underwater-coupled-beauty-v92'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v92'
        PACKS = {'control': 'Aqualumen-CoupledBeauty-Control-v92-2026-10-11.zip',
                 'candidate': 'Aqualumen-CoupledBeauty-v92-2026-10-11.zip'}
        NATIVE_CHECK = OUT.parent / 'native-coupled-beauty-compile-v92.log'
        INTERFACE_NORMAL_COMPARISON = True
    if raw_receiver_packet:
        OUT = OUT.parent / 'underwater-raw-receiver-v93'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v93'
        PACKS = {'control': 'Aqualumen-RawReceiverDiagnostic-Control-v93-2026-10-11.zip',
                 'candidate': 'Aqualumen-RawReceiverDiagnostic-v93-2026-10-11.zip'}
        NATIVE_CHECK = OUT.parent / 'native-raw-receiver-compile-v93.log'
        INTERFACE_NORMAL_COMPARISON = False
    if raw_rejection_packet:
        OUT = OUT.parent / 'underwater-raw-rejection-v94'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v94'
        PACKS = {'control': 'Aqualumen-RawRejectionDiagnostic-Control-v94-2026-10-11.zip',
                 'candidate': 'Aqualumen-RawRejectionDiagnostic-v94-2026-10-11.zip'}
        NATIVE_CHECK = OUT.parent / 'native-raw-rejection-compile-v94.log'
    if raw_unknown_packet:
        OUT = OUT.parent / 'underwater-raw-unknown-v95'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v95'
        PACKS = {'control': 'Aqualumen-RawUnknownKindsDiagnostic-Control-v95-2026-10-11.zip',
                 'candidate': 'Aqualumen-RawUnknownKindsDiagnostic-v95-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-raw-unknown-tags-v97.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '908d8227b10d66268969f64cf0e9bcdcfd4a28aea789296d8ca28d788bae7f9f'}
        NATIVE_CHECK = OUT.parent / 'native-raw-unknown-compile-v95.log'
    if plant_owner_bounds_packet:
        OUT = OUT.parent / 'receiver-plant-owner-bounds-v96'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v96'
        PACKS = {'control': 'Aqualumen-DisplayWater-PlantOwnerBounds-Control-v96-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-PlantOwnerBounds-v96-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-plant-owner-probe-v100.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: 'd3b07b3f5e28f0c7bc5346f44391166051143662e087313d24e49008854cd16c'}
        NATIVE_CHECK = OUT.parent / 'native-plant-owner-bounds-compile-v96.log'
    if plant_window_packet:
        OUT = OUT.parent / 'receiver-plant-window-v97'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v97'
        PACKS = {'control': 'Aqualumen-DisplayWater-PlantReceiverWindow-Control-v97-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-PlantReceiverWindow-v97-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-plant-receiver-window-v102.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '084ec18bacff6001a74889d944d009e67bcd86c6697c1b50945aec7a2d7150ce'}
        NATIVE_CHECK = OUT.parent / 'native-plant-window-compile-v97.log'
    if plant_tiled_packet:
        OUT = OUT.parent / 'receiver-plant-tiled-v98'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v98'
        PACKS = {'control': 'Aqualumen-DisplayWater-PlantTiledWindow-Control-v98-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-PlantTiledWindow-v98-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-plant-tiled-probe-v104.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: 'fd61eadfe2c89be28406ef013cc5c09a201d7938d7804c6891f81c3b847c0523'}
        NATIVE_CHECK = OUT.parent / 'native-plant-tiled-compile-v98.log'
    if plant_fluid_publication_packet:
        OUT = OUT.parent / 'receiver-plant-fluid-publication-v99'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v99'
        PACKS = {'control': 'Aqualumen-DisplayWater-PlantFluidPublication-Control-v99-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-PlantFluidPublication-v99-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-plant-fluid-probe-v106.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: 'c9346f973d45619bace996067cb8391c44a6fd81f198e8726091b5682ef3628c'}
        NATIVE_CHECK = OUT.parent / 'native-plant-fluid-publication-compile-v99.log'
    if plant_owner_halo_packet:
        OUT = OUT.parent / 'receiver-plant-owner-halo-v100'
        OUT.mkdir(exist_ok=True)
        RUN_SUFFIX = '20261011-v100'
        PACKS = {'control': 'Aqualumen-DisplayWater-PlantOwnerHalo-Control-v100-2026-10-11.zip',
                 'candidate': 'Aqualumen-DisplayWater-PlantOwnerHalo-v100-2026-10-11.zip'}
        PHYS_PATH = ROOT / 'build/aqualumen-physics-0.3.0-plant-owner-halo-probe-v110.jar'
        MODS = {BENCH_PATH.name: MODS[BENCH_PATH.name],
                PHYS_PATH.name: '450d104073f4fcaead4b2636da0d13f7f7dca06a2f744b493632c0a05c7936d9'}
        NATIVE_CHECK = OUT.parent / 'native-plant-owner-halo-compile-v100.log'
    if args.action in {'select', 'launch', 'start', 'profile-start', 'collect', 'collect-failed'}:
        globals()[args.action.replace('-', '_')](args.role)
    else:
        globals()[args.action]()
