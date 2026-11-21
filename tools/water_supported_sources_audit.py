"""Independent source/raw replay, with a double-precision solar cap reference.

No producer success flag can substitute for the saved source/depth/input maps.
CPU kernel comes from the sealed independent transmission model, not GLSL.
Finite cap refinement is not a rigorous interval or pixel-AA acceptance.
"""
from array import array
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import water_supported_transmission as model

ROOT = Path(__file__).resolve().parents[1]
ROLES = ('enabled', 'disabled', 'strict', 'invalid', 'ledger')
CASES = ('zero', 'diffuse', 'sun', 'rain', 'sun-absent', 'opaque-narrow',
         'cave', 'moon', 'wide-sun', 'wide-opaque')


def normalize(a):
    length = math.sqrt(model.dot(a, a))
    return tuple(x / length for x in a)


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def cap(p, axis, radius, radial_order=4, azimuth_order=12):
    axis = normalize(axis)
    auxiliary = (0, 1, 0) if abs(axis[1]) < .95 else (1, 0, 0)
    tangent = normalize(cross(axis, auxiliary)); bitangent = cross(axis, tangent)
    delta = 2 * math.sin(.5*radius)**2
    values = []; absent = supported = 0
    for q, weight in model.interval_nodes(model.legendre(radial_order), 0, 1):
        offset = delta*q; cosine = 1-offset; sine = math.sqrt(offset*(2-offset))
        for j in range(azimuth_order):
            phi = 2*math.pi*(j+.5)/azimuth_order
            target = normalize(tuple(cosine*a+sine*(math.cos(phi)*t+math.sin(phi)*b)
                                     for a, t, b in zip(axis, tangent, bitangent)))
            node = model.inverse_kernel(p, target)
            supported += node['supported']; absent += not node['supported']
            values.append(weight*node['kernel'])
    return dict(value=math.fsum(values)*delta*2*math.pi/azimuth_order,
                supported=supported, absent=absent, calls=radial_order*azimuth_order)


def values(blob):
    result = array('f'); result.frombytes(blob)
    if sys.byteorder != 'little': result.byteswap()
    assert all(math.isfinite(a) for a in result)
    return result


