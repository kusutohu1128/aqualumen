"""Read-only full saved actual-water-main replay; never invokes GL or Minecraft."""
from array import array
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from water_snell_main_runtime import analyze_record, pack_policy, REFERENCE_SHA
from water_snell_main_pack import (INPUT_STORE, REPLACEMENTS, INPUT_BODIES, EXTENSION,
    MANIFEST, HELPER, WATER, NODE, NODE_EXTENSION_GUARD, NODE_SHA, recover_inputs, recover_helper)
from water_residual_sun_reason_pack import STORE, strip_reason_blocks
from water_residual_sun_reason_runtime import qualify_point
from water_residual_sun_iris_runtime import zip_files, json_file

HELPER_PATH = ROOT / 'reports/2026-10-03-water-residual-sun-reasons/cpu-independent-native/audit.py'
HELPER_SHA = 'b804d78c495a73c347379cbcc16a802b97941b8ad43cfc9943c4bac1e0adb362'
SOURCE_SHA = 'e15d9956b02b0595f64ae191657ce33652a76b32d24891c1fd429af1d48a4f2c'
BINARY_SHA = 'a9c07ccc581217b86583e59fc5c549b189011417b31577e8d57baa57a4dce38e'
RESULT_SHA = '5d11be3e540e2ac2c579e91381b20e634c3be1ba9cd025e18ff9a04c030201b4'
RUNTIME_SHA = 'dc1fabf8706821f7f9a5e813bdfd45c2092a6317841ed09ffafd2237860f5ad8'
SIZE = 257
PIXELS = SIZE * SIZE
MODES = ('old', 'stable')
ROLES = ('physical', 'reasons', 'inputs')
CASES = ('central2-cachezero-guard0', 'central2-cachezero-guard1',
    'central2-cachepositive-guard0', 'central2-cachepositive-guard1', 'wide60-cachepositive-guard1')
EPS8 = 8 * 2**-23
POLICY = dict(observer_C0_absolute=.0005, observer_C0_relative=.0002, depth_absolute=2e-6,
    cross_variant_C0_absolute=2e-6, cross_variant_C0_relative=.0002,
    cross_variant_mean_view_XYZ_absolute_relative=EPS8, repeat_absolute=0,
    reason_TES_absolute=0, ROI_center=[128, 128], ROI_radius=40)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def require(okay, message):
    if not okay:
        raise ValueError(message)


require(sha(HELPER_PATH.read_bytes()) == HELPER_SHA, 'Frozen shared read-only helper changed')
spec = importlib.util.spec_from_file_location('frozen_native_helpers', HELPER_PATH)
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)


def erase(source, begin, end):
    require(source.count(begin) == source.count(end) == 1, 'Unique source recovery tag required')
    start = source.index(begin)
    stop = source.index(end, start) + len(end)
    return source[:start] + source[stop:]


def strip_inputs(source):
    for name in INPUT_BODIES:
        source = erase(source, '// AQUALUMEN_SNELL_INPUT_BEGIN:' + name + '\n',
            '// AQUALUMEN_SNELL_INPUT_END:' + name + '\n')
    require('AQUALUMEN_SNELL_INPUT_' not in source, 'Unknown input source tag')
    return source


def restore_stable(source):
    source = erase(source, '// AQUALUMEN_SNELL_MAIN_MODULE_BEGIN\n',
        '// AQUALUMEN_SNELL_MAIN_MODULE_END\n')
    for name, (old, new) in REPLACEMENTS.items():
        tagged = '// AQUALUMEN_SNELL_MAIN_REPLACE_BEGIN:' + name + '\n' + new + \
            '// AQUALUMEN_SNELL_MAIN_REPLACE_END:' + name + '\n'
        require(source.count(tagged) == 1, 'Stable replacement differs')
        source = source.replace(tagged, old)
    require(source.count(EXTENSION) == 1, 'Stable FS extension differs')
    return source.replace(EXTENSION, '')


