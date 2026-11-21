import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)


def execute(command, directory, label, environment=None):
    print(label, flush=True)
    result = subprocess.run(['rtk', 'proxy', *map(str, command)], capture_output=True,
                            text=True, env=environment, timeout=240)
    for suffix, value in (('stdout', result.stdout), ('stderr', result.stderr)):
        with (directory / (label + '.' + suffix)).open('x') as stream:
            stream.write(value)
    receipt = dict(command=list(map(str, command)), exitCode=result.returncode,
                   stdoutSHA256=sha(directory / (label + '.stdout')),
                   stderrSHA256=sha(directory / (label + '.stderr')))
    save(directory / (label + '-receipt.json'), receipt)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--shader-root', type=Path, required=True)
    parser.add_argument('--algorithm', choices=('legacy', 'land'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--expected-exit', type=int, choices=(0, 2), default=0)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = args.shader_root.resolve(strict=True)
    out = args.out.absolute()
    out.mkdir(exist_ok=False)
    receipt = dict(schema='aqualumen-land-shadow-native-v1', utc=datetime.now(timezone.utc).isoformat(),
                   label=args.label, algorithm=args.algorithm, shaderRoot=str(source),
                   expectedExit=args.expected_exit, completedExpectedObservation=False,
                   physicalTargetsPassed=False, actualMinecraft=False, visualAccepted=False,
                   performanceMeasured=False, sourcePins={})
    try:
        native = out / 'land_shadow_native.cpp'
        shutil.copyfile(root / 'tools/land_shadow_native.cpp', native)
        shader = out / 'shaders'
        shutil.copytree(source, shader)
        receipt['runnerSHA256'] = sha(Path(__file__))
        receipt['sourcePins'] = {path.relative_to(out).as_posix(): sha(path)
                                 for path in sorted(out.rglob('*')) if path.is_file()}
        binary = out / 'land-shadow-native'
        build = execute(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', native,
                         '-o', binary, '-lepoxy', '-lEGL'], out, 'build')
        if build.returncode:
            raise RuntimeError('Native compilation failed, not an expected physical red')
        receipt['binarySHA256'] = sha(binary)
        cpu = execute([binary, '--cpu-self-test'], out, 'cpu-self-test')
        if cpu.returncode:
            raise RuntimeError('CPU fixture checks failed')
        environment = dict(os.environ, __EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/10_nvidia.json')
        result = execute([binary, shader, args.algorithm, out / 'capture'], out, 'native', environment)
        receipt['observedExit'] = result.returncode
        if result.returncode != args.expected_exit:
            raise RuntimeError('Unexpected native exit; preserve evidence rather than calling it expected red')
        data_path = out / 'capture/RESULT.json'
        data = json.loads(data_path.read_text())
        if not data['positiveControlsPassed'] or 'NVIDIA GeForce RTX 3080 Ti' not in data['renderer']:
            raise RuntimeError('Invalid fixture or unintended GL renderer')
        if args.algorithm == 'legacy' and not data['legacyContactLeakReproduced']:
            raise RuntimeError('Legacy contact leak was not reproduced')
        receipt.update(resultSHA256=sha(data_path), renderer=data['renderer'], depthBits=data['depthBits'],
                       positiveControlsPassed=data['positiveControlsPassed'],
                       legacyContactLeakReproduced=data['legacyContactLeakReproduced'],
                       physicalTargetsPassed=data['allPhysicalTargetsPassed'],
                       completedExpectedObservation=True)
        receipt['candidateQualified'] = args.algorithm == 'land' and result.returncode == 0 and data['allPhysicalTargetsPassed']
    except Exception as error:
        receipt['failure'] = str(error)
        raise
    finally:
        save(out / 'receipt.json', receipt)
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
