"""Independent old/new raw/class comparison and binary32 first-plane replay."""
import hashlib
import json
import math
from pathlib import Path
import struct
import water_source_boundary_audit as retained
import water_source_boundary_oracle as oracle
from water_path_precision_prepare import ROOT, OUT

OLD = ROOT / 'reports/2026-10-06-water-source-boundary/fixed-observed-12-01'
OLD_SOURCE = ROOT / 'reports/2026-10-06-water-source-boundary/fixed-observer-12-v1'
NEW = OUT / 'refine12-main-01'
SOURCE = OUT / 'refine12-observer-v1'


def run():
    qualified = retained.audit(NEW, SOURCE)
    assert qualified['nodes'] == 288
    assert (qualified['actualHits'], qualified['actualMisses']) == (97, 191)
    assert qualified['observedPlaneMisses'] == qualified['hitsOutsideOracleSafetyViewport'] == 0
    anchor = 'for (int refine=0;refine<4;++refine)'
    assert (SOURCE / 'baseline.fsh').read_text() == (OLD_SOURCE / 'baseline.fsh').read_text().replace(
        anchor, 'for (int refine=0;refine<12;++refine)', 1)
    exact = 0
    def same(a, b):
        nonlocal exact
        assert a.read_bytes() == b.read_bytes(), (str(a), str(b))
        exact += 1
    for name in [f'geometry-stage{i}.glsl' for i in range(3)] + ['probability-rule.json']:
        same(SOURCE / name, OLD_SOURCE / name)
    for tag in ('black', 'green'):
        for role in ('baseline', 'observer'):
            for path in (OLD / tag / f'{role}-actual-inputs').iterdir():
                same(path, NEW / tag / f'{role}-actual-inputs' / path.name)
            for slot in range(1, 7):
                same(OLD / tag / f'{role}-slot{slot}.rgba32f', NEW / tag / f'{role}-slot{slot}.rgba32f')
            same(OLD / tag / f'{role}-depth.f32', NEW / tag / f'{role}-depth.f32')
            if tag == 'black':
                for slot in (0, 7):
                    same(OLD / tag / f'{role}-slot{slot}.rgba32f', NEW / tag / f'{role}-slot{slot}.rgba32f')
        a = retained.records(OLD / tag / 'observer-nodes.bin')
        b = retained.records(NEW / tag / 'observer-nodes.bin')
        assert len(a) == len(b) == 288
        for i, (old, new) in enumerate(zip(a, b)):
            assert (old[6][3] > 0) == (new[6][3] > 0), i
            for slot in list(range(6)) + list(range(8, 17)) + [20, 21]:
                assert old[slot] == new[slot], (tag, i, slot)
                exact += 1
            if old[6][3] < 0:
                assert old == new, (tag, i, 'miss changed')
                exact += 1
    state = json.loads((NEW / 'green/observer-actual-inputs/state.json').read_text())
    inverse = state['matrices']['gbufferProjectionInverse']
    depth = {a[0] for a in struct.iter_unpack('<f', (NEW / 'green/observer-actual-inputs/input-sampler3.f32').read_bytes())}
    assert len(depth) == 1
    f32 = lambda a: struct.unpack('<f', struct.pack('<f', a))[0]
    z = f32(f32(next(iter(depth)) * 2) - 1)
    scene_z = f32(f32(f32(inverse[10] * z) + inverse[14]) / f32(f32(inverse[11] * z) + inverse[15]))
    rows = []
    a = retained.records(OLD / 'green/observer-nodes.bin')
    b = retained.records(NEW / 'green/observer-nodes.bin')
    for i, (old, new) in enumerate(zip(a, b)):
        if old[6][3] < 0:
            continue
        assert old[19][2] == new[19][2] == scene_z
        truth = oracle.first_plane(new[3][:3], new[4][:3], state['matrices']['gbufferProjection'], -scene_z)
        expected = math.exp(-.085 * truth['distance'])
        center = min(*truth['screen'], *(1-v for v in truth['screen'])) > .1
        row = dict(index=i, firstPlaneMeters=truth['distance'], oldPathMeters=old[6][3],
                   newPathMeters=new[6][3], oldPathErrorMeters=old[6][3]-truth['distance'],
                   newPathErrorMeters=new[6][3]-truth['distance'], center=center,
                   expectedUnitGreen=expected, oldUnitError=abs(old[7][1]/.125-expected),
                   newUnitError=abs(new[7][1]/.125-expected), unchangedUnitGate=2e-6+2e-4*expected)
        if center:
            assert old[17][2:] == new[17][2:] == (1., 1.)
            assert row['newUnitError'] <= row['unchangedUnitGate'], row
        rows.append(row)
    assert sum(r['center'] for r in rows) == 85
    assert rows[0]['oldUnitError'] > rows[0]['unchangedUnitGate']
    assert rows[0]['newUnitError'] <= rows[0]['unchangedUnitGate']
    return dict(schema='aqualumen-path-precision-audit-v1', renderer=qualified['renderer'], GL=qualified['GL'],
                exactOldNewComparisons=exact, nodeCount=288, retainedHits=97, retainedMisses=191,
                actualInputGeometryProbabilityAndUnchangedMRTExact=True,
                blackAllMRTExact=True, actualSceneZ=scene_z, centerOpticalGates=85,
                firstCenter=rows[0], oldMaxPathErrorMeters=max(abs(r['oldPathErrorMeters']) for r in rows),
                newMaxPathErrorMeters=max(abs(r['newPathErrorMeters']) for r in rows),
                oldMaxCenterUnitError=max(r['oldUnitError'] for r in rows if r['center']),
                newMaxCenterUnitError=max(r['newUnitError'] for r in rows if r['center']),
                replayedGreen=qualified['replayedGreen'], selected=rows,
                candidateFunctionSHA256=hashlib.sha256(__import__('water_path_precision_prepare').tracer((SOURCE/'baseline.fsh').read_text()).encode()).hexdigest(),
                arbitraryGeometryAccepted=False, IrisAccepted=False, MinecraftFPSMeasured=False,
                convergenceAccepted=False, temporalAccepted=False, fullGoalAchieved=False)


if __name__ == '__main__':
    print(json.dumps(run(), indent=2, sort_keys=True))
