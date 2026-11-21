"""Freeze each exclusive CPU API/audit increment; never runs GL or Minecraft."""
import json
from pathlib import Path
import subprocess
import sys
from water_receiver_sun_audit import ROOT, sha

OUT = ROOT / 'reports/2026-10-06-water-receiver-draw'

def main(label):
    if label not in ('decode-red1', 'decode-green1', 'decode-red2', 'decode-green2',
                     'decode-red3', 'decode-green3', 'decode-final',
                     'audit-red1', 'audit-green1', 'audit-final') or (OUT / 'SHA256SUMS').exists():
        raise ValueError('Declared new increment in unsealed packet required')
    target = OUT / label
    target.mkdir(exist_ok=False)
    if label.startswith('decode'):
        names = ['physics-mod/dev/aqualumen/physics/ReceiverVertexShader.java',
                 'physics-mod/test/dev/aqualumen/physics/ReceiverVertexShaderTest.java',
                 'tools/test-receiver-vertex-shader.sh']
        command = ['bash', 'tools/test-receiver-vertex-shader.sh']
    else:
        names = ['tools/water_receiver_draw_audit.py', 'tools/test_water_receiver_draw_audit.py']
        command = ['python3', 'tools/test_water_receiver_draw_audit.py']
    names.append('tools/water_receiver_draw_record.py')
    hashes = {}
    for name in names:
        copy = target / 'source' / name
        copy.parent.mkdir(parents=True, exist_ok=True)
        with copy.open('xb') as stream: stream.write((ROOT / name).read_bytes())
        hashes[name] = sha(copy)
    run = subprocess.run(['rtk', 'proxy', *command], cwd=ROOT, capture_output=True)
    with (target / 'test.log').open('xb') as stream: stream.write(run.stdout + run.stderr)
    with (target / 'receipt.json').open('x') as stream:
        json.dump(dict(exitCode=run.returncode, sourceSHA256=hashes,
                       actualGPUOutputOracle=True, nativeGLExecuted=False,
                       currentMinecraftCapture=False, fullGoalAchieved=False), stream, indent=2, sort_keys=True)
    print((run.stdout + run.stderr).decode(), end='')
    if run.returncode != (1 if 'red' in label else 0): raise SystemExit(1)

if __name__ == '__main__': main(sys.argv[1])
