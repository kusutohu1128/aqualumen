"""Exclusive real Iris resource/material query cycle. Never restore ordinary saves."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import uuid
import water_receiver_texture_lifecycle as base

ROOT, GAME = base.ROOT, base.GAME
OUT = ROOT / 'reports/2026-10-06-water-receiver-light'
JAR = 'aqualumen-receiver-light-probe-0.1.0-resources-v1.jar'
PROPERTY = 'aqualumen-receiver-light-probe.properties'
base.OUT, base.JAR, base.PROPERTY = OUT, JAR, PROPERTY


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(source.read_bytes())


def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)


def build():
    OUT.mkdir(exist_ok=False)
    contract = ROOT / 'reports/2026-10-06-water-receiver-triangle/input-contract.json'
    data = json.loads(contract.read_text())
    faces = data['faces']
    points = [p for p in data['samples'] if p['kind'] == 'saved-first-receiver']
    if len(faces) != 14 or len(points) != 16:
        raise ValueError('Qualified archived fixture scope changed')
    body = struct.pack('>II', 0x41514d31, len(faces))
    for face in faces:
        for st, words in zip(face['st'], face['words']):
            if len(words) != 5 or st not in ([0, 0], [1, 0], [1, 1], [0, 1]):
                raise ValueError('Original encoded full face rejected')
            body += struct.pack('>2d3I', *st, *words[2:5])
    body += struct.pack('>I', len(points))
    for point in points:
        body += struct.pack('>I2d', point['face'], point['s'], point['t'])
    fixture = OUT / 'material-queries.bin'
    with fixture.open('xb') as stream:
        stream.write(body)
    copy(contract, OUT / 'archived-triangle-input-contract.json')
    sources = [Path(__file__).resolve(), ROOT / 'tools/build-receiver-light-probe.sh',
               ROOT / 'physics-mod/dev/aqualumen/physics/ReceiverVertexShader.java',
               ROOT / 'physics-mod/dev/aqualumen/physics/ReceiverTriangle.java',
               *sorted((ROOT / 'tools/receiver-light-probe').rglob('*'))]
    hashes = {}
    folder = OUT / 'actual-build-v1'
    folder.mkdir(exist_ok=False)
    for source in sources:
        if source.is_file():
            name = source.relative_to(ROOT)
            copy(source, folder / 'source' / name)
            hashes[str(name)] = base.sha(source)
    run = subprocess.run(['rtk', 'proxy', 'bash', 'tools/build-receiver-light-probe.sh', 'build/' + JAR, str(fixture)],
                         cwd=ROOT, capture_output=True)
    with (folder / 'compile.log').open('xb') as stream:
        stream.write(run.stdout + run.stderr)
    if run.returncode:
        print((run.stdout + run.stderr).decode(), end='')
        raise ValueError('Actual build failed; retained frozen sources and log')
    if any(base.sha(ROOT / name) != digest for name, digest in hashes.items()):
        raise ValueError('Build sources changed')
    copy(ROOT / 'build' / JAR, folder / JAR)
    save('build-receipt.json', dict(jar=JAR, artifactSHA256=base.sha(ROOT / 'build' / JAR),
         sourceSHA256=hashes, sourceUnchangedDuringBuild=True, exitCode=0,
         archivedTriangleContractSHA256=base.sha(contract), queryFixtureSHA256=base.sha(fixture),
         nativeGLExecuted=False, actualRuntimeQualified=False, fullGoalAchieved=False))
    print('Built exclusive TEST resource/material observer', base.sha(ROOT / 'build' / JAR))


def baseline():
    base.closed()
    if 'All dimensions are saved' not in (GAME / 'logs/latest.log').read_text():
        raise ValueError('Clean ordinary save/exit required')
    if (OUT / 'SHA256SUMS').exists() or (GAME / 'config' / PROPERTY).exists() or any('probe' in p.name for p in (GAME / 'mods').glob('*.jar')):
        raise ValueError('No existing instrumentation or sealed packet')
    cache = Path(tempfile.mkdtemp(prefix='aqualumen-legacy-branch-host-receiver-light-', dir='/home/kusutohu/.cache'))
    for name in ('options.txt', 'config/iris.properties', 'config/aqualumen-benchmark.properties'):
        copy(GAME / name, cache / name)
    save('fresh-normal-baseline.json', base.original(cache))
    copy(GAME / 'logs/latest.log', OUT / 'normal-clean-save-exit.log')
    print('NEW ordinary post-save baseline', cache)


def install():
    base.closed()
    baseline = json.loads((OUT / 'fresh-normal-baseline.json').read_text())
    if base.original(Path(baseline['backup'])) != baseline:
        raise ValueError('Ordinary state changed before TEST install')
    receipt = json.loads((OUT / 'build-receipt.json').read_text())
    if receipt['jar'] != JAR or base.sha(ROOT / 'build' / JAR) != receipt['artifactSHA256']:
        raise ValueError('Built artifact changed')
    for name, digest in receipt['sourceSHA256'].items():
        if base.sha(ROOT / name) != digest:
            raise ValueError('Built source changed')
    marker = dict(line.split('=', 1) for line in (GAME / 'saves/AqualumenNaturalV2/aqualumen-world.properties').read_text().splitlines())
    if marker.get('world_id') != base.WORLD or marker.get('seed') != '308060' or marker.get('generator') != 'minecraft:noise/overworld':
        raise ValueError('Exact TEST identity rejected')
    if (GAME / 'mods' / JAR).exists() or (GAME / 'config' / PROPERTY).exists():
        raise ValueError('No overwrite')
    request = str(uuid.uuid4())
    body = '\n'.join(['schema=1', f'world_id={base.WORLD}', f'request_id={request}',
        f'pack_sha256={base.sha(GAME / "shaderpacks/Aqualumen-0.6.0.zip")}',
        f'query_fixture_sha256={receipt["queryFixtureSHA256"]}']) + '\n'
    copy(ROOT / 'build' / JAR, GAME / 'mods' / JAR)
    with (GAME / 'config' / PROPERTY).open('x') as stream:
        stream.write(body)
    with (OUT / 'request.properties').open('x') as stream:
        stream.write(body)
    save('install.json', dict(requestId=request, worldUUID=base.WORLD, probeSHA256=receipt['artifactSHA256'],
         shaderSourceChanged=False, normalPhysicsUnchanged=True, worldCommands=False, fullGoalAchieved=False))
    print('Installed V2-only read-only observer', request)


def collect():
    request = json.loads((OUT / 'install.json').read_text())['requestId']
    source = GAME / 'aqualumen-receiver-light-probe' / request
    target = OUT / 'actual-resources'
    target.mkdir(exist_ok=False)
    if source.is_symlink() or not source.is_dir():
        raise ValueError('Actual exclusive output absent')
    for path in sorted(source.iterdir()):
        if path.is_symlink() or not path.is_file():
            raise ValueError('Unexpected actual readback path')
        copy(path, target / path.name)
    copy(GAME / 'logs/latest.log', OUT / 'test-resource-runtime.log')
    data = json.loads((target / 'readback.json').read_text())
    if 'error' in data:
        raise ValueError('Actual observer rejected: ' + data['error'])
    if data['request_id'] != request or data['world_id'] != base.WORLD or not data['originalMultiDrawReturned']:
        raise ValueError('Actual resource/draw scope incomplete')
    print('Retained actual sampled resources and controlled GPU fetches; independent audit pending')


def main(action):
    if action in ('build', 'baseline', 'install', 'collect'):
        {'build': build, 'baseline': baseline, 'install': install, 'collect': collect}[action]()
        return
    base.HASH = json.loads((OUT / 'build-receipt.json').read_text())['artifactSHA256']
    if action in ('test', 'normal'):
        base.launch(action)
    elif action == 'restore':
        base.restore()
    else:
        raise ValueError('Declared lifecycle action required')


if __name__ == '__main__':
    import sys
    main(sys.argv[1])
