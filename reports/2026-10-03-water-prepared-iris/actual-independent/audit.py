"""CPU replay of saved prepared Iris telemetry; never a runtime action."""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from water_sun_prepared_runtime import audit as prepared_audit
from water_sun_support_runtime import audit as support_audit
from water_residual_sun_iris_runtime import IDENTITY, json_file, exact_fields
from report import check_png, metrics, validate_underwater_up
from test_thin_runtime_audit import read_intervals

PINS = {
    'tools/water_sun_prepared_runtime.py': '15a47cec7db8cb5d9f5aed586e1111fd085768d20f7868d059485dadd716acd5',
    'tools/water_sun_support_runtime.py': 'f7d37236671e4333ac12312dae32cd6cdec39023dee01622f12258d7bc680d31',
    'tools/report.py': '716e7dbbb58c736ad076f317d214f23ba542bc0e91b1b480865eb1d37201b31c',
    'tools/test_thin_runtime_audit.py': 'c8954f7f436ce23444bc05aeb048a6b0691e3e434aa9c80cc0ecff64d2988630',
    'reports/2026-10-03-water-sun-support/cpu-independent-iris/audit.py': '911265553e2f44cf6ea475cdb3a69343fb9f7d5ae75be18ba012aa2f7133315f'}
PACK_PINS = {'reasons': 'c9bd5eb7f945039858e3ccd985a3c634e7526b63a00cdb7d3137dce6271d0ca2',
             'inputs': '4bacca9e88b993e6c274db4aa91f807f75af3a0aa1eab2b91ecf6411c4b7cc02'}
OLD = ROOT / 'reports/2026-10-03-water-sun-support'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def raw_bits(values):
    require(len(values) == 4 and all(type(v) in (float, int) and math.isfinite(v)
        and struct.unpack('<f', struct.pack('<f', v))[0] == v for v in values), 'Lossless finite binary32 vec4 required')
    return [struct.pack('<f', v).hex() for v in values]


