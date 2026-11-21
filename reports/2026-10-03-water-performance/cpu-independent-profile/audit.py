#!/usr/bin/env python3
"""Read-only replay of the first matched control/profile captures; stdout only."""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import report
from test_thin_runtime_audit import read_intervals
import water_sun_profile_build as build

PACK = 'Aqualumen-ShoreProbe-world-sun-support-zero-physical-v1.zip'
SHA = '33164466c3828daa93724d6b9e531fcb66897e300ecd16dc4cfa90ec08c38cda'
SCENES = ['underwater-up-near', 'underwater-up-deep', 'underwater-up-tilt']
WORLD = 'b22dbccb-2970-41e6-847f-f183b1ec923d'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def utc(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))


def context(packet, folder, run):
    start = utc(run['started_utc'])
    end = utc(read(packet / folder / 'complete.json')['utc'])
    prefix = folder.removesuffix('-run')
    file = packet / (prefix + '-gpu-process.txt')
    result = {'gc_names': run['garbage_collectors'], 'heap_initial_bytes': run['jvm_heap_initial_bytes'],
        'heap_max_bytes': run['jvm_heap_max_bytes'], 'scope': 'whole run incl warmup/sample/setup; host timestamps interpreted as JST, not per-scene GPU-stage timing'}
    if file.exists():
        samples = []
        for line in file.read_text().splitlines():
            parts = line.split()
            if len(parts) == 14 and parts[-1] == 'java' and parts[5].isdigit():
                time = dt.datetime.strptime(parts[0] + ' ' + parts[1], '%Y%m%d %H:%M:%S').replace(tzinfo=dt.timezone(dt.timedelta(hours=9)))
                if start <= time <= end:
                    samples.append((int(parts[3]), int(parts[5])))
        assert samples and len({pid for pid, _ in samples}) == 1
        values = [sm for _, sm in samples]
        result['pmon_java'] = {'pid': samples[0][0], 'samples': len(values), 'sm_min': min(values), 'sm_max': max(values),
            'sm_mean': sum(values) / len(values), 'file_sha256': sha(file)}
    return result


def scenes(packet, role, folder):
    directory = packet / folder
    run, complete = read(directory / 'run.json'), read(directory / 'complete.json')
    expected = {'world_id': WORLD, 'seed': 308060, 'world_generator': 'minecraft:noise/overworld',
        'pack_name': PACK, 'pack_sha256': SHA, 'expected_pack_sha256': SHA,
        'resolution': [1600, 900], 'framebuffer_resolution': [1600, 900],
        'expected_resolution': [1600, 900], 'render_chunks': 12, 'simulation_chunks': 6,
        'frame_limit': 120, 'warmup_seconds': 10.0, 'sample_seconds': 10.0, 'scenarios': SCENES}
    assert all(run.get(k) == v for k, v in expected.items())
    assert run['shader_active'] is True and run['shader_fallback'] is False and run['vsync'] is False
    assert Path(run['world_directory']).name == 'AqualumenNaturalV2'
    assert complete['run_id'] == run['run_id'] and complete['status'] == 'complete'
    assert complete['scenarios'] == SCENES and complete['fixture_cleanup_complete'] is True
    assert not (directory / 'aborted.json').exists()
    for name, version in {'aqualumen_benchmark': '0.3.9', 'aqualumen_physics': '0.3.0',
        'aqualumen_water_sun_test': '0.1.0', 'aqualumen_water_stage_probe': '0.1.0',
        'iris': '1.8.8+mc1.21.1', 'sodium': '0.6.9+mc1.21.1'}.items():
        assert run['mods'][name] == version
    assert 'shaderPack=' + PACK in run['iris_configuration'] and 'enableShaders=true' in run['iris_configuration']
    storage = run['iris_render_target_storage']
    assert storage['available'] is True and storage['bindingRestored'] is True
    rows = []
    for scene in SCENES:
        row = read(directory / (scene + '.json'))
        for key in ('world_id', 'pack_name', 'pack_sha256', 'resolution', 'framebuffer_resolution'):
            assert row[key] == run[key]
        assert row['scenario'] == scene and row['run_id'] == run['run_id']
        assert row['window_focused'] is True and row['shader_active'] is True and row['shader_fallback'] is False
        assert row['camera_follows_local_player'] is True and row['camera_lock'] and row['physics_active_seen'] is True
        assert row['player_dimension'] == 'minecraft:overworld' and row['contact_driver'] == 'none'
        assert row['warmup_seconds'] == 10 and row['sample_seconds_requested'] == 10
        assert row['sample_seconds_actual'] >= 9.9
        report.validate_underwater_up(row, scene)
        report.check_png(directory / (scene + '.png'), [1600, 900])
        ns, ms = read_intervals(directory / (scene + '.csv'))
        metrics = report.metrics(ms)
        ordered, slow = sorted(ns), max(1, math.ceil(len(ns) * .01))
        integer_metrics = {'mean_fps': 1e9 * len(ns) / sum(ns),
            'one_percent_low_fps': 1e9 * slow / sum(ordered[-slow:]),
            'p99_ms': ordered[math.ceil(len(ns) * .99) - 1] / 1e6, 'max_ms': max(ns) / 1e6}
        assert all(abs(metrics[k] - v) < 1e-9 for k, v in integer_metrics.items())
        assert all(abs(row[k] - v) <= max(.001, abs(v) * .00001) for k, v in metrics.items())
        assert abs(row['recorded_seconds'] - sum(ns) * 1e-9) < 1e-8
        rows.append({'scene': scene, **metrics, 'raw_integer_ns_sum': sum(ns),
            'sample_seconds_actual': row['sample_seconds_actual'], 'png_sha256': sha(directory / (scene + '.png')),
            'camera_position': row['actual_camera_position'], 'camera_rotation': row['actual_camera_rotation'],
            'actual_eye_depth': row['underwater_up']['actual_eye_depth']})
    guard_file = packet / (folder.removesuffix('-run') + '-guard-after-complete.json')
    if not guard_file.exists():
        assert folder in ('control-repeat-run', 'profile-repeat-run')
        return run, rows
    guard = read(guard_file)
    assert all(guard.get(k) is True for k in ('available', 'readOnly', 'scopeAuthorized',
        'localIntegratedSinglePlayer', 'currentPipelineMatches', 'containsTessellation', 'programAndFrameUnchanged'))
    assert guard['worldId'] == WORLD and guard['packSha256'] == SHA and guard['benchmarkState'] == 'complete'
    assert guard['constructorProgram'] == guard['programBefore'] == guard['programAfter']
    assert guard['frameBefore'] == guard['frameAfter'] and guard['supplierAuthorization'] == 1
    uniform = guard['uniform']
    assert uniform['name'] == 'aqualumenSunTestAuthorized' and uniform['active'] is True and uniform['location'] >= 0
    assert [uniform[k] for k in ('type', 'size', 'value')] == [5124, 1, 1]
    assert utc(guard['capturedUtc']) > utc(complete['utc'])
    return run, rows


