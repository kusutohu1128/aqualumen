"""Reversible land-only Lab comparison. Each command writes a new receipt."""
import argparse
import csv
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import uuid
from zipfile import ZipFile
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import water_paired_runtime as shared
from water_hit_depth_runtime import lab_java_processes

GAME = shared.GAME
REPORT = 'reports/2026-10-23-land-shadows'
WORLD = 'AqualumenNaturalV2'
WORLD_ID = 'b22dbccb-2970-41e6-847f-f183b1ec923d'
ORDINARY = 'Aqualumen-0.6.0.zip'
ORDINARY_SHA = '6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73'
BENCH = 'aqualumen-benchmark-0.3.9-projection-guards.jar'
BENCH_SHA = 'ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29'
NORMAL_MODS = {'aqualumen-physics-0.2.0.jar', 'iris-fabric-1.8.8+mc1.21.1.jar',
               'sodium-fabric-0.6.9+mc1.21.1.jar'}
SCENES = ['air-shadow-backlit', 'air-sunlit-front', 'air-backlit-open']
CONFIGS = shared.CONFIG
SENTINEL = 'config/aqualumen-benchmark.enabled'
SENTINEL_TEXT = b'Land shadow comparison in exact disposable V2 UUID only\n'
OPTIONS = dict(renderDistance='12', simulationDistance='6', maxFps='120',
               enableVsync='false', fullscreen='false', pauseOnLostFocus='false',
               overrideWidth='1600', overrideHeight='900')
LAUNCHER_TELEMETRY = {'lastLaunchTime', 'lastTimePlayed', 'totalTimePlayed'}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    require(path.is_file() and not path.is_symlink(), 'Missing or redirected file: ' + str(path))
    return digest(path.read_bytes())


def pairs(data, separator='='):
    result = {}
    for line in data.decode('utf-8').splitlines():
        if not line or line.startswith(('#', '[', '!')):
            continue
        require(separator in line, 'Unrecognized configuration line')
        key, value = line.split(separator, 1)
        require(key not in result, 'Duplicate configuration key: ' + key)
        result[key] = value
    return result


def replace_values(data, values, separator='='):
    original = pairs(data, separator)
    require(set(values) <= set(original), 'Expected configuration keys are missing')
    return ('\n'.join(line.split(separator, 1)[0] + separator + values[line.split(separator, 1)[0]]
                      if separator in line and line.split(separator, 1)[0] in values else line
                      for line in data.decode('utf-8').splitlines()) + '\n').encode()


def properties(values):
    return ''.join(str(key) + '=' + str(value) + '\n' for key, value in values.items()).encode()


def tree(folder):
    require(folder.is_dir() and not folder.is_symlink() and folder.resolve() == folder, 'Directory redirected')
    paths = list(folder.rglob('*'))
    require(not any(path.is_symlink() for path in paths), 'Symlinked tree input')
    return {path.relative_to(folder).as_posix(): sha(path) for path in paths if path.is_file()}


def nvidia(renderer):
    return 'NVIDIA GeForce RTX 3080 Ti' in renderer


def png_dimensions(data):
    require(data[:8] == b'\x89PNG\r\n\x1a\n', 'Invalid PNG signature')
    offset, image, payload, ended = 8, None, bytearray(), False
    while offset < len(data):
        require(offset + 12 <= len(data), 'Truncated PNG chunk')
        size = struct.unpack('>I', data[offset:offset + 4])[0]
        chunk = data[offset + 4:offset + 8]
        end = offset + 12 + size
        require(end <= len(data), 'Truncated PNG payload')
        body = data[offset + 8:end - 4]
        require(zlib.crc32(chunk + body) == struct.unpack('>I', data[end - 4:end])[0], 'PNG checksum differs')
        if image is None:
            require(chunk == b'IHDR' and size == 13, 'PNG header missing')
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', body)
            require(depth == 8 and color in (2, 6) and compression == filtering == interlace == 0,
                    'Unexpected Minecraft screenshot encoding')
            image = (width, height, 3 if color == 2 else 4)
            require((width, height) == (1600, 900), 'Scene PNG extent differs')
        elif chunk == b'IDAT':
            payload.extend(body)
        elif chunk == b'IEND':
            require(size == 0 and end == len(data), 'PNG trailing data')
            ended = True
        offset = end
    require(ended and image is not None and payload, 'Incomplete PNG image')
    width, height, channels = image
    raw = zlib.decompress(payload)
    stride = width * channels + 1
    require(len(raw) == height * stride and all(raw[index * stride] <= 4 for index in range(height)),
            'Invalid PNG image rows')
    return [width, height]