def sources(packet, manifest):
    expected = {}
    zip_hashes = {}
    for mode in MODES:
        input_pack = ROOT / f'reports/2026-10-03-water-snell-main/cpu-pack/Aqualumen-SnellMain-{mode}-inputs-v1.zip'
        policy = pack_policy(input_pack)
        for role in ('reasons', 'inputs'):
            pack = input_pack.with_name(input_pack.name.replace('-inputs-', '-' + role + '-'))
            files = zip_files(pack)
            zip_hashes[pack.name] = sha(pack.read_bytes())
            meta = json_file(packet / f'{mode}-{role}-metadata.json')
            require(meta == json.loads(files[MANIFEST]), 'Saved authoritative metadata differs')
            require((meta['mode'], meta['observe']) == (mode, role), 'Source variant/role')
            require(recover_inputs(files[HELPER]) == files['SNELL-MAIN-reason-helper.glsl']
                if role == 'inputs' else files[HELPER] == files['SNELL-MAIN-reason-helper.glsl'],
                'Raw helper role recovery')
            helper = files['SNELL-MAIN-reason-helper.glsl']
            require((recover_helper(helper) if mode == 'stable' else helper) ==
                files['PARENT-SNELL-MAIN-reason-helper.glsl'], 'Exact old inverse source recovery')
            if mode == 'stable':
                original = files['PARENT-SNELL-MAIN-node.glsl']
                require(sha(original) == NODE_SHA and original.count(NODE_EXTENSION_GUARD.encode()) == 1
                    and files[NODE] == original.replace(NODE_EXTENSION_GUARD.encode(), b'', 1),
                    'Stable included module changed beyond extension adaptation')
            expanded = shared.expand(files, WATER)
            expected[f'{mode}-{role}-expanded.fsh'] = expanded.encode()
            store = INPUT_STORE if role == 'inputs' else STORE
            require(expanded.count(store) == 1, 'Exact observer STORE')
            physical = expanded.replace(store, '')
            if role == 'inputs':
                physical = strip_inputs(physical)
            physical = strip_reason_blocks(physical)
            name = f'{mode}-physical-expanded.fsh'
            if name in expected:
                require(expected[name] == physical.encode(), 'Physical main differs between observer roles')
            expected[name] = physical.encode()
            expected[f'{mode}-{role}-metadata.json'] = files[MANIFEST]
            for n, stage in enumerate(('vsh', 'tcs', 'tes')):
                name = f'geometry-stage{n}.glsl'
                value = shared.expand(files, 'shaders/gbuffers_water.' + stage).encode()
                require(name not in expected or expected[name] == value, 'Four-stage geometry changed')
                expected[name] = value
        require(policy['mode'] == mode, 'Public input policy mode differs')
    require(restore_stable(expected['stable-physical-expanded.fsh'].decode()).encode() ==
        expected['old-physical-expanded.fsh'], 'Stable expanded physical main does not restore old bytes')
    for name, value in expected.items():
        require(shared.read_bytes(packet / name, manifest) == value, 'Compiled source export differs: ' + name)
    return expected, zip_hashes


def channels(values, alpha):
    return array('f', (v for i, v in enumerate(values) if (i % 4 == 3) is alpha))


def central(values):
    return array('f', (values[p + c] for y in range(SIZE) for x in range(SIZE)
        if (x - 128)**2 + (y - 128)**2 <= 1600 for p in [(y * SIZE + x) * 4] for c in range(4)))