def audit(packet, role):
    packet = Path(packet).resolve()
    require(role in PACK_PINS, 'Only reasons or inputs supported')
    for name, pin in PINS.items():
        require(sha((ROOT / name).read_bytes()) == pin, 'Frozen audit helper changed: ' + name)
    spec = importlib.util.spec_from_file_location('frozen_support_replay', OLD / 'cpu-independent-iris/audit.py')
    old_helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old_helpers)
    runtime = packet / 'runtime'
    run_dir = runtime / ('new-' + role)
    pack = packet / 'cpu-pack' / f'Aqualumen-ShoreProbe-world-sun-prepared-{role}-v1.zip'
    require(sha(pack.read_bytes()) == PACK_PINS[role], 'Actual prepared export pin changed')
    raw_path, guard_path, stage_path = [runtime / f'new-{role}-{suffix}.json' for suffix in ('final', 'guard', 'stage')]
    recalculated = prepared_audit(raw_path, pack, guard_path)
    canonical = (json.dumps(recalculated, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    require((runtime / f'new-{role}-audit.json').read_bytes() == canonical, 'Saved root audit replay differs')
    raw, guard, stage = map(json_file, (raw_path, guard_path, stage_path))
    identity = {**IDENTITY, 'packName': pack.name, 'packSha256': PACK_PINS[role]}
    stages = old_helpers.stage_contract(stage, identity)
    require(stage['constructorProgram'] == guard['constructorProgram'], 'Prepared guard/stage program differs')
    independent = old_helpers.independent_raw(raw, role, 'zero')
    run, complete, scene = [json_file(run_dir / name) for name in ('run.json', 'complete.json', 'underwater-up-near.json')]
    exact_fields(run, dict(world_id=IDENTITY['worldId'], seed=308060, world_generator='minecraft:noise/overworld',
        scenarios=['underwater-up-near'], warmup_seconds=5.0, sample_seconds=5.0, frame_limit=120,
        vsync=False, render_chunks=12, simulation_chunks=6, expected_resolution=[1600, 900]), 'Changed warmed near controls')
    for value in (run, scene):
        exact_fields(value, dict(world_id=IDENTITY['worldId'], pack_name=pack.name, pack_sha256=PACK_PINS[role],
            shader_active=True, shader_fallback=False, resolution=[1600, 900], framebuffer_resolution=[1600, 900],
            player_dimension='minecraft:overworld'), 'Wrong actual scene/shader identity')
    exact_fields(complete, dict(status='complete', scenarios=['underwater-up-near'], fixture_cleanup_complete=True), 'Incomplete measurement')
    require(run['run_id'] == complete['run_id'] == scene['run_id'] and scene['window_focused'] is True
        and scene['camera_follows_local_player'] is True and scene['physics_active_seen'] is True, 'Wrong focus/local actor/run')
    require(run['mods']['aqualumen_benchmark'] == '0.3.9' and run['mods']['aqualumen_physics'] == '0.3.0'
        and 'NVIDIA' in run['gl_renderer'] and '3080 Ti' in run['gl_renderer'], 'Wrong recorded runtime stack')
    iris = dict(line.split('=', 1) for line in run['iris_configuration'].splitlines() if line and not line.startswith('#') and '=' in line)
    require(iris.get('enableShaders') == 'true' and iris.get('shaderPack') == pack.name, 'Wrong recorded selected pack')
    validate_underwater_up(scene, 'underwater-up-near')
    check_png(run_dir / 'underwater-up-near.png', (1600, 900))
    ns, ms = read_intervals(run_dir / 'underwater-up-near.csv')
    measured = metrics(ms)
    require(scene['sample_seconds_actual'] >= 4.9 and sum(ns) >= 4.9e9, 'Truncated five-second sample')
    for name, value in measured.items():
        require(scene[name] == value if type(value) is int else math.isclose(scene[name], value, rel_tol=1e-12, abs_tol=1e-9),
                'Integer-ns metric differs: ' + name)
    require(raw['unshiftedCameraPosition'] == scene['actual_camera_position'], 'Held raw camera differs')
    require(all(stamp(complete['utc']) < stamp(value) for value in (raw['utc'], guard['capturedUtc'], stage['capturedUtc'])),
            'Observer preceded measurement completion')
    old_dir = OLD / ('iris-zero-' + role)
    old_pack = OLD / 'cpu-pack' / f'Aqualumen-ShoreProbe-world-sun-support-zero-{role}-v1.zip'
    old_replay = support_audit(old_dir / 'final-raw.json', old_pack, old_dir / 'guard-raw.json')
    old_raw, old_stage = json_file(old_dir / 'final-raw.json'), json_file(old_dir / 'stage-raw.json')
    old_stages = old_helpers.stage_contract(old_stage, {**IDENTITY, 'packName': old_pack.name, 'packSha256': sha(old_pack.read_bytes())})
    geometry = {k: v for k, v in stages.items() if k != '35632'}
    require(geometry == {k: v for k, v in old_stages.items() if k != '35632'}, 'Actual rewritten geometry stage changed')
    comparisons = []
    for i in range(16):
        coordinates = [(s['samples'][i]['x'], s['samples'][i]['y']) for s in raw['samplers'][:4]]
        require(coordinates == [(s['samples'][i]['x'], s['samples'][i]['y']) for s in old_raw['samplers'][:4]], 'Old/new selected order differs')
        labels = ('reasonTuple', 'status', 'covarianceFlags', 'TES') if role == 'reasons' else ('meanCalled', 'viewRequested', 'covarianceFlags', 'firstTargetReason')
        equal = {}; fields = {}
        for label, current, previous in zip(labels, raw['samplers'][:4], old_raw['samplers'][:4]):
            new_bits, old_bits = raw_bits(current['samples'][i]['rgba']), raw_bits(previous['samples'][i]['rgba'])
            equal[label] = new_bits == old_bits
            fields[label] = dict(newBits=new_bits, oldBits=old_bits)
        comparisons.append(dict(x=coordinates[0][0], y=coordinates[0][1], fields=fields, binary32Equal=equal))
    files = [raw_path, guard_path, stage_path, runtime / f'new-{role}-audit.json', pack,
             *(run_dir / name for name in ('run.json', 'complete.json', 'underwater-up-near.json', 'underwater-up-near.csv', 'underwater-up-near.png'))]
    return dict(schema='aqualumen-independent-prepared-iris-v1', evidenceReplay='PASS', role=role,
        packSha256=PACK_PINS[role], publicReplaySha256=sha(canonical), validatorSourceSha256=PINS,
        selectedPoints=16, selectedAudit=recalculated, independentlyDecodedPoints=independent,
        oldPublicAuditSha256=sha((json.dumps(old_replay, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()),
        oldPointBinary32Equal={label: sum(p['binary32Equal'][label] for p in comparisons) for label in labels},
        oldPointComparisons=comparisons, actualGeometryStageHashes=geometry, actualFragmentStageHash=stages['35632'],
        oldFragmentStageHash=old_stages['35632'], metrics=measured, rawFrameIntervals=len(ns), rawNanosecondsTotal=sum(ns),
        actualEyeDepth=scene['underwater_up']['actual_eye_depth'], guardFrame=guard['frameBefore'], stageFrame=stage['frameBefore'],
        finalFrame=raw['snapshotFrame'], observationsAfterComplete=True, fullPngCRCQualified=True,
        fileSha256={str(p.relative_to(packet)): sha(p.read_bytes()) for p in files},
        historicalControlWarmupSeconds=10, newWarmupSeconds=5, timingCausalComparisonAccepted=False,
        certificateUnknownBranchObserved=False, all48RawInputsObserved=False, sameFrameProven=False,
        drawIssuedProven=False, fragmentFetchProven=False, physicalAccepted=False, visualAccepted=False,
        motionAccepted=False, nativePixelAAAccepted=False, FPSFloorAccepted=False, shippingAccepted=False,
        scope='Saved900p warmed near only. Selected field bit identity and counts/first-target evidence; separate guard/stage/FINAL/PNG captures, not simultaneous draw or all48 raw node proof. Unknown certificate branch is unexercised; no natural-world, appearance, FPS-floor or shipping adoption.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    parser.add_argument('--role', choices=('reasons', 'inputs'), default='reasons')
    args = parser.parse_args()
    print(json.dumps(audit(args.packet, args.role), indent=2, sort_keys=True, allow_nan=False))
