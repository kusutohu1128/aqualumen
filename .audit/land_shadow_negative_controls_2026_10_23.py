import json
import os
from pathlib import Path
import shutil
import sys

root = Path('/home/kusutohu/repos/aqualumen')
sys.path.insert(0, str(root / 'tools'))
from land_shadow_run import execute, save, sha

report = root / 'reports/2026-10-23-land-shadows'
out = report / 'negative-controls1'
out.mkdir(exist_ok=False)
environment = dict(os.environ, __EGL_VENDOR_LIBRARY_FILENAMES='/usr/share/glvnd/egl_vendor.d/10_nvidia.json')
native = report / 'native-candidate2/land-shadow-native'
motion = report / 'motion2-checks/land-shadow-motion'
source = report / 'candidate2-checks/pack/shaders'
mutations = {
    'flat-reference': ('float lightZ = receiver.lightPosition.z-dot(receiver.lightNormal.xy,displacement)/receiver.lightNormal.z;',
                       'float lightZ = receiver.lightPosition.z;'),
    'legacy-bias': ('float residualBias = 0.002*receiver.depthPerMetre+2.0/16777215.0;',
                    'float residualBias = 0.00015;'),
    'nearest-only': ('return mix(mix(a,b,fraction.x),mix(c,d,fraction.x),fraction.y);', 'return a;'),
}
results = {}
for name, (old, new) in mutations.items():
    folder = out / name
    folder.mkdir()
    shader = folder / 'shaders'
    shutil.copytree(source, shader)
    helper = shader / 'lib/land_shadows.glsl'
    text = helper.read_text()
    assert text.count(old) == 1
    helper.write_text(text.replace(old, new))
    binary = motion if name == 'nearest-only' else native
    run = execute([binary, shader, 'land', folder / 'capture'], folder, 'native', environment)
    data = json.loads((folder / 'capture/RESULT.json').read_text())
    assert 'NVIDIA GeForce RTX 3080 Ti' in data['renderer'] and run.returncode == 2
    if name == 'nearest-only':
        assert data['endpointContrastPassed'] and not data['maximumStepPassed']
    else:
        assert data['positiveControlsPassed'] and not data['allPhysicalTargetsPassed']
        scene = 'contact-gap-004m' if name == 'legacy-bias' else 'analytic-self-offaxis-60'
        target = next(item for item in data['scenarios'] if item['name'] == scene)
        assert not target['targetPassed'] and target['wrongReceiverPixels'] > 100
    results[name] = dict(exitCode=run.returncode, expectedRedObserved=True,
        mutatedHelperSHA256=sha(helper), resultSHA256=sha(folder / 'capture/RESULT.json'),
        negativeControlNotCandidate=True)
save(out / 'receipt.json', dict(controls=results, packSourceSHA256=sha(source / 'lib/land_shadows.glsl'),
     nativeBinarySHA256=sha(native), motionBinarySHA256=sha(motion),
     renderer='NVIDIA GeForce RTX 3080 Ti', actualMinecraft=False, performanceMeasured=False))
print('Three GPU negative controls failed their intended unchanged targets; production source untouched.')