def audit(packet, control_folder='control-run', profile_folder='profile-run'):
    assert control_folder in ('control-run', 'control-repeat-run')
    assert profile_folder in ('profile-run', 'profile-repeat-run')
    manifest = read(packet / 'cpu-profile/pair-v1/manifest.json')
    products = {}
    installed = read(Path(__file__).resolve().parent / 'installed-at-audit.json')
    assert installed['schema'] == 'aqualumen-independent-installed-hash-receipt-v1'
    for name, pin in manifest['products'].items():
        first, repeat = (packet / 'cpu-profile' / part / name for part in ('pair-v1', 'pair-repeat-v1'))
        assert sha(first) == sha(repeat) == pin and first.read_bytes() == repeat.read_bytes()
        assert installed['artifacts'][name]['sha256'] == pin
        assert installed['artifacts'][name]['bytes'] == first.stat().st_size
        products[name] = {'sha256': pin, 'repeat_bytes_equal': True, 'live_installed_sha_matches_at_audit': True}
    assert installed['artifacts'][PACK] == {'bytes': 233866, 'sha256': SHA}
    for name, pin in manifest['originalSourcePins'].items():
        original = (packet / 'cpu-profile/pair-v1/parents' / name).read_bytes()
        generated = (packet / 'cpu-profile/pair-v1/sources' / name).read_bytes()
        assert hashlib.sha256(original).hexdigest() == pin
        assert hashlib.sha256(generated).hexdigest() == manifest['generatedSourcePins'][name]
        assert build.recover(name, generated) == original
    assert sha(ROOT / build.HELPER) == manifest['helperSourceSha256']
    runs, output = {}, {}
    folders = {'control': control_folder, 'profile': profile_folder}
    for role, folder in folders.items():
        runs[role], output[role] = scenes(packet, role, folder)
    control = read(packet / control_folder / 'sun-profile.json')
    profile = read(packet / profile_folder / 'sun-profile.json')
    for role, value in [('control', control), ('profile', profile)]:
        assert value['runId'] == runs[role]['run_id'] and value['mode'] == role
        assert value['schema'] == 'aqualumen-sun-profile-v1' and value['metricsAvailable'] is True
        assert value['measurementFailures'] == 0
    assert control['timingsMeasured'] is False and control['rows'] == []
    assert all(control[k] is None for k in ('supplierCalls', 'authorized', 'hashCalls', 'hashBytes', 'fullHashExpressionNs'))
    assert profile['timingsMeasured'] is True
    assert all(profile[k] == 0 for k in ('rejected', 'originalThrows', 'unownedHashCalls', 'unownedHashBytes',
        'unownedFullHashExpressionNs', 'nestedSuppliers'))
    rows = profile['rows']
    assert len(rows) <= profile['maximumRows'] == 4096
    assert all(type(v) is int and v >= 0 for row in rows for k, v in row.items() if k != 'phase')
    assert len({r['supplierId'] for r in rows}) == 1 and rows[0]['supplierId'] <= profile['maximumRegistrationIds'] == 256
    assert all(b['frame'] == a['frame'] + 1 for a, b in zip(rows, rows[1:]))
    assert all(r['calls'] == r['authorized'] == r['hashCalls'] == 1 and r['hashBytes'] == 233866
        and r['rejected'] == r['originalThrows'] == 0 and 0 < r['fullHashExpressionNs'] <= r['totalAuthorizationNs'] for r in rows)
    aliases = {'supplierCalls': 'calls'}
    for key in ('supplierCalls', 'authorized', 'rejected', 'originalThrows', 'hashCalls', 'hashBytes', 'fullHashExpressionNs'):
        assert profile[key] == sum(r[aliases.get(key, key)] for r in rows)
    groups = []
    for row in rows:
        if not groups or groups[-1]['phase'] != row['phase']:
            groups.append({'phase': row['phase'], 'rows': []})
        groups[-1]['rows'].append(row)
    assert [g['phase'] for g in groups] == ['preparing-scene', 'warmup', 'sampling', 'screenshot'] * 3 + ['finishing']
    sampling = [g['rows'] for g in groups if g['phase'] == 'sampling']
    for measured, group in zip(output['profile'], sampling):
        assert len(group) == measured['frames'] + 1
        auth, hashed = (sum(r[key] for r in group) for key in ('totalAuthorizationNs', 'fullHashExpressionNs'))
        measured['profile'] = {'sampling_rows': len(group), 'frame_first': group[0]['frame'], 'frame_last': group[-1]['frame'],
            'total_authorization_ns': auth, 'nested_full_hash_ns': hashed,
            'authorization_mean_us': auth / len(group) / 1000, 'full_hash_mean_us': hashed / len(group) / 1000,
            'after_discarded_start_authorization_frame_share_percent': 100 * (auth - group[0]['totalAuthorizationNs']) / measured['raw_integer_ns_sum'],
            'after_discarded_start_hash_frame_share_percent': 100 * (hashed - group[0]['fullHashExpressionNs']) / measured['raw_integer_ns_sum']}
    for before, after in zip(output['control'], output['profile']):
        assert all(before[k] == after[k] for k in ('camera_position', 'camera_rotation', 'actual_eye_depth'))
    return {'schema': 'aqualumen-independent-sun-profile-audit-v1', 'status': 'PASS', 'products': products,
        'run_folders': folders, 'after_complete_guard_snapshot_available': {role:
            (packet / (folder.removesuffix('-run') + '-guard-after-complete.json')).exists() for role, folder in folders.items()},
        'context': {role: context(packet, folder, runs[role]) for role, folder in folders.items()},
        'source_recovery_files': len(manifest['originalSourcePins']), 'helper_source_sha256': manifest['helperSourceSha256'],
        'pack_sha256': SHA, 'png_integrity_count': 6, 'integer_csv_intervals': sum(r['frames'] for rows in output.values() for r in rows),
        'all_rows': len(rows), 'supplier_id': rows[0]['supplierId'], 'frame_range': [rows[0]['frame'], rows[-1]['frame']],
        'all_row_authorization_ns': sum(r['totalAuthorizationNs'] for r in rows), 'all_row_hash_ns': profile['fullHashExpressionNs'],
        'sampling_rows': sum(len(g) for g in sampling), 'sampling_authorization_ns': sum(r['totalAuthorizationNs'] for g in sampling for r in g),
        'sampling_hash_ns': sum(r['fullHashExpressionNs'] for g in sampling for r in g), 'phases': [{'phase': g['phase'],
            'rows': len(g['rows']), 'frames': [g['rows'][0]['frame'], g['rows'][-1]['frame']]} for g in groups], 'runs': output,
        'limits': ['Authorization includes some wrapper overhead; nested hash is not additive or isolated SHA.',
            'Count-aligned shares discard the first sampling row using Recorder tail semantics; CSV has no Iris-frame timestamp join.',
            'Live hashes are point-in-time verification, not an independent historic-install receipt.',
            'Guard snapshots are after completion, not every-fragment or PNG-same-frame proof.',
            'No optical, visual, isolated GPU-stage, FPS-floor, or shipping acceptance.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control', default='control-run')
    parser.add_argument('--profile', default='profile-run')
    args = parser.parse_args()
    print(json.dumps(audit(Path(__file__).resolve().parent.parent, args.control, args.profile), indent=2, sort_keys=True))
