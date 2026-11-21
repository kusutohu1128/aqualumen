"""Independent saved-input/replay and original-SSR path attribution, not adoption."""
import hashlib
import json
import math
from pathlib import Path
import struct
import water_source_boundary_audit as saved
import water_source_boundary_oracle as oracle
import water_observed_plane_integral as integral
import water_supported_conditioned as model

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/2026-10-06-water-observed-plane'
BASE = ROOT / 'reports/2026-10-06-water-source-boundary'


def audit():
    old = json.loads((OUT / 'integral-results-v1.json').read_text())
    replay = json.loads((OUT / 'integral-results-v1-replay.json').read_text())
    current = json.loads((OUT / 'integral-results-v2.json').read_text())
    exact = 0
    for before, after in zip(old['results'], replay['results']):
        assert before['order'] == after['order']
        for a, b in zip(before['modes'], after['modes']):
            for key, value in a.items():
                assert b[key] == value
                exact += 1
    path = BASE / 'fixed-observed-12-01'
    raw = saved.records(path / 'green/observer-nodes.bin')
    node = raw[0]
    state = json.loads((path / 'green/observer-actual-inputs/state.json').read_text())
    assert current['actualState'] == state
    assert current['actualNodeCaptureSHA256'] == hashlib.sha256((path / 'green/observer-nodes.bin').read_bytes()).hexdigest()
    for key, expected in (('rawNormal', node[10][:3]), ('rawView', node[11][:3]), ('rawCovariance', node[12][:3]), ('origin', node[2][:3])):
        assert current[key] == list(expected)
    assert current['eta'] == node[10][3]
    for name, digest in current['algorithmSHA256'].items():
        assert hashlib.sha256((ROOT / 'tools' / name).read_bytes()).hexdigest() == digest
    # The early v1 output lacked code hashes. Current non-fade replay reproduces
    # all its numeric fields exactly; it does not rewrite that earlier evidence.
    p = model.t.prepare(node[10][:3], node[11][:3], node[12][:3], node[10][3])
    matrix, projection = (state['matrices'][key] for key in ('gbufferModelView', 'gbufferProjection'))
    port = []
    geometry = saved.audit(path, BASE / 'fixed-observer-12-v1')
    for order in (8, 12):
        capture = saved.audit(BASE / f'fixed-observed-{order}-01', BASE / f'fixed-observer-{order}-v1')
        value = next(r['modes'][0]['knownWindowGreen'] for r in current['results'] if r['order'] == order)
        error = abs(value - capture['sameNodesTruePlaneGreen'])
        assert error <= 1e-7
        port.append(dict(order=order, CPU=value, savedSameNodeTruePlane=capture['sameNodesTruePlaneGreen'], difference=error))
    comparisons = []
    for mode in (2, 3):
        reference = current['results'][-1]['modes'][mode]['knownWindowGreen'] / .125
        previous = current['results'][-2]['modes'][mode]['knownWindowGreen'] / .125
        gate = 2e-6 + 2e-4*abs(reference)
        refinement = abs(reference-previous)
        assert refinement < gate
        for order in (4, 8, 12):
            record = next(r['modes'][mode] for r in current['results'] if r['order'] == order)
            measured = record['knownWindowGreen'] / .125
            comparison = dict(edge=mode == 3, order=order, actualCPUUnitResponse=measured,
                finite128Reference=reference, finite96To128Difference=refinement,
                retainedUnitCoefficientGate=gate, absoluteError=abs(measured-reference),
                meetsSelectedDiagnosticGate=abs(measured-reference)+refinement <= gate,
                sourceEvaluations=record['sourceEvaluations'])
            assert comparison['meetsSelectedDiagnosticGate']
            comparisons.append(comparison)
    original_path = []
    depth_blob = (path / 'green/observer-actual-inputs/input-sampler3.f32').read_bytes()
    depths = {a[0] for a in struct.iter_unpack('<f', depth_blob)}
    assert len(depths) == 1
    depth = next(iter(depths))
    f32 = lambda a: struct.unpack('<f', struct.pack('<f', a))[0]
    inverse = state['matrices']['gbufferProjectionInverse']
    clip_z = f32(f32(depth*2)-1)
    numerator = f32(f32(inverse[10]*clip_z)+inverse[14])
    denominator = f32(f32(inverse[11]*clip_z)+inverse[15])
    reconstructed_z = f32(numerator/denominator)
    assert reconstructed_z == -5.99981689453125
    # Camera/depth binary32 reconstruction is a DIFFERENT plane from nominal6m.
    # Independently reconstruct from actual depth/matrix, never fit to a result.
    for index, item in enumerate(geometry['selected']):
        if not item['actualHit']:
            continue
        observation = raw[index]
        assert observation[19][2] == reconstructed_z
        truth = oracle.first_plane(observation[3][:3], observation[4][:3], projection, -reconstructed_z)
        assert truth['kind'] == 'observed-plane'
        exact_distance = truth['distance']
        current_distance = observation[6][3]
        assert current_distance >= exact_distance-2e-5, (index, current_distance, exact_distance)
        confidence, edge = observation[17][2:]
        exact_edge = integral.smoothstep(0., .08, min(*truth['screen'], *(1-a for a in truth['screen'])))
        expected = .125*math.exp(-.085*exact_distance)*exact_edge
        original_path.append(dict(index=index, firstUV=truth['screen'], refinedUV=observation[17][:2],
            trueDistance=exact_distance, actualDistance=current_distance,
            pathOvershoot=current_distance-exact_distance,
            actualConfidence=confidence, actualEdge=edge, exactEdge=exact_edge,
            actualSource=observation[7][1], exactPlaneEdgeSource=expected, weight=item['weight']))
    assert len(original_path) == 97
    assert all(row['actualConfidence'] == 1.0 for row in original_path)
    center = [r for r in original_path if min(*r['firstUV'], *(1-a for a in r['firstUV'])) > .1]
    assert center and any(r['pathOvershoot'] > .02 for r in center)
    # No GPU/SSR correction is inferred from success of the different functional.
    return dict(schema='aqualumen-observed-plane-audit-v1', exactV1ReplayFields=exact,
        sameCapturedNodePortComparisons=port, selectedDiagnosticComparisons=comparisons,
        originalSSRPathAttribution=original_path, centerObservedHits=len(center),
        recordedSSRConfidenceIsExactlyOne=True,
        actualBinary32ReconstructedPlaneZ=reconstructed_z,
        nominalDeclaredPlaneDistance=state['planeViewDistance'],
        sourcePlanePrecisionScope='CPU integral uses declared6m; SSR path attribution separately uses independently binary32 reconstructed observed depth plane.',
        selectedPlaneCPUNumericGatesPassed=True, actualSSRSourceGatePassed=False,
        arbitraryGeometryProven=False, GLSLPortExecuted=False, intervalCertified=False,
        IrisAccepted=False, temporalAccepted=False, physicalEnergyAccepted=False, fullGoalAchieved=False,
        scope='CPU observed-window/fade functional and actual saved-node geometry/path attribution. Finite refinement is not certified integration; it is not the existing SSR functional, full unobserved scene or a Minecraft fix.')


if __name__ == '__main__':
    record = audit()
    with (OUT / 'independent-audit-v2.json').open('x') as output:
        json.dump(record, output, indent=2, sort_keys=True)
    print('PASSED selected CPU window/fade gates, exact replay and original SSR path attribution; not actual SSR acceptance')
