"""Describe a qualified four-point phase comparison; not an optical oracle."""
import hashlib
import json
from pathlib import Path
import struct
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from water_sun_support_runtime import decode_counts
from water_atlas_joint_runtime import audit

HERE = Path(__file__).resolve().parent
PACKS = HERE.parent / 'cpu-pack'
records = []
pack_files = []
stages = []
for phase in (0, 45):
    stem = f'phase{phase}'
    pack = PACKS / f'Aqualumen-ShoreProbe-world-gh-phase-{phase}-diagnostic-aligned-v2.zip'
    result = audit(HERE / f'{stem}-joint-band.json', pack,
                   HERE / f'{stem}-original16.json', HERE / f'{stem}-guard.json',
                   HERE / f'{stem}-joint-alignment-audit.json')
    raw = json.loads((HERE / f'{stem}-joint-band.json').read_text())
    stage = json.loads((HERE / f'{stem}-water-stage.json').read_text())
    assert stage['available'] and stage['programAndFrameUnchanged']
    assert stage['usingTessellationAtAdmission'] and stage['patchVertices'] == 3
    stages.append({s['type']: s['sourceSha256'] for s in stage['stages']})
    with ZipFile(pack) as z:
        files = {n: z.read(n) for n in z.namelist()}
    assert b'#define frameTimeCounter 120.0' in files['shaders/lib/uniforms.glsl']
    pack_files.append(files)
    records.append((result, raw))

bits = lambda v: struct.pack('<' + 'f' * len(v), *v).hex()
assert records[0][1]['transportUniforms'] == records[1][1]['transportUniforms']
assert set(stages[0]) == set(stages[1]) == {35633, 35632, 36487, 36488}
assert all(stages[0][t] == stages[1][t] for t in (35633, 36487, 36488))
assert set(pack_files[0]) == set(pack_files[1])
changed = sorted(n for n in pack_files[0] if pack_files[0][n] != pack_files[1][n])
assert [n for n in changed if n.startswith('shaders/')] == ['shaders/lib/water_residual.glsl']
assert pack_files[0]['shaders/lib/water_residual_sun.glsl'] == pack_files[1]['shaders/lib/water_residual_sun.glsl']
points = []
for a, b in zip(records[0][0]['points'], records[1][0]['points']):
    assert (a['x'], a['y']) == (b['x'], b['y'])
    assert bits(a['stage']) == bits(b['stage'])
    assert bits(a['outer_state']) == bits(b['outer_state'])
    row = dict(x=a['x'], y=a['y'], tesBinary32Equal=True,
               outerStateBinary32Equal=True,
               minimumFacingBinary32Equal=bits([a['full_wr'][2], a['base_wr'][2]]) == bits([b['full_wr'][2], b['base_wr'][2]]))
    for phase, p in ((0, a), (45, b)):
        row[f'phase{phase}'] = {k: p[k] for k in
            ('full_wr', 'base_wr', 'sun_status', 'reasons', 'c0_called', 'c0Center', 'c0DisplayRgb')}
        row[f'phase{phase}']['certificateCounts'] = decode_counts(p['sun_status'][2])
    row['c0CalledRgbDelta45Minus0'] = [b['c0_called'][i] - a['c0_called'][i] for i in range(3)]
    points.append(row)

changed_admission = [p for p in points if p['phase0']['full_wr'][:2] != p['phase45']['full_wr'][:2]]
assert len(changed_admission) == 1 and changed_admission[0]['y'] == 155
assert changed_admission[0]['phase0']['full_wr'][:2] == [1, 1]
assert changed_admission[0]['phase45']['full_wr'][:2] == [0, 0]
assert changed_admission[0]['phase45']['certificateCounts']['calls'] == 0
assert all(x < 0 for x in changed_admission[0]['c0CalledRgbDelta45Minus0'])
print(json.dumps(dict(
    schema='aqualumen-selected-gh-admission-comparison-v1',
    selectedPoints=4, shaderMembersChanged=changed,
    linkedGeometryStageHashesEqual=True,
    transportUniformsEqual=True, fixedWaveAndSkyTimeSeconds=120,
    selectedAdmissionChanges=len(changed_admission), points=points,
    selectedEncodedOutputCorrespondenceQualified=True,
    sourceSun48HelperUnchanged=True,
    sun48ExecutionInvariant=False,
    fullFrameInputEqualityProven=False,
    exactFailedLegacyPredicateObserved=False,
    wholeBandCausalityAccepted=False, opticalFixImplemented=False,
    visualAccepted=False, motionAccepted=False, shippingAccepted=False,
    interpretation='At source (1114,155), the rotated finite rule changes both legacy '
        'valid/applied states 1/1 to 0/0 with equal recorded TES, outer state and '
        'transport uniforms. Minimum facing changes with the sampled nodes but '
        'stays positive. The Sun wrapper then skips its 48 calls; '
        'water C15 and displayed C0 are darker. This is a selected correspondence '
        'and phase-sensitive admission finding, not proof of every band or a '
        'particular compound predicate. Covariance/n/v/node directions were not '
        'captured. Other selected points also change color while still admitted.'
), indent=2, sort_keys=True, allow_nan=False))