def audit(root):
    root = Path(root); report = json.loads((root/'result.json').read_text())
    assert report['schema'] == 'aqualumen-supported-sources-main-v1'
    assert report['size'] == 257 and 'RTX 3080 Ti' in report['renderer'] and 'NVIDIA' in report['GL']
    size = 257; center = 16*(128*size+128); checks = 0; selected = []
    geometry = [hashlib.sha256((root/f'geometry-stage{i}.glsl').read_bytes()).hexdigest() for i in range(3)]
    canonical = ROOT/'reports/2026-10-06-water-legacy-branch/native-sources-v2'
    assert geometry == [hashlib.sha256((canonical/f'geometry-stage{i}.glsl').read_bytes()).hexdigest() for i in range(3)]
    hashes = {role:hashlib.sha256((root/f'{role}.fsh').read_bytes()).hexdigest() for role in ROLES}
    assert len(report['sourceQueries']) == 4
    for pair_index, pair in enumerate(report['sourceQueries']):
        assert len(pair) == 2
        for item_index, item in enumerate(pair):
            assert [s['sha256'] for s in item['stages'][:3]] == geometry
            expected_role = 'enabled' if item_index == 0 else ROLES[pair_index+1]
            assert item['stages'][3]['sha256'] == hashes[expected_role]
            assert item['currentProgramBefore'] == item['currentProgramAfter']
    for case_index, case in enumerate(CASES):
        folder = root/case; maps = {}; inputs = {}; states = {}; original = {}
        for role in ROLES:
            frame = []
            for slot in range(8):
                blob = (folder/f'{role}-slot{slot}.rgba32f').read_bytes()
                assert len(blob) == size*size*16
                assert blob == (folder/f'{role}-repeat-slot{slot}.rgba32f').read_bytes(); checks += 1
                if role == 'enabled': original[slot] = blob
                elif slot == 4: assert blob == original[4]; checks += 1
                frame.append(list(struct.unpack_from('<4f', blob, center)))
                values(blob)
                if slot == 0 and role in ('disabled', 'strict', 'invalid', 'ledger'):
                    # Physical effect is one TEST evaluation pixel, not a
                    # production spatial gate. All other C0 bits must match.
                    assert blob[:center] == original[0][:center] and blob[center+16:] == original[0][center+16:]
                if slot == 0 and role == 'ledger': assert blob == original[0]; checks += 1
                if slot == 0 and role == 'disabled': disabled = blob
                if slot == 0 and role in ('strict', 'invalid'): assert blob == disabled; checks += 1
            depth = (folder/f'{role}-depth.f32').read_bytes()
            assert len(depth) == size*size*4 and depth == (folder/f'{role}-repeat-depth.f32').read_bytes(); checks += 1
            if role == 'enabled': baseline_depth = depth
            else: assert depth == baseline_depth; checks += 1
            maps[role] = frame
            inputs[role] = {p.name:p.read_bytes() for p in (folder/f'{role}-actual-inputs').glob('input-sampler*.f32')}
            assert len(inputs[role]) == 8
            states[role] = json.loads((folder/f'{role}-actual-inputs/state.json').read_text())
            if role != 'enabled':
                assert inputs[role] == inputs['enabled'] and states[role] == states['enabled']; checks += 9
        state = states['enabled']; frame = maps['enabled']; ledger = maps['ledger']
        assert state.get('TESTAuthorized') == 1
        assert state['rainStrength'] == (.5 if case == 'rain' else 0)
        assert [s['unit'] for s in state['samplers']] == list(range(8))
        for slot, field in ((1, 'normal'), (2, 'view')):
            iris = json.loads((ROOT/'reports/2026-10-06-water-supported-transmission/actual-iris-inputs.json').read_text())['points'][2]
            assert struct.pack('<3f', *frame[slot][:3]) == struct.pack('<3f', *iris['raw'][field][:3])
        assert frame[1][3] == 1 and frame[5][:3] == [1, 1, 1], (case, frame[5])
        assert maps['disabled'][1][3] == 0 and maps['disabled'][5][1] == 0
        assert maps['strict'][5][:3] == [1, 0, 0]
        assert maps['invalid'][3][:3] == [0, 0, 0] and maps['invalid'][5][0] == 0
        for c in range(3):
            # MAIN max-color and one final RGB addition are binary32.
            a, b = frame[6][c], frame[7][c]
            assert struct.pack('<f', a+b) == struct.pack('<f', frame[0][c])
        p = model.prepare(frame[1][:3], frame[2][:3], frame[3][:3], frame[3][3])
        # Transform ACTUAL queried view Sun back to world, then normalize the
        # generated axis. No raw n/v repair and no stock-source-unit changes.
        inv = state['matrices']['gbufferModelViewInverse']; raw = state['sunPosition']
        axis = normalize(tuple(sum(inv[c*4+r]*raw[c] for c in range(3)) for r in range(3)))
        sky = values(inputs['enabled']['input-sampler2.f32']); cache = sky[(31*64)*4:(31*64)*4+3]
        reference = cap(p, axis, .00465); finer = cap(p, axis, .00465, 16, 48)
        projected_area = math.pi*math.sin(.00465)**2
        expected = [s*c*(1-.85*state['rainStrength'])*reference['value']/projected_area
                    for s, c in zip((18, 17.6, 17), cache)]
        solar = ledger[6][:3]
        if case in ('cave', 'wide-opaque'): expected = [0, 0, 0]
        for got, want in zip(solar, expected):
            assert abs(got-want) <= 2e-6+2e-4*abs(want), (case, got, want)
        if any(cache):
            assert ledger[1][0] == reference['absent'] and ledger[1][1] == reference['supported'] and ledger[1][3] == 48
        else: assert ledger[1] == [0, 0, 0, 0]
        assert sum(ledger[2][:3]) > 0 and ledger[2][3] == 1
        if case.startswith('wide-'):
            assert ledger[2][2] == 0  # Every admitted air ray is actually observed.
        else:
            assert ledger[2][2] > 0  # Narrow frustum needs the declared proxy.
        assert ledger[3][1] > 0, 'Miss proxy must be explicit, not black-water claim'
        if case == 'zero': assert solar == ledger[7][:3] == frame[6][:3] == [0, 0, 0]
        if case == 'diffuse':
            ref = json.loads((ROOT/'reports/2026-10-06-water-supported-transmission/reference-v4.json').read_text())['points'][2]
            assert abs(frame[6][0]-.25*ref['referenceValue']) <= .25*ref['absoluteRelativeGate']
            assert frame[6][1:3] == [0, 0]
        if case == 'sun-absent': assert ledger[1] == [48, 0, 0, 48] and solar == [0, 0, 0]
        if case == 'moon':
            moon = cap(p, tuple(-a for a in axis), .0045)
            for got, amplitude in zip(ledger[7][:3], (.12, .16, .24)):
                want = amplitude*moon['value']; assert abs(got-want) <= 2e-8+2e-4*abs(want)
            assert ledger[7][0] > 0
        if case == 'wide-sun': assert ledger[2][0] > 0 and ledger[1][1] > 0 and solar[0] > 0
        if case == 'wide-opaque':
            assert ledger[2][1] > 0 and ledger[1][2] == reference['supported'] > 0
            assert frame[6][1] > 0 and frame[6][0] == frame[6][2] == 0
        selected.append(dict(case=case, C0=frame[0], transmitted=frame[6], reflected=frame[7],
                             solar=solar, lunar=ledger[7][:3], capLedger=ledger[1], airKinds=ledger[2],
                             reflectionKinds=ledger[3][:2], solarReference=reference,
                             solarRefinementDifference=abs(reference['value']-finer['value']),
                             covariance=frame[3][:3]))
        del original, inputs
    sun_record = next(a for a in selected if a['case'] == 'sun')
    rain_record = next(a for a in selected if a['case'] == 'rain')
    assert sun_record['solar'][0] > 0
    for dry, wet in zip(sun_record['solar'], rain_record['solar']):
        assert abs(wet-.575*dry) <= 2e-6+2e-4*abs(dry)
    return dict(schema='aqualumen-supported-sources-audit-v1', renderer=report['renderer'], GL=report['GL'],
                exactRawComparisons=checks, selected=selected, actualDirectionalLUTAndCacheQualified=True,
                actualOpaqueTracePositiveQualified=True, currentTESDepthAndSourcePairsQualified=True,
                diffuseAndSunUseSameSmithKernel=True, physicalOffscreenVisibilityProven=False,
                legacyRadianceUnits=True, pixelAAAccepted=False, reflectionHitPositiveQualified=False,
                IrisAccepted=False, motionAccepted=False, shippingAccepted=False, fullGoalAchieved=False)


if __name__ == '__main__':
    print(json.dumps(audit(sys.argv[1]), indent=2, sort_keys=True))
