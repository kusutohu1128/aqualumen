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
script=root/'.audit/rim_candidate_audit_2026_10_22.py'
result=dict(scope='Review addendum only; no additional Minecraft/GPU execution and no full acceptance',
    auditScriptSHA256=sha(script),previousClosureSHA256=sha(out/'CLOSURE.json'),
    reviewerReceiptSHA256=sha(out/'claude-trail-review/receipt.json'),
    taskTable=dict(path='.audit/rim-fix-2026-10-22.todo.md',sha256=sha(root/'.audit/rim-fix-2026-10-22.todo.md'),
        originalVisualReproVerificationComplete=False),comparisons={})
for scene,oldDirs in [('near',['candidate-audit-near','candidate-audit-near-boundary']),('deep',['candidate-audit-deep'])]:
    newPath=out/('candidate-audit-'+scene+'-review/result.json')
    new=json.loads(newPath.read_text())
    assert new['auditScriptSHA256']==sha(script) and new['boundedTIRMatchPassed']
    assert new['waterPixels']==1440000 and new['solvedWaterPixels']==1440000
    comparisons=[]
    for oldDir in oldDirs:
        oldPath=out/oldDir/'result.json'
        old=json.loads(oldPath.read_text())
        changed=[key for key in old if key in new and old[key]!=new[key]]
        assert not changed,changed
        comparisons.append(dict(oldResult=str(oldPath.relative_to(root)),oldSHA256=sha(oldPath),
            commonFieldsChanged=changed,oldContemporaneousScriptHashUnavailable=True,
            interpretation='Old artifact is unchanged; saved raw data reproduced every common result under the newly pinned audit script.'))
    result['comparisons'][scene]=dict(newResult=str(newPath.relative_to(root)),newSHA256=sha(newPath),
        waterPixels=new['waterPixels'],solvedWaterPixels=new['solvedWaterPixels'],boundedTIRMatchPassed=True,
        oldResults=comparisons,openGates=new['openGates'])
closure=json.loads((out/'CLOSURE.json').read_text())
assert closure['originalSourcePins']=={name:sha(root/name) for name in closure['originalSourcePins']}
result.update(originalPackInputsStillExact=True,ordinaryRestorationReceiptUnchanged=sha(out/'runtime-hit1/restored.json')==closure['evidence']['runtime-hit1/restored.json'],
    runtimeImplementationChangedAfterFinalReview=False,shippingAccepted=False,visualAccepted=False,
    sourceAuditArtifacts={str(p.relative_to(root)):sha(p) for p in
        (script,root/'.audit/rim_reference_audit_2026_10_22.py',root/'.audit/rim_reference_run_2026_10_22.py',root/'.audit/rim_mapping_2026_10_22.py')},
    commentReview=dict(deletedUnusedDocstrings=1,deletedFile='.audit/rim_mapping_2026_10_22.py',restores=0,
        reruns=0,continuousScopedDeletionCandidates=0,applicationCodeChangesFromCommentReview=0,openConstraints=[]))
with (out/'REVIEW-ADDENDUM.json').open('x') as f:json.dump(result,f,indent=2)
print('New pinned audit reproduces all common fields of all3 old artifacts; water-only counts1.44m each; normal sources/settings intact; full visual/release gates remain open')
