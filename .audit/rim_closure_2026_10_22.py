import hashlib
import json
from pathlib import Path
import sys

root=Path('/home/kusutohu/repos/aqualumen')
out=root/'reports/2026-10-22-underwater-rim-fix'
sys.path.insert(0,str(root/'tools'))
import water_paired_runtime as runtime
runtime.prior.stopped()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
prior=json.loads((root/'reports/2026-10-22-joint-paired-water/packs/manifest.json').read_text())
pins=prior['inputs']['sha256']
current={name:sha(root/name) for name in pins}
assert current==pins
normal=json.loads((out/'runtime-hit1/restored.json').read_text())
assert all(normal[key] for key in ('instanceExact','normalConfigExact','normalModsExact','ordinarySaveExact'))
assert normal['ordinaryPack']=='Aqualumen-0.6.0.zip' and normal['ordinaryPhysics']=='0.2.0' and not normal['ordinarySaveRestored']
near=json.loads((out/'candidate-audit-near-boundary/result.json').read_text())
deep=json.loads((out/'candidate-audit-deep/result.json').read_text())
assert near['passed'] and deep['passed']
assert json.loads((out/'runtime-hit1/launcher-exit.json').read_text())['exitCode']==0
result=dict(scope='Bounded optical hit correction TEST; not full visual/physical/release acceptance',
    originalPackSourcePinsMatched=True,originalSourcePins=current,normalSettingsRestored=normal,
    ownedClientStopped=True,ownedLauncherExitCode=0,actualNearDeepOpticalTIRMatched=True,
    productionShaderChangedThisRun=False,shippingAccepted=False,visualAccepted=False,
    R2Accepted=False,depthAndRadianceCorrected=False,physicalFluidSimulationAccepted=False,
    excludedPixels=dict(near=dict(rootResidual=156,critical=3385),deep=dict(rootResidual=24,critical=2281)),
    sourceTools={str(p.relative_to(root)):sha(p) for p in [root/'tools'/name for name in
        ('water_optical_probe.py','water_optical_audit.py','water_continuous_reference.cpp','water_continuous_interface_test.glsl','water_continuous_candidate.py','water_continuous_invariance.cpp','water_paired_native_run.py','water_paired_runtime.py')]},
    evidence={str(p.relative_to(out)):sha(p) for p in
        (out/'candidate-audit-near-boundary/result.json',out/'candidate-audit-deep/result.json',out/'runtime-hit1/restored.json',
         out/'native-opticalhit1-zoom3/receipt.json',out/'invariance-hit12/receipt.json',out/'claude-review/receipt.json')})
with (out/'CLOSURE.json').open('x') as f:json.dump(result,f,indent=2)
print('Original source pins exact; actual near/deep first-hit optics matched; Lab stopped and normal0.6/physics0.2 restored; no whole-render acceptance')