def audit(packet):
    packet = Path(packet).resolve()
    manifest = {}
    receipt_path = ROOT / 'reports/2026-10-03-water-snell-main/cpu-native/HANDOFF.json'
    receipt = json_file(receipt_path)
    require(receipt['source_sha256'] == SOURCE_SHA and receipt['binary_sha256'] == BINARY_SHA,
        'Frozen probe receipt pins differ')
    require(sha((ROOT / receipt['source']).read_bytes()) == SOURCE_SHA and
        sha((ROOT / receipt['binary']).read_bytes()) == BINARY_SHA, 'Frozen probe source/executable bytes')
    for name, digest in receipt['inherited_sources_sha256'].items():
        require(sha((ROOT / name).read_bytes()) == digest, 'Included source changed: ' + name)
    require(sha((ROOT / 'tools/water_snell_main_runtime.py').read_bytes()) == RUNTIME_SHA and
        sha((ROOT / 'tools/water_snell_boundary_reference.py').read_bytes()) == REFERENCE_SHA,
        'Public input/reference source changed')
    result = json_file(packet / 'result.json')
    require(sha(shared.read_bytes(packet / 'result.json', manifest)) == RESULT_SHA, 'Frozen actual result differs')
    require(result['schema'] == 'aqualumen-snell-main-native-v1' and result['size'] == SIZE and
        result['phase_seconds'] == 120 and result['patch_arity'] == 3 and result['fp64Available'] is True
        and result['rawFormat'] == 'little-endian binary32 bottom-left origin' and result['policy'] == POLICY
        and result['input_C12_is_TES'] is False and result['same_draw_input_payload'] is True, 'Fixed source/fixture/policy')
    expected, pack_hashes = sources(packet, manifest)
    names = [m + '-' + r for m in MODES for r in ROLES]
    require([p['name'] for p in result['programs']] == names and all(p['linked'] is True and
        sorted(p['stage_types']) == [35632,35633,36487,36488] and p['tess_layout'] == [3,4,514,2305,0]
        for p in result['programs']), 'Actual six linked four-stage programs')
    require(result['case_count'] == 5 and [c['path'] for c in result['cases']] == list(CASES), 'No case subset')
    reports = []
    counts = Counter()
    maximum = 0.0
    comparison_maxima = {}
    for index, case in enumerate(result['cases']):
        print('CPU replay ' + case['path'], file=sys.stderr, flush=True)
        wide = index == 4
        positive = wide or index >= 2
        guard = 1 if wide else index % 2
        directory = packet / case['path']
        require(case['guard'] == guard and case['positive_cache'] is positive and
            case['aperture_degrees'] == (60 if wide else 2) and case['central_acceptance_case'] is (not wide),
            'Changed fixture role')
        programs = {}
        require(len(case['queried_program_sources']) == 4, 'Complete source queries required')
        for pair, (mode, role) in zip(case['queried_program_sources'], ((m,r) for m in MODES for r in ROLES[1:])):
            require(len(pair) == 2, 'Attached program pair')
            for query, current_role in zip(pair, ('physical', role)):
                key = mode + '-' + current_role
                require(type(query['program']) is int and query['program'] > 0 and
                    query['currentProgramBefore'] == query['currentProgramAfter'], 'Source-query state')
                require(key not in programs or programs[key] == query['program'], 'Program identity changed')
                programs[key] = query['program']
                require(sorted(s['type'] for s in query['stages']) == [35632,35633,36487,36488], 'Four attached stages')
                for stage in query['stages']:
                    name = key + '-expanded.fsh' if stage['type'] == 35632 else \
                        f'geometry-stage{(35633,36488,36487).index(stage["type"])}.glsl'
                    require(stage['bytes'] == len(expected[name]) and stage['sha256'] == sha(expected[name]),
                        'Actual attached shader-source query differs')
                    counts['attachedStageDigests'] += 1
        require(len(set(programs.values())) == 6, 'Aliased programs')
        frames = {}
        inputs = []
        ledger = {}
        for mode in MODES:
            for role in ROLES:
                key = mode + '-' + role
                frame = [shared.floats(directory / f'{key}-slot{s}.rgba32f', PIXELS * 4, manifest) for s in range(8)]
                frame.append(shared.floats(directory / f'{key}-depth.f32', PIXELS, manifest))
                frames[key] = frame
                for slot, values in enumerate(frame):
                    suffix = f'slot{slot}.rgba32f' if slot < 8 else 'depth.f32'
                    repeat = shared.floats(directory / f'{key}-repeat-{suffix}', len(values), manifest)
                    require(values.tobytes() == repeat.tobytes(), 'Whole binary32 repeat differs')
                    ledger[key + '-' + ('depth' if slot == 8 else 'slot' + str(slot)) + '-repeat'] = (values, repeat, 0, 0)
                    counts['exactRepeatPairs'] += 1
                    counts['finiteRealShaderOutputMaps' if slot < 5 else
                        'finiteInactiveClearedMaps' if slot < 8 else 'finiteDepthMaps'] += 2
                    if 5 <= slot < 8:
                        require(all(v == 0 for v in values), 'Inactive storage not cleared zero')
                for label, d in ((key, directory), (key + '-repeat', directory),
                        ('actual-inputs', directory / (key + '-actual-inputs'))):
                    path = d / (label + '-guard.json')
                    g = json_file(path)
                    shared.read_bytes(path, manifest)
                    shared.typed(g, dict(schema='aqualumen-native-sun-iris-guard-input-v1', program=programs[key],
                        currentProgramBefore=programs[key], currentProgramAfter=programs[key],
                        name='aqualumenSunTestAuthorized', type=5124, size=1, value=guard))
                    counts['typedScalarGuardQueries'] += 1
                inputs.append(shared.input_snapshot(directory / (key + '-actual-inputs'), case, programs[key], manifest))
                counts['actualInputSnapshots'] += 1
                counts['finiteInputTextureMaps'] += 8
        require(all(value == inputs[0] for value in inputs), 'Matrices or actual texture bytes differ across roles/variants')
        vertices = shared.floats(directory / 'uploaded-open-water-vertices.f32', 90, manifest)
        require(all(vertices[p+12:p+15] == array('f', [0,1,10000]) for p in range(0,90,15)), 'Actual lightmap/material input')
        for mode in MODES:
            physical = frames[mode + '-physical']
            for role in ROLES[1:]:
                key = mode + '-' + role
                for slot, label, absolute, relative in ((0,'C0',.0005,.0002),(8,'depth',2e-6,0)):
                    ledger[key + '-' + label + '-passive'] = (physical[slot], frames[key][slot], absolute, relative)
                if role == 'reasons':
                    ledger[key + '-C12-TES-exact'] = (physical[4], frames[key][4], 0, 0)
            ledger[mode + '-reason-input-covariance-flags-exact'] = (frames[mode+'-reasons'][3], frames[mode+'-inputs'][3],0,0)
        old, stable = frames['old-inputs'], frames['stable-inputs']
        for slot in (1,2):
            ledger[f'cross-variant-input-slot{slot}-XYZ-EPS8'] = (channels(old[slot], False), channels(stable[slot], False),EPS8,EPS8)
            ledger[f'cross-variant-input-slot{slot}-alpha-exact'] = (channels(old[slot], True), channels(stable[slot], True),0,0)
        for slot, label in ((3,'input-covariance-flags'),(8,'physical-depth'),(4,'physical-TES')):
            a, b = (old,stable) if slot == 3 else (frames['old-physical'],frames['stable-physical'])
            ledger['cross-variant-' + label + '-exact'] = (a[slot],b[slot],0,0)
        if not wide:
            a,b = frames['old-physical'][0],frames['stable-physical'][0]
            regression = not guard or not positive
            ledger['old-stable-C0-' + ('regression' if regression else 'central-optical-comparison')] = \
                (a if regression else central(a), b if regression else central(b), 2e-6,.0002)
        rows = case['comparisons']
        require(len(rows) == len(ledger) and len({r['name'] for r in rows}) == len(rows), 'Complete unique comparison ledger')
        for row in rows:
            a,b,absolute,relative = ledger.pop(row['name'])
            delta = shared.compare(a,b,absolute,relative)
            require(row == dict(name=row['name'], accepted=True, samples=len(a), max_absolute_delta=delta,
                absolute_tolerance=absolute, relative_tolerance=relative), 'Recorded comparison differs from raw replay')
            maximum = max(maximum, delta)
            comparison_maxima[case['path'] + '/' + row['name']] = delta
            counts['comparisonGatesRecomputed'] += 1
        require(not ledger, 'Unreplayed comparison')
        mode_reports = []
        for mode in MODES:
            physical, reasons, input_frame = (frames[mode+'-'+r] for r in ROLES)
            histogram = [0]*10
            totals = Counter()
            references = Counter()
            first_targets = []
            for y in range(SIZE):
                for x in range(SIZE):
                    if not wide and (x-128)**2+(y-128)**2 > 1600:
                        continue
                    p = (y*SIZE+x)*4
                    tes = list(physical[4][p:p+4])
                    cov = list(reasons[3][p:p+4])
                    if wide and tes[3] == 0:
                        totals['nonwater'] += 1
                        continue
                    if wide and cov[3] != 15:
                        totals['excludedEligible'] += 1
                        continue
                    totals['inspected'] += 1
                    require(cov[3] == 15 and shared.stage(tes) and shared.stage(reasons[4][p:p+4])
                        and all(f[0][p+3] == 1 for f in (physical,reasons,input_frame)), 'Unqualified raster domain')
                    require((cov[0]>0 and cov[2]>0 and cov[0]*cov[2]-cov[1]**2>0 and cov[0]+cov[2]>1e-5)
                        if guard else cov[:3] == [0,0,0], 'Actual covariance domain')
                    payload = list(reasons[1][p:p+4])
                    status = list(reasons[2][p:p+4])
                    qualify_point(dict(reasonTuple=payload, sun_status=status, covariance_flags=cov,
                        stage=list(reasons[4][p:p+4])))
                    require(status[0] == guard and (positive or status[1:] == [0,0,0]), 'Actual request/source negative control')
                    if not wide:
                        require(status == [guard,int(guard and positive),0,0], 'Fixed central application')
                    record = dict(x=x,y=y, **{name:list(input_frame[slot][p:p+4]) for slot,name in enumerate(
                        ('mean_called','view_requested','covariance_flags','first_target_reason'),1)})
                    interpreted = analyze_record(record)
                    require(interpreted['helperCalled'] == bool(guard) and interpreted['requested'] == bool(status[0])
                        and interpreted['firstReason'] == payload[0], 'Same-draw target/reason/call attribution differs')
                    if interpreted['firstReason']:
                        ref = interpreted['reference']
                        require(sum(payload[1:]) > 0 and ref['precision_agreement'] is True, 'Recorded first target/reference disagreement')
                        references[interpreted['arithmeticReplayClassification']] += 1
                        first_targets.append(dict(**record, firstReason=interpreted['firstReason'],
                            firstNodeIndex=interpreted['firstNodeIndex'], classification=interpreted['arithmeticReplayClassification'],
                            support=ref['physical']['supported'], precisionAgreement=ref['precision_agreement'],
                            rawViewBits=ref['raw_v_bits'], rawTargetBits=ref['raw_t_bits'],
                            discriminant120=ref['physical'].get('discriminant'),
                            oldHypotheticalReplayAccepted={k:v['accepted'] for k,v in ref['old_binary32'].items()}))
                    else:
                        require(payload == [0,0,0,0], 'Absent target has classified reason')
                        references['NOT_EVALUATED'] += 1
                    histogram[interpreted['firstReason']] += 1
                    totals['applied'] += status[1] == 1
                    totals['recordedFirstTargets'] += interpreted['firstNodeIndex'] is not None
                    for name,value in zip(('hemisphere','receiver','other'),payload[1:]):
                        totals[name] += int(value)
            for key, value in (('inspected_points_old_stable',totals['inspected']),
                ('domain_qualified_points_old_stable',totals['inspected']),('input_accounted_points_old_stable',totals['inspected']),
                ('applied_points_old_stable',totals['applied']),('first_failed_target_points_old_stable',totals['recordedFirstTargets'])):
                require(case[key][MODES.index(mode)] == value, 'Recorded all-point count differs: '+key)
            require(histogram == case['first_reason_histograms_old_stable'][MODES.index(mode)], 'Recorded first-reason histogram')
            require(totals['inspected'] == (15274 if wide else 5025) and
                (not wide or totals['nonwater']+totals['excludedEligible']+totals['inspected'] == PIXELS), 'No subset shrink/whole wide canvas')
            mode_reports.append(dict(mode=mode, counts=dict(totals), firstReasonHistogram=histogram,
                referenceClassifications=dict(references), recordedFirstTargets=first_targets))
        for sample in case['fixed_six_samples']:
            x,y = sample['pixel']
            p = (y*SIZE+x)*4
            require(len(sample['variants']) == 2, 'Fixed six variant pair')
            for saved,mode in zip(sample['variants'],MODES):
                require(saved == dict(mode=mode, physical_C0=list(frames[mode+'-physical'][0][p:p+4]),
                    reason_C9=list(frames[mode+'-reasons'][1][p:p+4]), WNS_status=list(frames[mode+'-reasons'][2][p:p+4]),
                    inputs=[list(frames[mode+'-inputs'][s][p:p+4]) for s in range(1,5)]), 'Fixed sample/raw mismatch')
                counts['fixedSampleVariantsRecomputed'] += 1
        require(len(case['fixed_six_samples']) == 6, 'Fixed six completeness')
        reports.append(dict(path=case['path'], variants=mode_reports))
    require(result['status'] == 'PASS' and result['fixture_qualified'] is True and result['accepted'] is True,
        'Actual exporter terminal status disagrees')
    return dict(schema='aqualumen-independent-snell-main-native-audit-v1', status='PASS',
        sourceSHA256=SOURCE_SHA, binarySHA256=BINARY_SHA, nativeResultSHA256=RESULT_SHA,
        frozenHelperSHA256=HELPER_SHA, publicRuntimeSHA256=RUNTIME_SHA, referenceSHA256=REFERENCE_SHA,
        packSHA256=pack_hashes, counts=dict(counts), maximumAllComparisonDelta=maximum,
        comparisonMaxima=comparison_maxima,
        maximumObserverC0Delta=max(v for k,v in comparison_maxima.items() if k.endswith('-C0-passive')),
        maximumObserverDepthDelta=max(v for k,v in comparison_maxima.items() if k.endswith('-depth-passive')),
        cases=reports, sourceRecoveryQualified=True, passivityQualified=True, empiricalCentralRegressionQualified=True,
        manifest={str(Path(p).relative_to(packet)):d for p,d in manifest.items()},
        forcedCriticalFixture=False,numericBugReproduced=False,all48NodeCausesObserved=False,
        GPUArithmeticCauseProven=False,physicsAccepted=False,pixelAAAccepted=False,IrisAccepted=False,
        visualAccepted=False,motionAccepted=False,FPSAccepted=False,energyAccepted=False,shippingAccepted=False,
        scope='Full saved native actual-main call/passivity/regression and same-draw first-target replay only. '
            'Wide firstReason counts one failed node per texel; grouped hemisphere includes categories3/9. '
            'Scalar support replay excludes reflected hemisphere/receivers/legacy whole-cap admission. '
            'No target means not observed, not physical zero. Input C12 is not TES. Slots5–7 are cleared storage, '
            'not shader outputs. Saved source/binary identities do not independently attest root launch lifecycle.')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: audit.py SAVED_NATIVE_PACKET')
    print(json.dumps(audit(sys.argv[1]), indent=2, sort_keys=True, allow_nan=False))
