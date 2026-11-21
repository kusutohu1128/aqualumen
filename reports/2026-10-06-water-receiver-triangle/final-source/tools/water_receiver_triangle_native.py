"""Fresh normal baseline -> exclusive saved-source NVIDIA fixture -> normal reopen."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import sys
from water_receiver_triangle_record import OUT, ROOT, GAME, copy, sha
import water_receiver_texture_lifecycle as base

base.OUT=OUT
base.JAR='aqualumen-receiver-triangle-NOT-INSTALLED.jar'
base.PROPERTY='aqualumen-receiver-triangle-NOT-ENABLED.properties'

def baseline():
    base.closed()
    if 'All dimensions are saved' not in (GAME/'logs/latest.log').read_text():raise ValueError('Clean ordinary save required')
    cache=Path(tempfile.mkdtemp(prefix='aqualumen-legacy-branch-host-receiver-triangle-',dir='/home/kusutohu/.cache'))
    for name in ('options.txt','config/iris.properties','config/aqualumen-benchmark.properties'):copy(GAME/name,cache/name)
    base.save('fresh-normal-baseline.json',base.original(cache))
    copy(GAME/'logs/latest.log',OUT/'normal-clean-save-exit.log')
    print('Fresh post-save ordinary41-file/config/Mod baseline; no TEST install',cache)

def native():
    base.closed()
    baseline=json.loads((OUT/'fresh-normal-baseline.json').read_text())
    if base.original(Path(baseline['backup']))!=baseline:raise ValueError('Ordinary state changed')
    folder=OUT/'native-v1';folder.mkdir(exist_ok=False)
    hashes={}
    for name in ('tools/receiver-triangle-gpu.cpp','tools/water_receiver_triangle_native.py','tools/water_receiver_triangle_record.py'):
        copy(ROOT/name,folder/'source'/name);hashes[name]=sha(ROOT/name)
    contract=json.loads((OUT/'input-contract.json').read_text())
    draw=json.loads((OUT/'archived-draw.json').read_text())
    with (folder/'actual-linked.vsh').open('x') as stream:stream.write(draw['linkedVertexSource'])
    body=struct.pack('<3I18f',0x41515431,14,len(contract['samples']),*draw['lightmapMatrixColumnMajor'],*draw['texCoordShrink'])
    for f in contract['faces']:body+=struct.pack('<I3f20I',f['axis'],*f['offset'],*(w for v in f['words'] for w in v))
    body+=struct.pack('<84I',*contract['actualIndices']['INTEGER'])
    for p in contract['samples']:body+=struct.pack('<I2f',p['face'],p['s'],p['t'])
    with (folder/'native-input.bin').open('xb') as stream:stream.write(body)
    run=subprocess.run(['rtk','proxy','g++','-std=c++17','-O2','-Wall','-Wextra','tools/receiver-triangle-gpu.cpp','-o',str(folder/'triangle-gpu'),'-lepoxy','-lEGL'],cwd=ROOT,capture_output=True)
    with (folder/'compile.log').open('xb') as stream:stream.write(run.stdout+run.stderr)
    if run.returncode:raise ValueError('Native fixture compile failed; retained log/source')
    run=subprocess.run(['rtk','proxy',str(folder/'triangle-gpu'),str(folder/'actual-linked.vsh'),str(folder/'native-input.bin'),str(folder/'native-outputs.f32')],cwd=ROOT,capture_output=True)
    with (folder/'runtime.log').open('xb') as stream:stream.write(run.stdout+run.stderr)
    base.save('native-v1-receipt.json',dict(sourceSHA256=hashes,exitCode=run.returncode,
        actualLinkedVertexSHA256=sha(folder/'actual-linked.vsh'),binarySHA256=sha(folder/'triangle-gpu'),
        inputSHA256=sha(folder/'native-input.bin'),rendererMustBeNVIDIA=True,originalFragmentInvocation=False,
        actualMinecraftFrameTimings=False,fullGoalAchieved=False))
    print((run.stdout+run.stderr).decode(),end='')
    if run.returncode:raise ValueError('Native fixture failed; do not restart client without checking')
    if any(sha(ROOT/n)!=h for n,h in hashes.items()):raise ValueError('Native source changed during execution')
    after=base.original(Path(baseline['backup']))
    if after!=baseline:raise ValueError('Ordinary state changed during native fixture')
    base.save('normal-exact-after-native.json',after)

if __name__=='__main__':
    action=sys.argv[1]
    if action=='baseline':baseline()
    elif action=='native':native()
    elif action=='normal':base.launch('normal')
    else:raise ValueError('Declared safe lifecycle action required')
