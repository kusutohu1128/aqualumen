#!/usr/bin/env bash
set -euo pipefail
cd /home/kusutohu/repos/aqualumen
task_java=/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/java/java-runtime-delta/bin
task_classes=$(mktemp -d build/receiver-vertex-shader-test-classes.XXXXXX)
"$task_java/javac" -proc:none -Xlint:all -d "$task_classes" physics-mod/dev/aqualumen/physics/ReceiverVertexShader.java physics-mod/test/dev/aqualumen/physics/ReceiverVertexShaderTest.java
python3 - "$task_java/java" "$task_classes" <<'PY'
import json
from pathlib import Path
import struct
import subprocess
import sys
out = Path('reports/2026-10-06-water-receiver-draw')
draw = json.loads((out / 'actual-draw-readback.json').read_text())
mesh = json.loads((out / 'archived-actual-mesher-inputs.json').read_text())
words = [v for event in mesh['actualMesherEncodes'] for v in event['encodedFirst20ByteWords']]
gpu = draw['gpuDecode']['uvLightmapColor']
assert len(words) == len(gpu) == 56 and all(len(v) == 8 for v in gpu)
body = struct.pack('>I18f', 56, *draw['lightmapMatrixColumnMajor'], *draw['texCoordShrink'])
for v, observed in zip(words, gpu):
    body += struct.pack('>3I8f', *v[2:5], *observed)
result = subprocess.run([sys.argv[1], '-cp', sys.argv[2], 'dev.aqualumen.physics.ReceiverVertexShaderTest'], input=body)
raise SystemExit(result.returncode)
PY
