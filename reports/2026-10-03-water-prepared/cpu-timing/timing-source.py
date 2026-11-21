#!/usr/bin/env python3
"""Read-only isolated native water-draw timing summary; no GL or FPS estimate."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import statistics
import struct
import sys

FIXTURES = (
    'central2-cachezero-guard0', 'central2-cachezero-guard1',
    'central2-cachepositive-guard0', 'central2-cachepositive-guard1',
    'wide60-cachepositive-guard1', 'wide90-cachepositive-guard1')
MODES = ('old', 'prepared')
ABBA = ('old', 'prepared', 'prepared', 'old')
HEADER = ['fixture', 'stage', 'cycle', 'position', 'variant', 'elapsed_ns']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _integer(value, low, high, message):
    require(type(value) is int and low <= value <= high, message)
    return value


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def _read(root, name, limit=16 * 1024 * 1024):
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts,
            'packet-relative path required')
    path = root / relative
    require(path.is_file() and not path.is_symlink()
            and path.resolve().is_relative_to(root.resolve()), 'regular contained file required: ' + name)
    require(0 < path.stat().st_size <= limit, 'bounded nonempty file required: ' + name)
    return path.read_bytes()


def _json(root, name):
    return json.loads(_read(root, name), object_pairs_hook=_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON: ' + value)))


def _summary(values):
    return {'median_ms': statistics.median(values) / 1e6,
            'min_ms': min(values) / 1e6, 'max_ms': max(values) / 1e6,
            'population_stdev_ms': statistics.pstdev(values) / 1e6,
            'median_absolute_deviation_ms':
                statistics.median(abs(value - statistics.median(values)) for value in values) / 1e6}


def _sources(root, result):
    raw = _read(root, 'source-manifest.json')
    require(sha(raw) == result['source_manifest_sha256'], 'source manifest hash differs')
    manifest = _json(root, 'source-manifest.json')
    require(manifest['schema'] == 'aqualumen-prepared-main-source-v1', 'source manifest schema differs')
    names = set()
    hashes = {}
    for item in manifest['sources']:
        name = item['file']
        require(type(name) is str and name not in names, 'unique source names required')
        names.add(name)
        source = _read(root, name)
        require(type(item['bytes']) is int and item['bytes'] == len(source)
                and item['sha256'] == sha(source), 'source content/hash differs: ' + name)
        hashes[name] = item['sha256']
    return hashes


def _matrix_bits(matrices):
    require(type(matrices) is dict and matrices, 'actual matrix values required')
    result = {}
    for name, values in matrices.items():
        require(type(values) is list and len(values) == 16 and
                all(type(value) in (int, float) and math.isfinite(value) for value in values),
                'finite mat4 values required')
        result[name] = struct.pack('<16f', *values)
    return result


def _input_evidence(root, sources):
    inputs = _json(root, 'draw-timer-inputs.json')
    require(type(inputs) is list and [item['fixture'] for item in inputs] == list(FIXTURES),
            'six ordered timer input records required')
    evidence = {}
    for item in inputs:
        fixture = item['fixture']
        entries = item['actual_inputs']
        queried = item['queried_program_sources']
        require(type(entries) is list and [entry['variant'] for entry in entries] == list(MODES)
                and type(queried) is list and len(queried) == 2, 'paired timer inputs/sources required')
        matrix_reference, payload_reference = None, None
        for mode, entry, query in zip(MODES, entries, queried):
            name = fixture + '/timer-' + mode + '-actual-inputs/actual-inputs.json'
            require(entry['receipt'] == name, 'canonical timer receipt path required')
            require(sha(_read(root, name)) == entry['receipt_sha256'], 'actual input receipt hash differs')
            receipt = _json(root, name)
            require(receipt['schema'] == 'aqualumen-native-residual-sun-inputs-v1', 'actual input schema differs')
            program = _integer(receipt['program'], 1, 2 ** 32 - 1, 'receipt program integer required')
            for key in ('currentProgramBefore', 'currentProgramAfter'):
                require(type(receipt[key]) is int and receipt[key] == program, 'receipt current program differs')
            require(receipt['stateRestored'] is True, 'receipt state restoration required')
            for before, after in [('activeTextureBefore', 'activeTextureAfter'),
                                  ('textureBindingBefore', 'textureBindingAfter')]:
                require(type(receipt[before]) is int and type(receipt[after]) is int
                        and receipt[before] == receipt[after], 'receipt texture query state differs')
            matrices = _matrix_bits(receipt['matrices'])
            if matrix_reference is not None:
                require(matrices == matrix_reference, 'old/prepared actual matrix bits differ')
            matrix_reference = matrices
            samplers = receipt['samplers']
            require(type(samplers) is list and len(samplers) == 8, 'eight actual input maps required')
            payload = b''
            for unit, sampler in enumerate(samplers):
                require(type(sampler['unit']) is int and sampler['unit'] == unit, 'sampler unit order differs')
                w = _integer(sampler['width'], 1, 257, 'bounded input width required')
                h = _integer(sampler['height'], 1, 257, 'bounded input height required')
                components = _integer(sampler['components'], 1, 4, 'input component count required')
                filename = sampler['file']
                require(type(filename) is str and Path(filename).name == filename,
                        'receipt-local input basename required')
                raw = _read(root, str(Path(name).parent / filename))
                require(len(raw) == w * h * components * 4 and
                        all(math.isfinite(value[0]) for value in struct.iter_unpack('<f', raw)),
                        'finite actual input map with exact byte count required')
                payload += raw
            payload_sha = sha(payload)
            require(payload_sha == entry['texture_payload_sha256'], 'actual input payload hash differs')
            if payload_reference is not None:
                require(payload == payload_reference, 'old/prepared actual texture bits differ')
            payload_reference = payload
            guard = _json(root, str(Path(name).parent / 'timer-guard.json'))
            require(guard['schema'] == 'aqualumen-native-sun-iris-guard-input-v1'
                    and guard['name'] == 'aqualumenSunTestAuthorized'
                    and type(guard['type']) is int and guard['type'] == 5124
                    and type(guard['size']) is int and guard['size'] == 1
                    and type(guard['value']) is int and guard['value'] == int(fixture.endswith('guard1')),
                    'typed actual input authorization differs')
            for key in ('program', 'currentProgramBefore', 'currentProgramAfter'):
                require(type(guard[key]) is int and guard[key] == program, 'actual guard program differs')
            require(type(query['program']) is int and query['program'] == program
                    and type(query['currentProgramBefore']) is int
                    and type(query['currentProgramAfter']) is int
                    and query['currentProgramBefore'] == query['currentProgramAfter'],
                    'attached source query program/restoration differs')
            stages = query['stages']
            require(type(stages) is list and len(stages) == 4
                    and all(type(stage['type']) is int for stage in stages)
                    and {stage['type'] for stage in stages} == {35633, 36488, 36487, 35632},
                    'four unique actual attached stages required')
            stage_files = {35633: 'geometry-stage0.glsl', 36488: 'geometry-stage1.glsl',
                           36487: 'geometry-stage2.glsl', 35632: mode + '-physical-expanded.fsh'}
            for stage in stages:
                file = stage_files[stage['type']]
                require(stage['sha256'] == sources[file] and type(stage['bytes']) is int
                        and stage['bytes'] == len(_read(root, file)), 'attached stage source/hash differs')
            evidence[fixture, mode] = {'program': program, 'receipt': entry['receipt_sha256'],
                                       'payload': payload_sha}
    return evidence


def _state_identity(state, fixture, mode, timer, physical, programs):
    program = _integer(state['program'], 1, 2 ** 32 - 1, 'actual program integer required')
    for key in ('currentProgramBefore', 'currentProgramAfter'):
        require(type(state[key]) is int and state[key] == program, 'actual current program differs')
    if mode in programs:
        require(programs[mode] == program, 'physical program changed within variant')
    else:
        require(program not in programs.values(), 'old/prepared programs must be distinct')
        programs[mode] = program
    _integer(state['framebuffer'], 1, 2 ** 32 - 1, 'actual framebuffer required')
    _integer(state['VAO'], 0, 2 ** 32 - 1, 'actual VAO integer required')
    require(state['stateUnchanged'] is True and type(state['patchVertices']) is int
            and state['patchVertices'] == 3, 'unchanged patch/draw state required')
    for name, expected in [('viewport', [0, 0, 257, 257]),
                           ('drawBuffers', [36064, 36065, 36066, 36067, 36068, 0, 0, 0])]:
        require(type(state[name]) is list and all(type(value) is int for value in state[name])
                and state[name] == expected, 'actual physical ' + name + ' differs')
    require(type(state['counterBits']) is int and state['counterBits'] == timer['counterBits'],
            'query counter bits differs')
    guard = state['guard']
    require(guard['name'] == 'aqualumenSunTestAuthorized' and type(guard['type']) is int
            and guard['type'] == 5124 and type(guard['size']) is int and guard['size'] == 1,
            'active scalar GL_INT authorization required')
    _integer(guard['location'], 0, 2 ** 31 - 1, 'guard location required')
    for name in ('actualBefore', 'actualAfter'):
        require(type(guard[name]) is int and guard[name] == int(fixture.endswith('guard1')),
                'actual before/after fixture authorization differs')
    require(state['queried_fragment_source_sha256'] == physical[mode],
            'actual queried physical source hash differs')


def audit(output):
    """Validate saved timer ordering/identity and summarize measured draws only."""
    root = Path(output)
    result = _json(root, 'result.json')
    require(result['schema'] == 'aqualumen-prepared-main-native-v1', 'native-main schema differs')
    for name in ('nativeGLExecuted', 'accepted', 'main_fixture_qualified', 'main_differential_accepted'):
        require(result[name] is True, 'completed main gate required: ' + name)
    require(result['status'] == 'PASS'
            and 'RTX 3080 Ti' in result['renderer'] and 'NVIDIA' in result['vendor'],
            'completed NVIDIA RTX3080Ti result required')
    synthetic = result.get('syntheticOnly', False)
    require(type(synthetic) is bool, 'synthetic marker must be bool')
    timer = result['timer']
    require(timer['executed'] is True and timer['query'] == 'GL_TIME_ELAPSED'
            and timer['alternation'] == 'ABBA old/prepared/prepared/old'
            and timer['Minecraft_FPS'] is False, 'isolated draw timer contract differs')
    warmup = _integer(timer['warmup_cycles'], 1, 4, 'bounded warmup cycles required')
    measured = _integer(timer['measurement_cycles'], 1, 12, 'bounded measured cycles required')
    _integer(timer['counterBits'], 1, 64, 'counter bits required')
    require(type(timer['samples_per_variant_per_fixture']) is int
            and timer['samples_per_variant_per_fixture'] == 2 * measured, 'sample count differs')
    require(timer['raw_integer_ns_file'] == 'draw-timer.csv'
            and timer['state_file'] == 'draw-timer-state.json', 'canonical timer files required')
    require([case['path'] for case in result['cases']] == list(FIXTURES),
            'six exact fixture order required')
    for case in result['cases']:
        require(case['qualified'] is True and case['accepted'] is True, 'case gate required')
        require(type(case['guard']) is int and case['guard'] == int(case['path'].endswith('guard1'))
                and case['positive_cache'] is ('cachepositive' in case['path'])
                and type(case['aperture_degrees']) is int
                and case['aperture_degrees'] == (90 if case['path'].startswith('wide90') else
                                                60 if case['path'].startswith('wide60') else 2),
                'fixed fixture inputs differ')
    sources = _sources(root, result)
    physical = {mode: sources[mode + '-physical-expanded.fsh'] for mode in MODES}
    input_evidence = _input_evidence(root, sources)
    programs = {}
    raw_csv = _read(root, 'draw-timer.csv')
    raw_state = _read(root, 'draw-timer-state.json')
    require(sha(raw_csv) == timer['raw_csv_sha256']
            and sha(raw_state) == timer['state_sha256'], 'CSV/state hash differs')
    reader = csv.DictReader(io.StringIO(raw_csv.decode('utf-8'), newline=''))
    require(reader.fieldnames == HEADER, 'canonical CSV header required')
    rows = list(reader)
    states = _json(root, 'draw-timer-state.json')
    require(type(states) is list and len(rows) == len(states) == 24 * (warmup + measured),
            'exact chronological row/state count required')
    expected = [(fixture, stage, cycle, position, mode)
                for fixture in FIXTURES
                for stage, cycles in [('warmup', warmup), ('measured', measured)]
                for cycle in range(cycles) for position, mode in enumerate(ABBA)]
    values = {fixture: {mode: [] for mode in MODES} for fixture in FIXTURES}
    cycles = {fixture: [{mode: [] for mode in MODES} for _ in range(measured)]
              for fixture in FIXTURES}
    for row, state, identity in zip(rows, states, expected):
        require(set(row) == set(HEADER) and None not in row.values(), 'CSV arity differs')
        for key in ('cycle', 'position', 'elapsed_ns'):
            require(re.fullmatch(r'0|[1-9][0-9]*', row[key]) is not None, 'canonical CSV integer required')
        fixture, stage, cycle, position, mode = identity
        require((row['fixture'], row['stage'], int(row['cycle']), int(row['position']), row['variant'])
                == identity, 'strict chronological ABBA row differs')
        ns = _integer(int(row['elapsed_ns']), 1, 60000000000, 'elapsed ns outside declared range')
        require(type(state['elapsed_ns']) is int and state['elapsed_ns'] == ns,
                'chronological state elapsed ns differs')
        _state_identity(state, fixture, mode, timer, physical, programs)
        inputs = input_evidence[fixture, mode]
        require(state['program'] == inputs['program']
                and state['actual_input_receipt_sha256'] == inputs['receipt']
                and state['actual_texture_payload_sha256'] == inputs['payload'],
                'chronological draw input/program receipt differs')
        if stage == 'measured':
            values[fixture][mode].append(ns)
            cycles[fixture][cycle][mode].append(ns)
    fixtures = []
    for fixture in FIXTURES:
        ratios = [statistics.mean(cycle['prepared']) / statistics.mean(cycle['old'])
                  for cycle in cycles[fixture]]
        old, prepared = values[fixture]['old'], values[fixture]['prepared']
        fixtures.append({'fixture': fixture, 'measured_samples_per_variant': len(old),
                         'warmup_samples_per_variant_excluded': 2 * warmup,
                         'old': _summary(old), 'prepared': _summary(prepared),
                         'prepared_over_old_median_ratio': statistics.median(prepared) / statistics.median(old),
                         'paired_cycle_prepared_over_old_ratios': ratios,
                         'paired_cycle_ratio_median': statistics.median(ratios),
                         'paired_cycle_ratio_min': min(ratios), 'paired_cycle_ratio_max': max(ratios),
                         'paired_cycle_ratio_population_stdev': statistics.pstdev(ratios)})
    return {'schema': 'aqualumen-prepared-native-timing-summary-v1',
            'timingEvidenceQualified': True, 'syntheticOnly': synthetic,
            'nativeTimerQualified': not synthetic, 'GLExecutedByAuditor': False,
            'resultSHA256': sha(_read(root, 'result.json')),
            'csvSHA256': sha(raw_csv), 'stateSHA256': sha(raw_state),
            'timerInputsSHA256': sha(_read(root, 'draw-timer-inputs.json')),
            'sourceManifestSHA256': result['source_manifest_sha256'],
            'fixtures': fixtures, 'ratioDefinition': 'prepared / old; below 1 is lower draw time',
            'pairing': 'arithmetic mean of two B draws / two A draws within each measured ABBA cycle',
            'MinecraftFPS': False, 'universalSpeedupAccepted': False,
            'physicalAccepted': False, 'visualAccepted': False, 'shippingAccepted': False,
            'scope': 'Saved isolated native water-draw evidence only; no significance test, universal speedup, GPU re-execution or Minecraft FPS inference.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(audit(args.output), indent=2, allow_nan=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError, UnicodeError, csv.Error, struct.error, OverflowError) as error:
        print(json.dumps({'schema': 'aqualumen-prepared-native-timing-summary-v1',
                          'status': 'INCONCLUSIVE', 'timingEvidenceQualified': False,
                          'error': str(error), 'GLExecutedByAuditor': False,
                          'MinecraftFPS': False, 'universalSpeedupAccepted': False,
                          'physicalAccepted': False, 'visualAccepted': False,
                          'shippingAccepted': False}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
