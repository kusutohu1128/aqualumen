import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile

root = Path('/home/kusutohu/repos/aqualumen')
sys.path.insert(0, str(root / 'tools'))
from land_shadow_run import save, sha

report = root / 'reports/2026-10-23-land-shadows'
jar = root / 'build/aqualumen-benchmark-0.3.9-projection-guards.jar'
assert sha(jar) == 'ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29'
with ZipFile(jar) as archive:
    classes = [name for name in archive.namelist() if 'NativeMotion' in name]
    recorder = archive.read('dev/aqualumen/bench/Recorder.class')
assert not classes and b'native_motion_capture_active' not in recorder
label = 'System.nanoTime render-tail intervals; one start boundary discarded; setup/screenshots outside sample'
assert label.encode() in recorder
manifest = report / 'runtime1/ordinary-run/run.json'
data = json.loads(manifest.read_text())
assert 'native_motion_capture_active' not in data and data['frame_method'] == label
assert data['mods']['aqualumen_benchmark'] == '0.3.9'
save(report / 'capture-protocol.json', dict(pinnedBenchmarkSHA256=sha(jar),
     recorderClassSHA256=hashlib.sha256(recorder).hexdigest(), nativeMotionClasses=classes,
     hasMotionMetadataKey=False, staticFrameMethod=label, ordinaryRunManifestSHA256=sha(manifest),
     oldCollectorSHA256=sha(report / 'runtime-tool-checks/sources/.audit/land_shadow_runtime_2026_10_23.py'),
     repairedCollectorSHA256=sha(root / '.audit/land_shadow_runtime_2026_10_23.py'),
     ordinaryRunRerun=False, shaderChanged=False, thresholdsChanged=False,
     reason='Collection boundary expected current-source metadata absent from the exact pinned0.3.9binary'))
print('Pinned class/run protocol difference recorded; no game or shader change.')