def evidence_ref(root, value):
    require(isinstance(value, dict) and set(value) == {'path', 'sha256'}, 'Malformed evidence reference')
    relative = Path(value['path'])
    require('..' not in relative.parts, 'Evidence path escapes repository')
    path = relative if relative.is_absolute() else root / relative
    require(path.resolve() == path and path.is_relative_to(root.resolve()), 'Evidence path escapes repository')
    require(sha(path) == value['sha256'], 'Evidence changed')
    return path


def qualify(root, pack, qualification):
    proof = json.loads(qualification.read_text())
    require(proof.get('schema') == 'land-shadow-qualification-v1' and proof.get('packSHA256') == sha(pack),
            'Qualification does not bind candidate archive')
    require(set(proof.get('evidence', {})) == {'native', 'compile', 'motion'}, 'Qualification evidence roles differ')
    receipts = {role: json.loads(evidence_ref(root, ref).read_text()) for role, ref in proof['evidence'].items()}
    def verify_refs(value):
        if isinstance(value, dict):
            if 'path' in value and 'sha256' in value:
                evidence_ref(root, value)
            else:
                for item in value.values():
                    verify_refs(item)
        elif isinstance(value, list):
            for item in value:
                verify_refs(item)
    for value in (proof, *receipts.values()):
        verify_refs(value)
    native = receipts['native']
    require(native.get('schema') == 'aqualumen-land-shadow-native-v1' and native.get('algorithm') == 'land'
            and native.get('candidateQualified') is True and native.get('observedExit') == 0
            and native.get('positiveControlsPassed') is True and nvidia(native.get('renderer', '')),
            'Candidate NVIDIA native qualification missing')
    with ZipFile(pack) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'Duplicate candidate payload')
        shaders = {name: digest(archive.read(name)) for name in names if name.startswith('shaders/') and not name.endswith('/')}
    require(shaders and all(native.get('sourcePins', {}).get(name) == value for name, value in shaders.items()),
            'Native shader inputs do not match archive')
    for role in ('compile', 'motion'):
        receipt = receipts[role]
        require(receipt.get('packSHA256') == proof['packSHA256'] and receipt.get('exitCode') == 0
                and nvidia(receipt.get('renderer', '')), 'Candidate ' + role + ' qualification missing')
        if role == 'compile':
            evidence_ref(root, receipt['stdout'])
        else:
            require(receipt.get('passed') is True, 'Motion targets did not pass')
        for entry in receipt.get('evidence', []):
            evidence_ref(root, entry)
    for entry in proof.get('sourceEvidence', []):
        evidence_ref(root, entry)
    return proof


