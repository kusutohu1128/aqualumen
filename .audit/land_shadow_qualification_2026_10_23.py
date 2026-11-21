import json
from pathlib import Path
import sys
from zipfile import ZipFile

root = Path('/home/kusutohu/repos/aqualumen')
sys.path.insert(0, str(root / 'tools'))
from land_shadow_run import save, sha

report = root / 'reports/2026-10-23-land-shadows'
pack = report / 'Aqualumen-LandShadows-Preview-2026-10-23.zip'
native = report / 'native-candidate2/receipt.json'
compile_receipt = report / 'candidate2-checks/compile.json'
motion = report / 'motion2-checks/receipt.json'
data = json.loads(native.read_text())
assert data['candidateQualified'] and data['observedExit'] == 0 and data['algorithm'] == 'land'
with ZipFile(pack) as archive:
    for name in archive.namelist():
        if name.startswith('shaders/'):
            import hashlib
            assert hashlib.sha256(archive.read(name)).hexdigest() == data['sourcePins'][name]
for path in (compile_receipt, motion):
    proof = json.loads(path.read_text())
    assert proof['packSHA256'] == sha(pack) and proof['exitCode'] == 0
    assert 'NVIDIA GeForce RTX 3080 Ti' in proof['renderer']
assert json.loads(motion.read_text())['passed']
save(report / 'qualification.json', dict(schema='land-shadow-qualification-v1',
     packSHA256=sha(pack), evidence={name: dict(path=str(path), sha256=sha(path))
         for name, path in (('native', native), ('compile', compile_receipt), ('motion', motion))},
     physicalScope='26 fixed synthetic geometry checks plus513fixed-light receiver translations',
     actualMinecraft=False, releaseAccepted=False, performanceMeasured=False))
print('Pack-bound NVIDIA native/compile/motion eligibility saved; Iris comparison still required.')
