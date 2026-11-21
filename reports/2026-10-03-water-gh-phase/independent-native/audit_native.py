"""Read-only saved native audit; no GL, game, imports of the probe, or writes."""
from array import array
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import struct
import sys
from zipfile import ZipFile

BASE = Path(__file__).resolve().parents[1]
NATIVE = BASE / 'native'
SIZE = 257
PIXELS = SIZE * SIZE
ROLES = ('parent', 'phase0-physical', 'phase0-observer', 'phase45-physical', 'phase45-observer')
CASES = ('central2-cachezero-guard0', 'central2-cachezero-guard1',
         'central2-cachepositive-guard0', 'central2-cachepositive-guard1',
         'wide60-cachepositive-guard1', 'wide90-cachepositive-guard1')
HASHES = {}


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    demand(path.is_file() and not path.is_symlink(), 'Missing/nonregular saved input: ' + str(path.name))
    raw = path.read_bytes()
    name = str(path.relative_to(BASE))
    digest = sha256(raw).hexdigest()
    demand(name not in HASHES or HASHES[name] == digest, 'Saved input changed during audit: ' + name)
    HASHES[name] = digest
    return raw


def parsed(path):
    return json.loads(read(path))


def floats(path, count):
    raw = read(path)
    demand(len(raw) == count * 4, 'Raw length mismatch: ' + path.name)
    values = memoryview(raw).cast('f')
    demand(all(math.isfinite(x) for x in values), 'Nonfinite raw values: ' + path.name)
    return raw


def whole(value, maximum):
    return math.isfinite(value) and 0 <= value <= maximum and value == math.floor(value)


def stage(values):
    return (abs(values[3] - 1) <= 8 * 2**-23 and abs(sum(values[:3]) - 1) <= 2e-5
            and all(-2e-5 <= x <= 1 + 2e-5 for x in values[:3]))


def accounted(v, guard, positive):
    why, status, main, tes, full, base, copy = (v[i:i+4] for i in range(4, 32, 4))
    if tes[3] == 0:
        return all(x == 0 for x in v[4:])
    if not stage(tes) or v[3] != 1 or struct.pack('<3f', *v[:3]) != struct.pack('<3f', *copy[:3]):
        return False
    if not whole(main[0], 15) or not 0 <= main[1] <= 1 or not whole(main[2], 2) or copy[3] != guard:
        return False
    eligible = bool(int(main[0]) & 8)
    request = int(bool(guard) and eligible)
    if status[0] != request or not whole(status[1], 1) or not whole(status[3], 48) or not whole(status[2], 16777215):
        return False
    word = int(status[2])
    counts = [(word >> (6*i)) & 63 for i in range(4)]
    if any(x > 48 for x in counts) or sum(counts[:3]) != counts[3]:
        return False
    if status[1] == 1 and (counts[3] != 48 or counts[2] != 0 or status[3] != 0):
        return False
    if status[1] == 0 and counts[2] > 0 and status[3] <= 0:
        return False
    for wr in (full, base):
        if not guard:
            if any(wr):
                return False
        elif (not whole(wr[0], 1) or not whole(wr[1], 1) or not whole(wr[3], 18)
              or wr[1] != int(eligible and wr[0] == 1)):
            return False
    if not request:
        return not any(why) and not any(status)
    if not whole(why[0], 9) or not all(whole(x, 48) for x in why[1:]):
        return False
    total = sum(why[1:])
    if total > 48:
        return False
    zero = why[0] == 0 and total == 0
    if not positive:
        reasons_ok = zero and status[1] == 0 and status[3] == 0
    elif status[1] == 1:
        reasons_ok = zero and status[3] == 0
    elif total == 0:
        reasons_ok = zero and status[3] in (0, 1)
    else:
        first = int(why[0])
        appropriate = why[1] > 0 if first in (3, 9) else why[2] > 0 if first in (6, 7) else why[3] > 0
        reasons_ok = total == status[3] and first != 0 and appropriate
    return (reasons_ok and (positive or status[2] == 0) and counts[2] <= status[3]
            and counts[2] <= why[3] and total <= 48 - counts[0])