def validate_run(source, role, run_id):
    for path in source.rglob('*'):
        require(not path.is_symlink(), 'Redirected run artifact')
    manifest = json.loads((source / 'run.json').read_text())
    expected = dict(world_id=WORLD_ID, pack_name=role['pack'], pack_sha256=role['sha256'], shader_active=True,
                    shader_fallback=False, resolution=[1600, 900], framebuffer_resolution=[1600, 900])
    require(all(manifest.get(key) == value for key, value in expected.items()), 'Run shader/world identity differs')
    require(manifest.get('run_id') == run_id and manifest.get('scenarios') == SCENES
            and nvidia(manifest.get('gl_renderer', '')) and manifest.get('warmup_seconds') == 5
            and manifest.get('sample_seconds') == 5,
            'Run renderer/scenes/sampling differs')
    if 'native_motion_capture_active' in manifest:
        require(manifest['native_motion_capture_active'] is False, 'Motion capture is not a static scene observation')
    else:
        require(manifest.get('mods', {}).get('aqualumen_benchmark') == '0.3.9'
                and manifest.get('frame_method') == 'System.nanoTime render-tail intervals; one start boundary discarded; setup/screenshots outside sample'
                and not any(path.name.startswith('native-motion-') for path in source.iterdir()),
                'Unknown capture protocol without a motion-mode witness')
    complete = json.loads((source / 'complete.json').read_text())
    require(complete.get('run_id') == run_id and complete.get('status') == 'complete'
            and complete.get('scenarios') == SCENES and complete.get('fixture_cleanup_complete') is True,
            'Run did not finish fixture cleanup')
    counts = {}
    for scene in SCENES:
        sample = json.loads((source / (scene + '.json')).read_text())
        require(all(sample.get(key) == value for key, value in expected.items()) and sample.get('scenario') == scene
                and sample.get('run_id') == run_id and isinstance(sample.get('frames'), int) and sample['frames'] >= 10
                and sample.get('camera_first_person') is True and sample.get('camera_eye_match') is True,
                'Scene activation/camera/frame identity differs')
        require(sample.get('opaque_fixture', {}).get('camera_eye_match') is True, 'Air fixture camera witness missing')
        with (source / (scene + '.csv')).open() as stream:
            rows = list(csv.DictReader(stream))
        require(len(rows) == sample['frames'] and all(int(row['ns']) > 0 for row in rows), 'Scene raw frame count differs')
        data = (source / (scene + '.png')).read_bytes()
        png_dimensions(data)
        counts[scene] = sample['frames']
    return dict(runID=run_id, sceneFrameCounts=counts, renderer=manifest['gl_renderer'],
                shaderActive=True, shaderFallback=False, actualMinecraft=True,
                visualAccepted=False, performanceAcceptance=False)


