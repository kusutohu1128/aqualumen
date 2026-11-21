"""Compare four fresh Iris legacy records; inputs are evidence, never assumed fixed."""
import json
from pathlib import Path
import struct
import sys
import water_legacy_branch_runtime as runtime

def bits(value):
    return struct.pack('<f',value)

def compare(root):
    root=Path(root)
    roles=('phase0-full','phase0-base','phase45-full','phase45-base')
    audits={}
    stages={}
    for role in roles:
        phase,call=role.removeprefix('phase').split('-')
        pack=root/f'cpu-pack-v2/Aqualumen-ShoreProbe-world-legacy-branch-{phase}-{call}-v2.zip'
        audits[role]=runtime.audit(root/f'{role}-raw.json',pack,root/f'{role}-guard.json')
        stage=json.loads((root/f'{role}-stage.json').read_text())
        assert stage['available'] and stage['scopeAccepted'] and stage['programAndFrameUnchanged']
        assert stage['linkStatus']==1 and stage['attachedShaderCount']==4
        assert stage['worldId']=='b22dbccb-2970-41e6-847f-f183b1ec923d'
        assert stage['expectedPackSha256']==audits[role]['packSha256']
        stages[role]={s['stage']:s['sourceSha256'] for s in stage['stages'] if s['stage']!='fragment'}
    points=[]
    for i,(x,y) in enumerate(runtime.COORDS):
        raw={r:audits[r]['points'][i]['raw'] for r in roles}
        inputs={}
        for field in ('normal','view','covariance'):
            # All four components include eligibility/meanProjected/vertical.
            inputs[field]=all(tuple(map(bits,raw[r][field]))==tuple(map(bits,raw[roles[0]][field])) for r in roles)
        pairs={f'phase{p}':all(tuple(map(bits,raw[f'phase{p}-full'][f]))==tuple(map(bits,raw[f'phase{p}-base'][f])) for f in raw[roles[0]]) for p in (0,45)}
        points.append(dict(x=x,y=y,inputBitEqualityAcrossFourRoles=inputs,
            fullBaseAllSevenRecordsEqual=pairs,
            predicates={r:audits[r]['points'][i]['firstPredicate'] for r in roles},
            status={r:raw[r]['status'] for r in roles},
            allForwardReconstructionsQualified=all(audits[r]['points'][i]['forwardRayCorrespondenceQualified'] for r in roles)))
    return dict(schema='aqualumen-legacy-branch-four-role-comparison-v1',points=points,
        geometryStageHashes=stages,geometryHashesEqual=all(s==stages[roles[0]] for s in stages.values()),
        allInputBitsEqual=all(all(p['inputBitEqualityAcrossFourRoles'].values()) for p in points),
        exactOriginalSixteenQualification=False,opticalFixImplemented=False,physicalAccepted=False,
        fullFrameCauseProven=False,visualAccepted=False,motionAccepted=False,
        scope='Four actual FINAL records per role; independently re-audited. Geometry hashes, not source text or invocation proof.')

if __name__=='__main__':
    print(json.dumps(compare(sys.argv[1]),indent=2,sort_keys=True,allow_nan=False))