def input_audit(directory, role, guard, reference, programs):
    folder = directory / (role + '-actual-inputs')
    state = parsed(folder / 'actual-draw-state.json')
    j = parsed(folder / 'actual-inputs.json')
    program = programs[role]
    demand(state['program'] == program == j['program'] == j['currentProgramBefore'] == j['currentProgramAfter'], 'Actual program identity mismatch')
    demand(state['viewport'] == [0, 0, SIZE, SIZE] and state['patch_vertices'] == 3 and not state['blend'] and not state['culling'], 'Actual draw state mismatch')
    demand(j['stateRestored'] and j['activeTextureBefore'] == j['activeTextureAfter'] and j['textureBindingBefore'] == j['textureBindingAfter'], 'Input-query state mismatch')
    demand(len(j['targets']) == 8 and j['depth']['internalFormat'] == 36012 and j['depth']['width'] == SIZE and j['depth']['height'] == SIZE, 'Target storage mismatch')
    for i, target in enumerate(j['targets']):
        demand(target['slot'] == i and target['internalFormat'] == 34836 and target['width'] == SIZE and target['height'] == SIZE, 'Actual RGBA32F storage mismatch')
        route = state['actual_draw_routes'][i]
        active = i < (8 if role.endswith('observer') else 5)
        demand(route == {'slot': i, 'route': 36064+i if active else 0, 'object_type': 5890, 'texture': target['texture']}, 'Draw route/object mismatch')
    for suffix in (role + '-guard.json', role + '-repeat-guard.json'):
        g = parsed(directory / suffix)
        demand(g['program'] == program == g['currentProgramBefore'] == g['currentProgramAfter'] and g['type'] == 5124 and g['size'] == 1 and g['value'] == guard, 'Actual draw guard mismatch')
    g = parsed(folder / 'actual-inputs-guard.json')
    demand(g['program'] == program == g['currentProgramBefore'] == g['currentProgramAfter'] and g['type'] == 5124 and g['size'] == 1 and g['value'] == guard, 'Actual input guard mismatch')
    uniform = {x['name']: x for x in j['uniforms']}
    expected = {'sunPosition': (35665, [0, 0, -1]), 'rainStrength': (5126, [0]),
                'viewWidth': (5126, [SIZE]), 'viewHeight': (5126, [SIZE]),
                'isEyeInWater': (5124, [1]), 'aqualumenDimension': (5124, [0])}
    demand(set(uniform) == set(expected), 'Typed scalar names mismatch')
    for name, (kind, value) in expected.items():
        demand(uniform[name]['type'] == kind and uniform[name]['size'] == 1 and uniform[name]['values'] == value, 'Typed scalar mismatch: ' + name)
    demand(set(j['matrices']) == {'gbufferProjection', 'gbufferProjectionInverse', 'gbufferModelView', 'gbufferModelViewInverse'}, 'Matrix set mismatch')
    demand(all(len(x) == 16 and all(math.isfinite(v) for v in x) for x in j['matrices'].values()), 'Matrix shape/finiteness mismatch')
    demand(j['fixedFunctionProjection'] == j['matrices']['gbufferProjection'] and j['fixedFunctionModelView'] == j['matrices']['gbufferModelView'], 'Fixed-function matrix mismatch')
    demand(j['sunDirectionDerivedFromActualUniforms'] == [0, 1, 0], 'Recorded Sun basis mismatch')
    names = ('gtexture', 'colortex4', 'colortex6', 'depthtex1', 'shadowtex0', 'colortex8', 'aqualumenBathymetry', 'colortex7')
    widths, heights = (1, SIZE, 64, SIZE, 1, 1, 64, 64), (1, SIZE, 32, SIZE, 1, 1, 64, 32)
    actual = []
    demand(len(j['samplers']) == 8, 'Sampler count mismatch')
    for unit, s in enumerate(j['samplers']):
        components = 1 if unit in (3, 4) else 4
        fmt = 36012 if components == 1 else 34842 if unit == 5 else 34836
        demand(s['unit'] == unit == s['uniformUnit'] and s['name'] == names[unit] and s['uniformSize'] == 1 and s['uniformType'] == (35682 if unit == 4 else 35678), 'Typed sampler mismatch')
        demand(s['sampler'] == 0 and s['internalFormat'] == fmt and s['width'] == widths[unit] and s['height'] == heights[unit] and s['components'] == components and s['minFilter'] == s['magFilter'] == 9728, 'Sampler storage/filter mismatch')
        demand(s['file'] == f'input-sampler{unit}' + ('.f32' if components == 1 else '.rgba32f'), 'Sampler filename mismatch')
        actual.append(floats(folder / s['file'], widths[unit]*heights[unit]*components))
    if reference:
        demand(actual == reference[0] and j['matrices'] == reference[1] and state['framebuffer'] == reference[2], 'Inputs differ across roles/phases')
    return actual, j['matrices'], state['framebuffer']