@dataclass(frozen=True)
class LandShadowRuntime:
    out: Path
    game: Path = GAME
    root: Path = ROOT
    backup_parent: Path = Path.home() / '.cache'

    def save(self, name, data):
        with (self.out / name).open('x') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write('\n')

    def load(self, name):
        path = self.out / name
        sha(path)
        return json.loads(path.read_text())

    def stopped(self):
        require(not lab_java_processes(self.game), 'Owned Lab Java is live; runtime files stay unchanged')

    def paths(self):
        require(self.game == shared.GAME, 'Only the configured Lab is accepted')
        shared.owned_paths()
        shared.world_marker()
        require(self.out.resolve() == self.out and self.out.is_relative_to(self.root / REPORT), 'Evidence output redirected')

    def normal_save(self):
        return shared.prior.ordinary_tree()

    def config_tree(self):
        stages = {'.' + Path(name).name + '.land-20261023.pending' for name in CONFIGS if Path(name).parent == Path('config')}
        return {name: value for name, value in tree(self.game / 'config').items()
                if 'config/' + name not in CONFIGS and 'config/' + name != SENTINEL
                and name != 'aqualumen-physics-status.json' and name not in stages}

    def controls(self):
        return [path for path in (self.game / 'config').iterdir()
                if path.name.startswith('aqualumen-') and (path.name.endswith('.enabled')
                or 'observe' in path.name and path.suffix == '.properties')]

    def no_requests(self):
        for name in ('request.properties', 'opaque-fixture-journal.json'):
            require(not (self.game / 'aqualumen-benchmark' / name).exists(), 'Pending client request or fixture journal')

    def baseline(self):
        self.paths()
        data = self.load('baseline.json')
        require(data['game'] == str(self.game) and data['schema'] == 'land-shadow-runtime-v1', 'Runtime baseline identity differs')
        backup = Path(data['backup'])
        require(backup.resolve() == backup and not backup.is_symlink() and backup.is_dir(), 'Backup redirected')
        for name, value in data['config'].items():
            require(sha(backup / name) == value, 'Backup config changed')
        require(sha(backup / 'instance.cfg') == data['instanceSHA256'], 'Backup instance changed')
        return data

    def expected(self, data, role):
        target = data['roles'][role]
        backup = Path(data['backup'])
        return {'options.txt': replace_values((backup / 'options.txt').read_bytes(), OPTIONS, ':'),
                'config/iris.properties': replace_values((backup / 'config/iris.properties').read_bytes(), {'shaderPack': target['pack']}),
                'config/aqualumen-benchmark.properties': properties(dict(schema='2', world=WORLD, world_id=WORLD_ID,
                    expected_pack=target['pack'], expected_pack_sha256=target['sha256'], width='1600', height='900',
                    render_chunks='12', simulation_chunks='6', capture_motion='false'))}

    def stable(self, data):
        require(self.normal_save() == data['ordinarySave'], 'Ordinary save changed; never roll it back')
        require(self.config_tree() == data['unmanagedConfig'], 'Unmanaged config changed')
        backup = Path(data['backup'])
        variants = [{name: (backup / name).read_bytes() for name in CONFIGS},
                    self.expected(data, 'ordinary'), self.expected(data, 'candidate')]
        for name in CONFIGS:
            path = self.game / name
            staged = path.with_name('.' + path.name + '.land-20261023.pending')
            if staged.exists():
                require(any(sha(staged) == digest(item[name]) for item in variants), 'Owned staged configuration differs')
        instance_stage = self.game.parent / '.instance.cfg.land-20261023.pending'
        if instance_stage.exists():
            require(sha(instance_stage) == data['instanceSHA256'], 'Owned staged instance differs')
        for folder, allowed in (('mods', data['mods']), ('shaderpacks', data['shaderpacks'])):
            current = tree(self.game / folder)
            additions = {BENCH: BENCH_SHA} if folder == 'mods' else {data['roles']['candidate']['pack']: data['roles']['candidate']['sha256']}
            additions |= {shared.staging_path(self.game / folder / name).name: value for name, value in additions.copy().items()}
            for name, value in current.items():
                require((allowed | additions).get(name) == value, 'Unmanaged runtime artifact changed: ' + folder + '/' + name)
            require(all(current.get(name) == value for name, value in allowed.items()), 'Baseline runtime artifact missing')
        original = pairs((Path(data['backup']) / 'instance.cfg').read_bytes())
        current = pairs((self.game.parent / 'instance.cfg').read_bytes())
        require({k: v for k, v in current.items() if k not in LAUNCHER_TELEMETRY}
                == {k: v for k, v in original.items() if k not in LAUNCHER_TELEMETRY}, 'Unmanaged instance settings changed')
        controls = self.controls()
        require(all(path == self.game / SENTINEL and not path.is_symlink() and path.read_bytes() == SENTINEL_TEXT
                    for path in controls), 'Unowned TEST control appeared')

    def config_owned(self, data):
        backup = Path(data['backup'])
        variants = [{name: (backup / name).read_bytes() for name in CONFIGS},
                    self.expected(data, 'ordinary'), self.expected(data, 'candidate')]
        for name in CONFIGS:
            current = (self.game / name).read_bytes()
            separator = ':' if name == 'options.txt' else '='
            require(any(pairs(current, separator) == pairs(item[name], separator) for item in variants),
                    'Unmanaged setting changed: ' + name)

    def replace(self, path, content):
        staged = path.with_name('.' + path.name + '.land-20261023.pending')
        require(not staged.exists() and not staged.is_symlink(), 'Prior staged configuration exists')
        with staged.open('xb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staged, path)

    def setup(self, pack, qualification):
        self.stopped()
        self.paths()
        require(not self.out.exists(), 'Existing runtime Evidence must not be overwritten')
        require('Stopping!' in (self.game / 'logs/latest.log').read_text(), 'Clean prior client exit is unproven')
        require(set(path.name for path in (self.game / 'mods').glob('*.jar')) == NORMAL_MODS, 'Not the ordinary three-Mod baseline')
        require(sha(self.game / 'shaderpacks' / ORDINARY) == ORDINARY_SHA
                and sha(self.root / REPORT / 'ordinary-0.6.zip') == ORDINARY_SHA, 'Ordinary archive identity differs')
        iris = pairs((self.game / 'config/iris.properties').read_bytes())
        require(iris.get('shaderPack') == ORDINARY and iris.get('enableShaders') == 'true', 'Normal ordinary pack is not selected')
        require(not self.controls(), 'Prior TEST controls are active')
        self.no_requests()
        require(pack.name != ORDINARY and pack.suffix == '.zip' and Path(pack.name).name == pack.name, 'Unsafe candidate archive name')
        require(not (self.game / 'shaderpacks' / (pack.name + '.txt')).exists(), 'Candidate pack settings already exist')
        require(sha(self.root / 'build' / BENCH) == BENCH_SHA, 'Pinned benchmark changed')
        proof = qualify(self.root, pack, qualification)
        for target in (self.game / 'mods' / BENCH, self.game / 'shaderpacks' / pack.name):
            require(not target.exists() and not target.is_symlink() and not shared.staging_path(target).exists(), 'TEST install target already exists')
        for name in CONFIGS:
            path = self.game / name
            require(not path.with_name('.' + path.name + '.land-20261023.pending').exists(), 'Prior staged configuration exists')
        backup = Path(tempfile.mkdtemp(prefix='aqualumen-land-shadow-', dir=self.backup_parent))
        backup.chmod(0o700)
        config = {name: sha(self.game / name) for name in CONFIGS}
        for name in CONFIGS:
            destination = backup / name
            destination.parent.mkdir(exist_ok=True, parents=True)
            shutil.copy2(self.game / name, destination)
            require(sha(destination) == config[name], 'Backup copy changed')
        shutil.copy2(self.game.parent / 'instance.cfg', backup / 'instance.cfg')
        data = dict(schema='land-shadow-runtime-v1', game=str(self.game), backup=str(backup),
                    runtimeToolSHA256=sha(Path(__file__)), config=config,
                    instanceSHA256=sha(self.game.parent / 'instance.cfg'), mods=tree(self.game / 'mods'),
                    shaderpacks=tree(self.game / 'shaderpacks'), unmanagedConfig=self.config_tree(),
                    ordinarySave=self.normal_save(), roles=dict(ordinary=dict(pack=ORDINARY, sha256=ORDINARY_SHA),
                        candidate=dict(pack=pack.name, sha256=sha(pack))), qualificationSHA256=sha(qualification),
                    qualification=proof, nonce=uuid.uuid4().hex[:12])
        self.expected(data, 'ordinary')
        self.expected(data, 'candidate')
        self.out.mkdir()
        self.save('baseline.json', data)
        self.stopped()
        self.stable(data)
        shared.install_new(self.root / 'build' / BENCH, self.game / 'mods' / BENCH, BENCH_SHA)
        shared.install_new(pack, self.game / 'shaderpacks' / pack.name, data['roles']['candidate']['sha256'])
        self.save('prepared.json', dict(benchmarkSHA256=BENCH_SHA, candidateSHA256=data['roles']['candidate']['sha256'], configsUntouched=True))

    def selected(self, role):
        data = self.baseline()
        self.stable(data)
        require(not (self.out / 'restored.json').exists(), 'Runtime already restored')
        require(sha(self.game / 'mods' / BENCH) == BENCH_SHA, 'Benchmark is not installed')
        selected = self.load(role + '-selected.json')
        require(selected['role'] == role and selected['pack'] == data['roles'][role]['pack'], 'Selected role receipt differs')
        for name, content in self.expected(data, role).items():
            separator = ':' if name == 'options.txt' else '='
            require(pairs((self.game / name).read_bytes(), separator) == pairs(content, separator), 'Selected TEST settings differ')
        require((self.game / SENTINEL).read_bytes() == SENTINEL_TEXT, 'TEST opt-in differs')
        return data

    def select(self, role):
        self.stopped()
        self.no_requests()
        data = self.baseline()
        self.stable(data)
        self.config_owned(data)
        self.load('prepared.json')
        require(not (self.out / (role + '-selected.json')).exists(), 'Role selection already recorded')
        if role == 'candidate':
            self.load('ordinary-collected.json')
            self.load('ordinary-launcher-exit.json')
        else:
            require(not (self.out / 'candidate-selected.json').exists(), 'Ordinary role cannot follow candidate')
        for name, content in self.expected(data, role).items():
            self.replace(self.game / name, content)
        sentinel = self.game / SENTINEL
        if not sentinel.exists():
            with sentinel.open('xb') as stream:
                stream.write(SENTINEL_TEXT)
        self.save(role + '-selected.json', dict(role=role, **data['roles'][role]))

    def launch(self, role):
        self.stopped()
        data = self.selected(role)
        self.no_requests()
        previous = (self.game / 'logs/latest.log').read_bytes()
        private = Path(data['backup']) / (role + '-launcher-private.log')
        descriptor = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as output:
            self.save(role + '-launcher-start.json', dict(role=role, world_id=WORLD_ID, **data['roles'][role],
                      previousLog=dict(bytes=len(previous), sha256=digest(previous))))
            result = subprocess.run(['flatpak', 'run', '--command=prismrun', 'org.prismlauncher.PrismLauncher',
                '--launch', 'Aqualumen Lab', '--world', WORLD], env=dict(os.environ, DISPLAY=':1',
                XDG_RUNTIME_DIR='/run/user/1000', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus'),
                stdout=output, stderr=subprocess.STDOUT)
        self.save(role + '-launcher-exit.json', dict(exitCode=result.returncode))

    def start(self, role):
        require(len(lab_java_processes(self.game)) == 1, 'Exactly one owned Lab Java is required')
        data = self.selected(role)
        self.no_requests()
        launch = self.load(role + '-launcher-start.json')
        require(not (self.out / (role + '-launcher-exit.json')).exists(), 'Owned launcher already exited')
        log = (self.game / 'logs/latest.log').read_bytes()
        shared.prior.require_current_pipeline(log, launch['previousLog'])
        text = log.decode('utf-8', errors='replace')
        require('Using shaderpack: ' + data['roles'][role]['pack'] in text and 'NVIDIA GeForce RTX 3080 Ti' in text,
                'Fresh exact pack/NVIDIA pipeline not observed')
        require(not any(item in text for item in ('Shader compilation failed', 'Failed to create shader', 'Falling back to')),
                'Iris failure/fallback observed')
        run_id = 'land-shadow-' + role + '-' + data['nonce']
        result = subprocess.run([sys.executable, str(self.root / 'tools/benchmark-control.py'), '--game', str(self.game),
            'start', '--run-id', run_id, '--scenes', *SCENES, '--warmup', '5', '--sample', '5', '--auto-quit'],
            cwd=self.root, check=True, capture_output=True, text=True)
        request = json.loads(result.stdout)
        require(request.get('run_id') == run_id and request.get('action') == 'start'
                and request.get('world_id') == WORLD_ID and request.get('auto_quit') == 'true', 'Request identity differs')
        self.save(role + '-start-request.json', request)

    def collect(self, role):
        self.stopped()
        self.no_requests()
        data = self.selected(role)
        require(self.load(role + '-launcher-exit.json')['exitCode'] == 0, 'Owned launcher did not exit successfully')
        request = self.load(role + '-start-request.json')
        run_id = request['run_id']
        status = json.loads((self.game / 'aqualumen-benchmark/status.json').read_text())
        require(status.get('run_id') == run_id and status.get('request_id') == request['request_id']
                and status.get('state') in {'complete', 'quitting'}, 'Current benchmark acknowledgement differs')
        source = self.game / 'aqualumen-benchmark/runs' / run_id
        require(source.is_dir() and not source.is_symlink(), 'Missing owned run')
        observation = validate_run(source, data['roles'][role], run_id)
        target = self.out / (role + '-run')
        require(not target.exists(), 'Existing run Evidence must not be overwritten')
        shutil.copytree(source, target)
        require(tree(source) == tree(target), 'Archived run copy differs')
        self.save(role + '-collected.json', observation | dict(files=tree(target), ordinarySaveUnchanged=True))

    def restore(self):
        self.stopped()
        self.no_requests()
        data = self.baseline()
        self.stable(data)
        self.config_owned(data)
        backup = Path(data['backup'])
        for role in data['roles']:
            if (self.out / (role + '-launcher-start.json')).exists():
                self.load(role + '-launcher-exit.json')
        require(not (self.out / 'restored.json').exists(), 'Restoration already recorded')
        recover = backup / 'test-recovery'
        require(not recover.is_symlink() and (not recover.exists() or recover.is_dir()), 'Recovery directory redirected')
        planned = []
        for target, value in ((self.game / 'mods' / BENCH, BENCH_SHA),
                              (self.game / 'shaderpacks' / data['roles']['candidate']['pack'], data['roles']['candidate']['sha256'])):
            staged = shared.staging_path(target)
            if staged.exists():
                require(sha(staged) == value, 'Partial staged install differs')
                planned.append(staged)
        variants = [{name: (backup / name).read_bytes() for name in CONFIGS},
                    *[self.expected(data, role) for role in data['roles']]]
        for name in CONFIGS:
            path = self.game / name
            staged = path.with_name('.' + path.name + '.land-20261023.pending')
            if staged.exists():
                require(any(sha(staged) == digest(item[name]) for item in variants), 'Partial staged config differs')
                planned.append(staged)
        instance_staged = (self.game.parent / 'instance.cfg').with_name('.instance.cfg.land-20261023.pending')
        if instance_staged.exists():
            require(sha(instance_staged) == data['instanceSHA256'], 'Partial staged instance differs')
            planned.append(instance_staged)
        recover.mkdir(mode=0o700, exist_ok=True)
        for name in CONFIGS:
            destination = recover / name
            destination.parent.mkdir(exist_ok=True, parents=True)
            if not destination.exists():
                shutil.copy2(self.game / name, destination)
        if not (recover / 'instance.cfg').exists():
            shutil.copy2(self.game.parent / 'instance.cfg', recover / 'instance.cfg')
        benchmark = self.game / 'mods' / BENCH
        if benchmark.exists():
            require(sha(benchmark) == BENCH_SHA, 'Owned benchmark changed')
            require(not (recover / BENCH).exists(), 'Benchmark recovery destination exists')
            shutil.move(benchmark, recover / BENCH)
        sentinel = self.game / SENTINEL
        if sentinel.exists():
            require(sentinel.read_bytes() == SENTINEL_TEXT, 'Owned opt-in changed')
            require(not (recover / sentinel.name).exists(), 'Control recovery destination exists')
            shutil.move(sentinel, recover / sentinel.name)
        for path in planned:
            require(not (recover / path.name).exists(), 'Staged recovery destination exists')
            shutil.move(path, recover / path.name)
        for name in CONFIGS:
            self.replace(self.game / name, (backup / name).read_bytes())
        self.replace(self.game.parent / 'instance.cfg', (backup / 'instance.cfg').read_bytes())
        checks = dict(normalConfigExact=all(sha(self.game / name) == value for name, value in data['config'].items()),
                      normalModsExact=tree(self.game / 'mods') == data['mods'],
                      instanceExact=sha(self.game.parent / 'instance.cfg') == data['instanceSHA256'],
                      ordinarySaveExact=self.normal_save() == data['ordinarySave'], ordinarySaveRestored=False,
                      benchmarkDisabled=not (self.game / SENTINEL).exists(), normalPack=ORDINARY, normalPhysics='0.2.0',
                      previewRetainedInactive=(self.game / 'shaderpacks' / data['roles']['candidate']['pack']).exists(),
                      recoveryDirectory=str(recover))
        require(all(checks[key] for key in ('normalConfigExact', 'normalModsExact', 'instanceExact', 'ordinarySaveExact', 'benchmarkDisabled')),
                'Normal restoration differs; recovery retained')
        self.save('restored.json', checks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('setup', 'select', 'launch', 'start', 'collect', 'restore'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--role', choices=('ordinary', 'candidate'))
    parser.add_argument('--pack', type=Path)
    parser.add_argument('--qualification', type=Path)
    args = parser.parse_args()
    runtime = LandShadowRuntime(args.out.absolute())
    if args.action == 'setup':
        require(args.pack is not None and args.qualification is not None, 'setup needs --pack and --qualification')
        runtime.setup(args.pack.absolute(), args.qualification.absolute())
    elif args.action == 'restore':
        runtime.restore()
    else:
        require(args.role is not None, 'Role command needs --role')
        getattr(runtime, args.action)(args.role)


if __name__ == '__main__':
    main()