def audit():
    demand(sys.byteorder == 'little' and array('f').itemsize == 4, 'Little-endian binary32 host required')
    report = parsed(NATIVE / 'result.json')
    demand(report['schema'] == 'aqualumen-gh-phase-native-v1' and report['size'] == SIZE and report['case_count'] == 6, 'Native report schema mismatch')
    demand(report['nativeGLExecuted'] and 'RTX 3080 Ti' in report['renderer'] and 'NVIDIA' in report['vendor'], 'Recorded native renderer mismatch')
    demand([x['path'] for x in report['cases']] == list(CASES), 'Frozen case ordering mismatch')
    demand(sha256(read(NATIVE / 'probe-source.cpp')).hexdigest() == report['probe_source_sha256'], 'Native source identity mismatch')
    demand(sha256(read(BASE / 'runtime/root-water-gh-phase-probe')).hexdigest() == report['executable_sha256'], 'Executed binary identity mismatch')
    demand(report['parent_pack_sha256'] == 'b0fe0a7badf12a97b707b013de581c71dcc3c6e6d3d52a56bd187d4976a6b452', 'Parent pack identity mismatch')
    stage_files = {35633: 'geometry-stage0.glsl', 36488: 'geometry-stage1.glsl', 36487: 'geometry-stage2.glsl'}
    source = {name: read(NATIVE / (name + '-expanded.fsh')) for name in ROLES}
    demand(sha256(source['parent']).hexdigest() == 'cbf8b6b9e631b804014d09b642126e828fee81610015b13b6ebe03837b59a09f', 'Pinned original parent closure mismatch')
    geometry = {kind: read(NATIVE / name) for kind, name in stage_files.items()}
    zip_pins = {0: '04b9e74db4d34d505ae3e385568cd6b720568c16df0f66809f2e664f975cfda8',
                45: '088866e780d0d86fd8b787dfd18e617a516658246b57f5fe962b2871b45ae88d'}
    for phase in (0, 45):
        packed = read(BASE / f'cpu-pack/Aqualumen-ShoreProbe-world-gh-phase-{phase}-diagnostic-v1.zip')
        demand(sha256(packed).hexdigest() == zip_pins[phase], 'Frozen diagnostic ZIP identity mismatch')
        with ZipFile(BytesIO(packed)) as z:
            demand(source[f'phase{phase}-physical'] == z.read('GH-PHASE-physical-expanded.fsh') and source[f'phase{phase}-observer'] == z.read('GH-PHASE-observed-expanded.fsh'), 'Frozen pack/native source mismatch')
            for index, kind in enumerate(stage_files):
                demand(geometry[kind] == z.read(f'GH-PHASE-geometry-stage{index}.glsl'), 'Frozen geometry mismatch')
    rows, total_comparisons = [], 0
    for case in report['cases']:
        directory = NATIVE / case['path']
        programs = {}
        expected_groups = (ROLES[1:3], ROLES[3:5], ROLES[:2])
        demand(len(case['queried_program_sources']) == 3, 'Exact source-query group count required')
        for group, labels in zip(case['queried_program_sources'], expected_groups):
            demand(len(group) == 2, 'Source-query group shape mismatch')
            for q, label in zip(group, labels):
                if label in programs:
                    demand(programs[label] == q['program'], 'Source-query repeated program mismatch')
                programs[label] = q['program']
                demand(q['currentProgramBefore'] == q['currentProgramAfter'], 'Source-query state changed')
                expected_sources = {**geometry, 35632: source[label]}
                demand(len(q['stages']) == 4 and {s['type'] for s in q['stages']} == set(expected_sources), 'Four actual stages mismatch')
                for s in q['stages']:
                    demand(s['bytes'] == len(expected_sources[s['type']]) and s['sha256'] == sha256(expected_sources[s['type']]).hexdigest(), 'Queried compiler source mismatch')
        frames, reference = {}, None
        comparisons = {c['label']: c for c in case['comparisons']}
        demand(len(case['comparisons']) == len(comparisons) == 61, 'Comparison labels/count malformed')
        seen = set()

        def compare(label, a, b):
            nonlocal total_comparisons
            demand(a == b, 'Strict bytes mismatch: ' + case['path'] + '/' + label)
            demand(label in comparisons and label not in seen, 'Missing/duplicate comparison label')
            c = comparisons[label]
            demand(c['elements'] == len(a)//4 and c['mismatching_words'] == 0 and c['max_absolute_delta'] == 0 and c['absolute_policy'] == c['relative_policy'] == 0 and c['signed_zero_bits_compared'] and c['accepted'], 'Saved strict comparison mismatch')
            demand(c['a_sha256'] == sha256(a).hexdigest() and c['b_sha256'] == sha256(b).hexdigest(), 'Saved comparison digest mismatch')
            seen.add(label)
            total_comparisons += 1

        for role in ROLES:
            regular = [floats(directory / f'{role}-slot{s}.rgba32f', PIXELS*4) for s in range(8)]
            repeated = [floats(directory / f'{role}-repeat-slot{s}.rgba32f', PIXELS*4) for s in range(8)]
            depth = floats(directory / f'{role}-depth.f32', PIXELS)
            repeated_depth = floats(directory / f'{role}-repeat-depth.f32', PIXELS)
            for s in range(8):
                compare(f'{role}-slot{s}-repeat', regular[s], repeated[s])
            compare(role + '-depth-repeat', depth, repeated_depth)
            frames[role] = (regular, depth)
            reference = input_audit(directory, role, case['guard'], reference, programs)
        for s in range(5):
            compare(f'parent-phase0-physical-slot{s}-exact', frames[ROLES[0]][0][s], frames[ROLES[1]][0][s])
        compare('parent-phase0-physical-depth-exact', frames[ROLES[0]][1], frames[ROLES[1]][1])
        for phase in (0, 45):
            physical, observer = frames[f'phase{phase}-physical'], frames[f'phase{phase}-observer']
            for field, slot in (('C0', 0), ('TES', 4)):
                compare(f'phase{phase}-observer-{field}-passive-exact', physical[0][slot], observer[0][slot])
            compare(f'phase{phase}-observer-depth-passive-exact', physical[1], observer[1])
            def rgb(raw):
                return b''.join(raw[p:p+12] for p in range(0, len(raw), 16))
            compare(f'phase{phase}-same-draw-C15-C0-RGB-exact', rgb(observer[0][0]), rgb(observer[0][7]))
        compare('crossphase-physical-depth-exact', frames[ROLES[1]][1], frames[ROLES[3]][1])
        compare('crossphase-physical-TES-exact', frames[ROLES[1]][0][4], frames[ROLES[3]][0][4])
        demand(seen == set(comparisons) and len(seen) == 61, 'Comparison table coverage mismatch')
        observed = [[memoryview(raw).cast('f') for raw in frames[role][0]] for role in (ROLES[2], ROLES[4])]
        measures = {k: [0, 0] for k in ('stage_water_points', 'accounted_points', 'central_input_domain_points', 'full_WR_valid_points', 'full_WR_applied_points', 'base_WR_valid_points', 'base_WR_applied_points', 'Sun_applied_points')}
        changes, overlaps, sun_changes, color_changes, same_max, changed_max = [0]*4, [0]*4, 0, 0, 0.0, 0.0
        masks, first_changed, phase0_application = array('I'), [], True
        for pixel in range(PIXELS):
            p = pixel*4
            values = [[s[p+c] for s in mode for c in range(4)] for mode in observed]
            x, y = pixel % SIZE, pixel // SIZE
            for mode, v in enumerate(values):
                water = v[19] > 0
                valid = accounted(v, case['guard'], case['positive_cache'])
                measures['stage_water_points'][mode] += water
                measures['accounted_points'][mode] += valid
                if water:
                    for key, index in (('full_WR_valid_points', 20), ('full_WR_applied_points', 21), ('base_WR_valid_points', 24), ('base_WR_applied_points', 25), ('Sun_applied_points', 9)):
                        measures[key][mode] += v[index] == 1
                if case['central_acceptance_case'] and (x-128)**2 + (y-128)**2 <= 1600:
                    measures['central_input_domain_points'][mode] += water and stage(v[16:20]) and v[3] == 1 and v[12] == 15 and v[31] == case['guard'] and valid
                    if mode == 0:
                        phase0_application &= (v[8] == case['guard'] and v[9] == int(case['guard'] and case['positive_cache']) and v[11] == 0 and (not case['guard'] or all(v[i] == 1 for i in (20, 21, 24, 25))))
            mask = 0
            for i, index in enumerate((20, 21, 24, 25)):
                if values[0][index] != values[1][index]:
                    mask |= 1 << i
                    changes[i] += 1
            if values[0][8] != values[1][8]:
                mask |= 16
            if values[0][9] != values[1][9]:
                mask |= 32
                sun_changes += 1
            changed = frames[ROLES[2]][0][0][p*4:p*4+12] != frames[ROLES[4]][0][0][p*4:p*4+12]
            delta = max(abs(values[0][c] - values[1][c]) for c in range(3))
            if changed:
                mask |= 64
                color_changes += 1
                overlaps = [n + bool(mask & (1 << i)) for i, n in enumerate(overlaps)]
                if len(first_changed) < 8:
                    first_changed.append([x, y, delta])
            if mask & 15:
                changed_max = max(changed_max, delta)
            else:
                same_max = max(same_max, delta)
            masks.append(mask)
        recomputed = {**measures, 'changed_WR_xy_counts_fullValid_fullApplied_baseValid_baseApplied': changes,
                      'color_changed_points_with_each_WR_xy_change': overlaps, 'changed_Sun_applied_points': sun_changes,
                      'color_changed_points': color_changes, 'C0_RGB_max_delta_same_WR_xy': same_max,
                      'C0_RGB_max_delta_changed_WR_xy': changed_max}
        for key, value in recomputed.items():
            demand(case[key] == value, 'Raw measure/report mismatch: ' + case['path'] + '/' + key)
        demand(measures['accounted_points'] == [PIXELS, PIXELS], 'Raw point qualification failure')
        if case['central_acceptance_case']:
            demand(measures['central_input_domain_points'] == [5025, 5025] and phase0_application and case['phase0_original_central_application_gate'], 'Original central gate failure')
        else:
            demand(case['phase0_original_central_application_gate'] is None, 'Unexpected wide application gate')
        raw_mask = masks.tobytes()
        demand(case['cross_phase_mask_file'] == 'cross-phase-admission-mask.u32' and read(directory / case['cross_phase_mask_file']) == raw_mask and case['cross_phase_mask_sha256'] == sha256(raw_mask).hexdigest(), 'Crossphase mask bytes/order/hash mismatch')
        demand([s['pixel'] for s in case['fixed_six_samples']] == [[128, 128], [132, 131], [123, 127], [132, 135], [132, 127], [142, 134]], 'Frozen sample ordering mismatch')
        for sample in case['fixed_six_samples']:
            x, y = sample['pixel']
            p = (y*SIZE+x)*4
            for mode in range(2):
                demand(sample['phase_records'][mode] == [s[p+c] for s in observed[mode] for c in range(4)], 'Fixed sample/raw mismatch')
        rows.append({'case': case['path'], 'all61_strict_comparisons': True, **recomputed,
                     'mask_sha256': sha256(raw_mask).hexdigest(), 'first_eight_color_changed_points': first_changed})
    demand(report['status'] == 'PASS' and report['accepted'] and report['fixture_qualified'], 'Saved final status mismatch')
    ledger = ''.join(digest + '  ' + name + '\n' for name, digest in sorted(HASHES.items())).encode()
    return {'schema': 'aqualumen-gh-phase-independent-native-v1', 'status': 'PASS_SAVED_NATIVE_QUALIFICATION',
            'reader_GL_executed': False, 'reader_game_or_live_actions': False, 'input_file_count': len(HASHES),
            'input_file_hash_ledger_sha256': sha256(ledger).hexdigest(), 'result_sha256': HASHES['native/result.json'],
            'probe_source_sha256': report['probe_source_sha256'], 'executed_binary_sha256': report['executable_sha256'],
            'renderer_recorded': report['renderer'], 'GL_recorded': report['GL'], 'verified_comparison_count': total_comparisons,
            'cases': rows, 'same_draw_C15_RGB_all_bits_exact': True, 'raw_mask_all_bytes_and_counts_match': True,
            'source_compiler_query_and_input_state_receipts_verified': True, 'reader_source_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
            'limits': ['Native saved fixture source/input/observer qualification only, not a physical quality pass.',
                       'All WR.xy/Sun application changes are zero in these open-black fixtures; no visible-band cause proven.',
                       'Color change counts include signed-zero bits and overlapping admission categories, not disjoint causal classes.',
                       'No Iris allocation/FINAL display, actual cloud scene, same-frame live fragment proof, FPS or promotion claim.']}


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2, sort_keys=True))
