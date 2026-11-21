"""CPU-only saved prepared-main replay; no GL, game or source mutations."""
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys

import water_sun_prepared_audit as node_audit
import water_sun_prepared_timing as timing

SELECTED_PIXELS = [(128,128),(88,128),(168,128),(128,88),(128,168),
                   (64,64),(192,64),(64,192),(192,192)]
MODES = ('old', 'prepared')
KINDS = ('target', 'view', 'class')
ROLES = ('physical', 'reasons', 'inputs', 'all48')
require = node_audit.require
sha = node_audit.digest
PINS = {
    'source': '0e7e27e6cbf6655638745021c197c0c16f50784474f9fe820dce01e678b7ead5',
    'test': '5cffa7c4ba9918f549f2a34cc6b4b79dbd3bfa2e63323fceb36bbda421bcdc91',
    'binary': '99dccceaed1becea7678dc59ad4860d3c8e468d7486bd6f19172210d7434307e',
    'manifest': '1e2e0fe461aef7a33a2f9f5d2579aa866bef93d976f9197dfc0e442e30854921',
    'nodeReader': '0fca072c961304ed563a7e9ba914bd196eb33c1ece80b227e726ad75a8e349b8',
    'timing': '964103d36ed855cd752c9dbe793819577b01d94063719ea498a372dfee60522c',
}
GEOMETRY = ['5cb5cde275882a57395d34e1bdd7e2ccf852051cbcb5d421995e1a76557401fd',
            'bcdebf3c355194c6be1f901a2c8b582ec7eeb4d1ae5fb5ce6dcc23143a9df932',
            '973e088388ddec93565cb5aaa47f0bbd397703d7a381f900b19f8ed1d1765b6b']


def read(root, name, limit=32*1024*1024):
    path = Path(name)
    require(not path.is_absolute() and '..' not in path.parts, 'Contained packet path required')
    full = root / path
    require(full.resolve().is_relative_to(root.resolve()), 'Contained packet file required')
    return node_audit.read(full, limit)


def load(root, name):
    return node_audit.load_json(read(root, name))


def floats(raw, count):
    require(len(raw) == count*4 and sys.byteorder == 'little', 'Exact little-endian binary32 bytes required')
    values = array('f'); values.frombytes(raw)
    require(all(math.isfinite(x) for x in values), 'Nonfinite binary32 capture')
    return values


def counts(value):
    require(math.isfinite(value) and value == int(value) and 0 <= value < 2**24, 'Exact typed certificate countword required')
    word = int(value)
    result = [(word >> (6*i)) & 63 for i in range(4)]
    require(all(x <= 48 for x in result) and sum(result[:3]) == result[3], 'Invalid certificate counts')
    return result


def verify_nodes(root, records, count_words, size=257, selected_pixels=SELECTED_PIXELS):
    """Scan all direct maps/ledger; arithmetic subset is fixed, not outcome-selected."""
    require(len(records) == 48 and [r['node'] for r in records] == list(range(48)), 'All 48 ordered records required')
    pixels = size*size
    require(len(count_words) == pixels, 'Full-view countword map required')
    selected = {y*size+x for x,y in selected_pixels if 0 <= x < size and 0 <= y < size}
    require(len(selected) == len(selected_pixels), 'Unique in-bounds fixed pixels required')
    ledger = array('I', [0]) * (pixels*4)
    generated_total = called_total = arithmetic_records = 0
    hist = {'unknown': 0, 'absent': 0, 'supported': 0}
    arithmetic_hist = dict(hist)
    cache = {}
    reference_view = None
    for node, record in enumerate(records):
        saved = record['saved_maps']
        require(saved['node'] == node and saved['duplicate_maps_omitted'] is False, 'Direct BOTH-mode node archives required')
        entries = saved['maps']
        require(len(entries) == 6, 'Exactly six node maps required')
        raws, values = {}, {}
        for entry, (mode,kind) in zip(entries, [(m,k) for m in MODES for k in KINDS]):
            require(entry['mode'] == mode and entry['kind'] == kind and entry['slot'] == KINDS.index(kind)+5,
                    'Ordered typed node map roles required')
            require(Path(entry['file']).name == f'node{node}-{mode}-{kind}.rgba32f'
                    and (size != 257 or Path(entry['file']).parent == Path('all48-targets')), 'Canonical direct node filename required')
            raw = read(root, entry['file'])
            require(type(entry['bytes']) is int and entry['bytes'] == len(raw) == pixels*16
                    and sha(raw) == entry['sha256'], 'Saved node map hash/size differs')
            raws[mode,kind] = raw
            values[mode,kind] = floats(raw, pixels*4)
        for kind in KINDS:
            require(raws['old',kind] == raws['prepared',kind], 'Whole old/prepared raw bits differ: '+kind)
        if reference_view is None:
            reference_view = raws['old','view']
        require(raws['old','view'] == reference_view, 'Whole raw view/eta differs across nodes')
        target, view, status = [values['old',k] for k in KINDS]
        generated = called = 0
        for pixel in range(pixels):
            p = pixel*4
            flag = status[p+3]
            require(flag in (0., 1.), 'Generated flag must be binary')
            if flag == 0:
                require(all(values['old',k][p+c] == 0 for k in KINDS for c in range(4)),
                        'Non-generated record contains observations')
                continue
            generated += 1
            require(status[p+2] == node and target[p+3] == node+1
                    and view[p+3] == struct.unpack('<f', struct.pack('<f', 1.333))[0], 'Generated node identity/eta differs')
            require(status[p+1] in (0.,1.), 'Called flag must be binary')
            if status[p+1] == 0:
                require(status[p] == 0, 'Uncalled class is not observed')
                continue
            called += 1
            encoded = status[p]
            require(encoded in (0.,1.,2.), 'Observed certificate class must be exact 0/1/2')
            c = 2 if encoded == 0 else 0 if encoded == 1 else 1
            ledger[p+c] += 1; ledger[p+3] += 1
            hist[('absent','supported','unknown')[c]] += 1
            if pixel in selected:
                for mode in MODES:
                    bits = (*struct.unpack_from('<3I', raws[mode,'view'], p*4),
                            *struct.unpack_from('<3I', raws[mode,'target'], p*4),
                            struct.unpack_from('<I', raws[mode,'view'], (p+3)*4)[0])
                    if bits not in cache:
                        ctx, valid = node_audit.context(bits)
                        cache[bits] = node_audit.classification(bits, ctx, valid)
                    require(cache[bits]+1 == values[mode,'class'][p], 'Selected independent arithmetic class differs')
                    arithmetic_hist[('unknown','absent','supported')[cache[bits]+1]] += 1
                    arithmetic_records += 1
        require(generated == record['generated_pixels'] and called == record['class_called_pixels'], 'Full node generated/called counts differ')
        generated_total += generated; called_total += called
    for pixel, word in enumerate(count_words):
        require(list(ledger[pixel*4:pixel*4+4]) == counts(word), 'Full-view actual class/count ledger differs')
    return {'nativeGLExecuted': False, 'directMapsVerified': 48*6,
            'fullNodePixelPairsPerMode': 48*pixels, 'fullLedgerPixels': pixels,
            'generatedNodePixelPairsPerMode': generated_total, 'calledNodePixelPairsPerMode': called_total,
            'observedClassHistogramPerMode': hist, 'selectedPixels': selected_pixels,
            'selectedArithmeticRecords': arithmetic_records, 'selectedUniqueRawInputs': len(cache),
            'selectedArithmeticClassHistogram': arithmetic_hist,
            'all48ClassArithmeticEveryPixelAccepted': False}


def erase(source, begin, end):
    require(source.count(begin) == source.count(end) == 1, 'Unique removable source tags required')
    a, b = source.index(begin), source.index(end)
    require(a < b, 'Source tag order differs')
    return source[:a] + source[b+len(end):]


def verify_sources(root, result, receipt):
    require(receipt is not None, 'Frozen v3 probe receipt required')
    receipt = Path(receipt)
    handoff_raw = node_audit.read(receipt)
    handoff = node_audit.load_json(handoff_raw)
    require(handoff['schema'] == 'aqualumen-prepared-main-root-execution-v1'
            and handoff['native_gl_executed_by'] == 'root' and handoff['native_exit_code'] == 0
            and handoff['native_output_directory'] == root.name
            and handoff['native_result_sha256'] == sha(read(root,'result.json')), 'Executed root v3 receipt required')
    for key, pin in [('probe_source_sha256',PINS['source']), ('tests_sha256',PINS['test']), ('binary_sha256',PINS['binary'])]:
        require(handoff[key] == pin, 'Frozen source/binary receipt pin differs')
    for field,pin in [('probe_source_file',PINS['source']),('tests_file',PINS['test']),('binary_file',PINS['binary'])]:
        require(sha(read(receipt.parent,handoff[field])) == pin, 'Root frozen source/binary snapshot differs')
    sources = timing._sources(root, result)
    require(result['source_manifest_sha256'] == PINS['manifest']
            and result['executable_sha256'] == PINS['binary']
            and sha(read(root, 'executed-binary')) == PINS['binary'], 'Executed v3 artifact identity differs')
    require(sources['host-sources/water_sun_prepared_main_probe.cpp'] == PINS['source']
            and sources['host-sources/test_water_sun_prepared_main_probe.py'] == PINS['test'], 'Archived host source pin differs')
    require([sources[f'geometry-stage{i}.glsl'] for i in range(3)] == GEOMETRY, 'Unchanged geometry pins differ')
    helpers = {mode:read(root,mode+'-water-sun-support.glsl').decode() for mode in MODES}
    require(sources['old-water-sun-support.glsl'] == node_audit.PINS['old']
            and sources['prepared-water-sun-support.glsl'] == node_audit.PINS['prepared'], 'Exact helper pin differs')
    old_call = '        int WSP_supportClass=waterSunSupportClass(viewToEye,target,eta);\n'
    new_call = '        int WSP_supportClass=waterSunSupportClassPrepared(WPM_viewContext,target);\n'
    shader = {}
    for role in ROLES:
        for mode in MODES:
            shader[mode,role] = read(root,mode+'-'+role+'-expanded.fsh').decode()
        restored = shader['prepared',role]
        require(restored.count(helpers['prepared']) == 1 and restored.count(new_call) == 1, 'Unique context/module/call required')
        restored = restored.replace(helpers['prepared'], helpers['old'])
        restored = erase(restored,'// AQUALUMEN_PREPARED_MAIN_CONTEXT_BEGIN\n','// AQUALUMEN_PREPARED_MAIN_CONTEXT_END\n')
        restored = restored.replace(new_call,old_call)
        require(restored == shader['old',role], 'Prepared source does not recover old exactly')
    for mode in MODES:
        restored = shader[mode,'all48']
        for tag in ('GLOBALS','RESET','TARGET','NODE','STORE'):
            restored = erase(restored,f'// AQUALUMEN_PREPARED_TARGET_BEGIN:{tag}\n',f'// AQUALUMEN_PREPARED_TARGET_END:{tag}\n')
        require(restored == shader[mode,'physical'], 'All48 observer erasure differs from physical')
        require(read(root,mode+'-parent-reasons-metadata.json') == read(root,'old-parent-reasons-metadata.json')
                and read(root,mode+'-parent-inputs-metadata.json') == read(root,'old-parent-inputs-metadata.json'), 'Parent metadata changed')
    return sources, sha(handoff_raw)


def typed_guard(guard, program, value):
    require(guard['schema'] == 'aqualumen-native-sun-iris-guard-input-v1'
            and guard['name'] == 'aqualumenSunTestAuthorized'
            and type(guard['type']) is int and guard['type'] == 5124
            and type(guard['size']) is int and guard['size'] == 1
            and type(guard['value']) is int and guard['value'] == value, 'Actual scalar int guard differs')
    require(all(type(guard[k]) is int and guard[k] == program
                for k in ('program','currentProgramBefore','currentProgramAfter')), 'Guard program changed')


def query_sources(root, query, sources, mode, role):
    program = query['program']
    require(type(program) is int and program > 0 and type(query['currentProgramBefore']) is int
            and query['currentProgramBefore'] == query['currentProgramAfter'], 'Queried source program/state differs')
    stages = query['stages']
    require(len(stages) == 4 and {s['type'] for s in stages} == {35633,36488,36487,35632}, 'Four attached stages required')
    files = {35633:'geometry-stage0.glsl',36488:'geometry-stage1.glsl',36487:'geometry-stage2.glsl',
             35632:mode+'-'+role+'-expanded.fsh'}
    for stage in stages:
        name = files[stage['type']]
        require(type(stage['type']) is int and type(stage['bytes']) is int
                and stage['sha256'] == sources[name] and stage['bytes'] == len(read(root,name)), 'Attached source hash/bytes differs')
    return program


def verify_inputs(root, case, sources):
    prefix, guard = case['path'], case['guard']
    matrix_reference = texture_reference = None
    programs = {}
    physical_receipts = {}
    digests = []
    for role_index, role in enumerate(ROLES):
        queries = case['queried_program_sources'][role_index]
        require(len(queries) == 2, 'Two source queries per role required')
        for mode, query in zip(MODES, queries):
            program = query_sources(root,query,sources,mode,role); programs[mode,role] = program
            directory = f'{prefix}/{mode}-{role}-actual-inputs'
            raw = read(root,directory+'/actual-inputs.json'); digests.append(sha(raw))
            data = node_audit.load_json(raw)
            if role == 'physical': physical_receipts[mode] = data
            require(data['schema'] == 'aqualumen-native-residual-sun-inputs-v1' and data['program'] == program
                    and data['currentProgramBefore'] == data['currentProgramAfter'] == program
                    and data['stateRestored'] is True, 'Actual input program/restoration differs')
            for before,after in [('activeTextureBefore','activeTextureAfter'),('textureBindingBefore','textureBindingAfter')]:
                require(type(data[before]) is int and type(data[after]) is int and data[before] == data[after], 'Input query changed state')
            typed_guard(load(root,directory+'/actual-inputs-guard.json'),program,guard)
            matrices = timing._matrix_bits(data['matrices'])
            require(set(matrices) == {'gbufferProjection','gbufferProjectionInverse','gbufferModelView','gbufferModelViewInverse'}
                    and struct.pack('<16f',*data['fixedFunctionProjection']) == matrices['gbufferProjection']
                    and struct.pack('<16f',*data['fixedFunctionModelView']) == matrices['gbufferModelView'], 'Actual/fixed-function matrix bits differ')
            if matrix_reference is None: matrix_reference = matrices
            require(matrices == matrix_reference, 'Actual matrix bits changed across roles')
            expected_uniforms = [('sunPosition',35665,[0,0,-1]),('rainStrength',5126,[0]),
                                 ('viewWidth',5126,[257]),('viewHeight',5126,[257]),
                                 ('isEyeInWater',5124,[1]),('aqualumenDimension',5124,[0])]
            require(len(data['uniforms']) == 6, 'Six typed native uniforms required')
            for u,(name,kind,vals) in zip(data['uniforms'],expected_uniforms):
                require(u == dict(name=name,type=kind,size=1,values=vals), 'Actual typed uniform differs')
            require(data['aperture_degrees'] == case['aperture_degrees'] and data['sunDirectionDerivedFromActualUniforms'] == [0,1,0]
                    and data['solarRadius'] == .00465 and data['SOLAR'] == [18,17.6,17] and data['weatherFactor'] == 1, 'Fixed native solar inputs differ')
            names = ['gtexture','colortex4','colortex6','depthtex1','shadowtex0','colortex8','aqualumenBathymetry','colortex7']
            widths = [1,257,64,257,1,1,64,64]; heights = [1,257,32,257,1,1,64,32]
            formats = [34836,34836,34836,36012,36012,34842,34836,34836]
            require(len(data['samplers']) == 8, 'All eight actual inputs required')
            payload = []
            for unit,s in enumerate(data['samplers']):
                components = 1 if unit in (3,4) else 4
                require(s['unit'] == s['uniformUnit'] == unit and s['name'] == names[unit]
                        and s['uniformType'] == (35682 if unit == 4 else 35678) and s['uniformSize'] == 1
                        and type(s['texture']) is int and s['texture'] > 0 and s['sampler'] == 0
                        and [s['width'],s['height'],s['components'],s['internalFormat']] == [widths[unit],heights[unit],components,formats[unit]]
                        and s['minFilter'] == s['magFilter'] == 9728 and s['wrapS'] == s['wrapT'] == 33071
                        and s['compareMode'] == (34894 if unit == 4 else 0), 'Actual sampler binding/type/storage/filter differs')
                name = f'input-sampler{unit}'+('.f32' if components == 1 else '.rgba32f')
                require(s['file'] == name, 'Canonical input raw filename required')
                blob = read(root,directory+'/'+name); values = floats(blob,widths[unit]*heights[unit]*components)
                payload.append(blob)
                if unit in (3,4): require(all(v == 1 for v in values), 'Opaque-open actual depth input required')
                if unit in (2,7):
                    for p in range(widths[unit]*heights[unit]):
                        expected = ([.5,.625,.75] if case['positive_cache'] and unit == 2 and p == 64*31 else [0,0,0])
                        require(list(values[p*4:p*4+4]) == expected+[1], 'Actual cache/black LUT bytes differ')
            cache_rgb = [.5,.625,.75] if case['positive_cache'] else [0,0,0]
            require(data['solarCacheRGB'] == cache_rgb, 'Queried reserved-row solar cache differs')
            if texture_reference is None: texture_reference = payload
            require(payload == texture_reference, 'Actual input texture bits differ across every role')
            targets = data['targets']; require(len(targets) == 8, 'Eight actual output targets required')
            for slot,target in enumerate(targets):
                require(target['slot'] == slot and target['internalFormat'] == 34836 and target['width'] == target['height'] == 257
                        and type(target['texture']) is int and target['texture'] > 0, 'Output storage differs')
            require(len({t['texture'] for t in targets}) == 8, 'Output object aliases')
            depth = data['depth']
            require(depth['slot'] == 8 and depth['internalFormat'] == 36012 and depth['width'] == depth['height'] == 257
                    and depth['texture'] not in {t['texture'] for t in targets}, 'Depth storage differs')
    require(len(set(programs.values())) == 8, 'Eight distinct actual programs required')
    for mode in MODES:
        timer_directory = f'{prefix}/timer-{mode}-actual-inputs'
        timer_receipt = load(root,timer_directory+'/actual-inputs.json')
        # Do not let equal old/prepared timers silently use a changed fixture.
        for key in ('matrices','fixedFunctionProjection','fixedFunctionModelView','uniforms','samplers',
                    'targets','depth','aperture_degrees','solarCacheRGB','SOLAR','solarRadius','weatherFactor'):
            require(timer_receipt[key] == physical_receipts[mode][key], 'Timer actual input metadata differs from main fixture')
        for sampler in physical_receipts[mode]['samplers']:
            filename = sampler['file']
            require(read(root,timer_directory+'/'+filename) == read(root,f'{prefix}/{mode}-physical-actual-inputs/'+filename),
                    'Timer actual texture bits differ from main fixture')
    return programs, digests


def comparison(item, a_sha, b_sha, elements):
    require(item['elements'] == elements and item['a_sha256'] == a_sha and item['b_sha256'] == b_sha
            and a_sha == b_sha and item['mismatching_words'] == 0 and item['max_absolute_delta'] == 0
            and item['absolute_policy'] == item['relative_policy'] == 0
            and item['signed_zero_bits_compared'] is True and item['accepted'] is True, 'Exact comparison ledger contradicts saved raw')


def captures(root, case, programs):
    directory = case['path']; maps = {}; hashes = {}; verified = 0
    for mode in MODES:
        for role in ROLES[:3]:
            for repeat in (False,True):
                prefix = mode+'-'+role+('-repeat' if repeat else '')
                values = []
                for slot in range(9):
                    suffix = f'-slot{slot}.rgba32f' if slot < 8 else '-depth.f32'
                    blob = read(root,directory+'/'+prefix+suffix)
                    values.append(floats(blob,257*257*(4 if slot < 8 else 1)))
                    hashes[prefix,slot] = sha(blob); verified += 1
                    if slot in (5,6,7): require(all(x == 0 for x in values[-1]), 'Inactive cleared slots contain nonzero values')
                typed_guard(load(root,directory+'/'+prefix+'-guard.json'),programs[mode,role],case['guard'])
                if repeat:
                    require(all(hashes[prefix,s] == hashes[mode+'-'+role,s] for s in range(9)), 'Full capture repeat bits differ')
                else: maps[mode,role] = values
    expected = {}
    for mode in MODES:
        for role in ROLES[:3]:
            prefix = mode+'-'+role
            for slot in range(9): expected[prefix+('-slot'+str(slot) if slot < 8 else '-depth')+'-repeat'] = (prefix,slot,prefix+'-repeat',slot)
            if role != 'physical':
                expected[prefix+'-C0-physical-neutral'] = (mode+'-physical',0,prefix,0)
                expected[prefix+'-depth-physical-neutral'] = (mode+'-physical',8,prefix,8)
            if role == 'reasons': expected[prefix+'-TES-physical-neutral'] = (mode+'-physical',4,prefix,4)
    for role in ROLES[:3]:
        for slot in range(9): expected['old-prepared-'+role+('-slot'+str(slot) if slot < 8 else '-depth')] = ('old-'+role,slot,'prepared-'+role,slot)
    entries = case['comparisons']
    require(len(entries) == len(expected) and len({e['label'] for e in entries}) == len(expected), 'Full unique comparison ledger required')
    for entry in entries:
        a,slot,b,other = expected[entry['label']]
        comparison(entry,hashes[a,slot],hashes[b,other],257*257*(4 if slot < 8 else 1))
    return maps, hashes, verified


def stage(v):
    return abs(v[3]-1) <= 8*2**-23 and abs(sum(v[:3])-1) <= 2e-5 and all(-2e-5 <= x <= 1+2e-5 for x in v[:3])


def whole(value, high):
    return math.isfinite(value) and 0 <= value <= high and value == int(value)


def verify_domain(case, maps):
    totals = [0]*4; inspected = applied = complete = 0
    first_hist = {str(i):0 for i in range(10)}
    guard, positive = case['guard'], case['positive_cache']
    wide = case['path'].startswith('wide')
    for pixel in range(257*257):
        p = pixel*4; x,y = pixel%257,pixel//257
        if not wide and (x-128)**2+(y-128)**2 > 1600: continue
        covariance = maps['old','reasons'][3][p:p+4]
        physical_stage = maps['old','physical'][4][p:p+4]
        if wide and (physical_stage[3] == 0 or covariance[3] != 15): continue
        inspected += 1
        require(covariance[3] == 15 and stage(physical_stage)
                and stage(maps['old','reasons'][4][p:p+4])
                and all(maps['old',r][0][p+3] == 1 for r in ROLES[:3]), 'Fixed qualified pixel domain failed')
        if guard:
            xx,xz,zz = covariance[:3]
            require(xx > 0 and zz > 0 and xx*zz-xz*xz > 0 and xx+zz > 1e-5, 'Actual covariance domain failed')
        else: require(all(v == 0 for v in covariance[:3]), 'Unauthorized covariance nonzero')
        reasons = maps['old','reasons'][1][p:p+4]
        status = maps['old','reasons'][2][p:p+4]
        require(whole(reasons[0],9) and all(whole(v,48) for v in reasons[1:])
                and whole(status[0],1) and whole(status[1],1) and whole(status[3],48), 'Typed reason/status domain failed')
        count = counts(status[2]); rejection_sum = sum(reasons[1:])
        require(count[2] <= status[3] and count[2] <= reasons[3]
                and rejection_sum <= 48-count[0], 'Unknown/zero/rejection accounting contradicts')
        if status[1] == 1: require(count[3] == 48 and count[2] == 0 and status[3] == 0, 'Applied certificate ledger incomplete')
        zero_reasons = reasons[0] == rejection_sum == 0
        if not guard: require(zero_reasons and status[0] == status[1] == status[3] == status[2] == 0, 'Unauthorized status nonzero')
        else:
            require(status[0] == 1, 'Authorized call not requested')
            if not positive: require(zero_reasons and status[1] == status[3] == status[2] == 0, 'Zero-cache status nonzero')
            elif status[1] == 1: require(zero_reasons and status[3] == 0, 'Applied node rejection nonzero')
            elif rejection_sum == 0: require(zero_reasons and status[3] in (0,1), 'Unclassified fallback invalid')
            else:
                group = 1 if reasons[0] in (3,9) else 2 if reasons[0] in (6,7) else 3
                require(rejection_sum == status[3] and reasons[0] > 0 and reasons[group] > 0, 'First reason/group accounting differs')
        if not wide: require(status[0] == guard and status[1] == int(guard and positive) and status[3] == 0, 'Fixed central application failed')
        values = [v for slot in range(1,5) for v in maps['old','inputs'][slot][p:p+4]]
        require(values[3] == guard and values[7] == status[0] and values[11] == 15, 'Same-draw input flags/call/request differ')
        if not guard: require(all(v == 0 for i,v in enumerate(values) if i != 11), 'Unauthorized input observations nonzero')
        else:
            require(all(abs(sum(v*v for v in values[start:start+3])-1) <= 8*(8*2**-23) for start in (0,4)), 'Actual mean/view norm outside retained domain')
            code = values[15]
            if code == 0: require(all(v == 0 for v in values[12:15]) and zero_reasons, 'Missing target marker contradicts reason')
            else:
                require(whole(code,624) and 1 <= int(code)%64 <= 48 and 1 <= int(code)//64 <= 9
                        and int(code)//64 == reasons[0] and rejection_sum > 0
                        and abs(sum(v*v for v in values[12:15])-1) <= 8*(8*2**-23), 'First actual target/code domain failed')
        for i in range(4): totals[i] += count[i]
        applied += int(status[1]); complete += count[3] == 48
        first_hist[str(int(reasons[0]))] += 1
    require(inspected > 0 and (wide or inspected == 5025), 'Original fixed domain was shrunk')
    producer = case['domain_and_count_accounting']
    for key,value in [('inspected_old_prepared',[inspected]*2),('qualified_old_prepared',[inspected]*2),
                      ('count_accounted_old_prepared',[inspected]*2),('applied_old_prepared',[applied]*2),
                      ('complete48_old_prepared',[complete]*2),('class_totals_old_prepared',[totals]*2)]:
        require(producer[key] == value, 'Producer domain/count summary differs from raw')
    return {'inspectedPerMode':inspected,'appliedPerMode':applied,'complete48PerMode':complete,
            'classTotalsPerMode':dict(zip(('absent','supported','unknown','calls'),totals)),
            'firstReasonHistogram':first_hist, 'nonAdmittedPixels':257*257-inspected if wide else None}


def verify_node_states(case, programs, sources, hashes):
    records = case['all48_inputs_classes']['records']
    for node,record in enumerate(records):
        for mode in MODES:
            states = record['actual_draw_state'][mode]
            before,after = states['before'],states['after']
            require(states['draw_state_unchanged'] is True and before == after, 'Node draw state changed')
            require(before['expectedProgram'] == before['currentProgram'] == programs[mode,'all48']
                    and type(before['drawFramebuffer']) is int and before['drawFramebuffer'] > 0
                    and type(before['VAO']) is int and before['VAO'] >= 0 and before['patchVertices'] == 3
                    and before['viewport'] == [0,0,257,257] and before['drawBuffers'] == list(range(36064,36072)), 'Actual all48 routing/program differs')
            for key,name,value in [('requestedNode','WPM_requestedNode',node),('guard','aqualumenSunTestAuthorized',case['guard'])]:
                u = before[key]
                require(u['name'] == name and type(u['type']) is int and u['type'] == 5124
                        and type(u['size']) is int and u['size'] == 1 and type(u['location']) is int and u['location'] >= 0
                        and type(u['value']) is int and u['value'] == value, 'Actual node/guard scalar uniform differs')
            require(record['fragment_source_sha256'][mode] == sources[mode+'-all48-expanded.fsh'], 'Actual pernode source link differs')
        entries = {e['label']:e for e in record['comparisons']}
        require(len(entries) == len(record['comparisons']) == (22 if node else 21), 'Node comparison chronology differs')
        raw_hashes = {(e['mode'],e['slot']):e['sha256'] for e in record['saved_maps']['maps']}
        # Slots0..4/depth are ONLY the producer's in-memory hash records:
        # archived all48 raw contains slots5..7, not independent C0 neutrality.
        for mode in MODES:
            for slot in range(6):
                label = mode+'-all48-'+('slot'+str(slot) if slot < 5 else 'depth')+'-physical-neutral'
                h = hashes[mode+'-physical',slot if slot < 5 else 8]
                comparison(entries[label],h,h,257*257*(4 if slot < 5 else 1))
        for slot in range(9):
            label = 'old-prepared-all48-'+('slot'+str(slot) if slot < 8 else 'depth')
            if slot in (5,6,7): a,b = raw_hashes['old',slot],raw_hashes['prepared',slot]
            else:
                a = hashes['old-physical',slot]; b = hashes['prepared-physical',slot]
            comparison(entries[label],a,b,257*257*(4 if slot < 8 else 1))
        if node:
            first_view = records[0]['saved_maps']['maps'][1]['sha256']
            comparison(entries['raw-view-eta-all-nodes-exact'],first_view,raw_hashes['old',6],257*257*4)


def audit(packet, probe_receipt=None, node_receipt=None):
    packet = Path(packet)
    if not (packet/'result.json').is_file(): raise ValueError('Missing completed prepared-main result')
    require(sha(node_audit.read(Path(node_audit.__file__))) == PINS['nodeReader']
            and sha(node_audit.read(Path(timing.__file__))) == PINS['timing'], 'Frozen imported CPU reader pin differs')
    result = load(packet,'result.json')
    require(result['schema'] == 'aqualumen-prepared-main-native-v1' and result['nativeGLExecuted'] is True
            and result.get('syntheticOnly',False) is False and result['size'] == 257 and result['phase_seconds'] == 120
            and 'NVIDIA' in result['vendor'] and 'RTX 3080 Ti' in result['renderer']
            and result['rawFormat'] == 'little-endian binary32; bottom-left origin', 'Actual complete MAIN scope differs')
    for key in ('Iris_accepted','visual_accepted','physics_accepted','shipping_accepted','FPS_accepted'):
        require(result[key] is False, 'Unproved acceptance promoted')
    sources,receipt_sha = verify_sources(packet,result,probe_receipt)
    require(node_receipt is not None, 'Root standalone NODE receipt required')
    node_receipt = Path(node_receipt)
    node_data = node_audit.load_json(node_audit.read(node_receipt))
    node_path = node_receipt.parent/node_data['native_output_directory']
    independent_node = node_audit.audit(node_path,node_receipt)
    require(result['node_gate_sha256'] == sha(read(packet,'node-gate-result.json')) == independent_node['resultSHA256']
            and read(packet,'node-gate-result.json') == node_audit.read(node_path/'result.json'), 'Copied NODE gate differs from independently replayed packet')
    require([c['path'] for c in result['cases']] == list(timing.FIXTURES), 'Six fixed MAIN cases required')
    require([p['name'] for p in result['programs']] == [m+'-'+r for m in MODES for r in ROLES], 'Eight linked program roles required')
    for program in result['programs']:
        require(program['linked'] is True and program['stage_types'] == [35632,35633,36487,36488]
                and program['tess_layout'] == [3,4,514,2305,0], 'Linked four-stage program differs')
    cases = []; raw_maps = 0
    for case in result['cases']:
        name = case['path']
        require(type(case['guard']) is int and case['guard'] == int(name.endswith('guard1'))
                and case['positive_cache'] is ('cachepositive' in name)
                and case['aperture_degrees'] == (90 if name.startswith('wide90') else 60 if name.startswith('wide60') else 2), 'Fixed case inputs differ')
        programs, input_shas = verify_inputs(packet,case,sources)
        maps, hashes, count = captures(packet,case,programs); raw_maps += count
        domain = verify_domain(case,maps)
        verify_node_states(case,programs,sources,hashes)
        node_records = case['all48_inputs_classes']
        require(node_records['node_count'] == 48 and node_records['node_order'] == 'r*12+j, r0..3/j0..11', '48 fixed node order differs')
        node_result = verify_nodes(packet/name,node_records['records'],maps['old','reasons'][2][2::4])
        require(node_result['generatedNodePixelPairsPerMode'] == node_records['generated_node_pixel_pairs']
                and node_result['calledNodePixelPairsPerMode'] == node_records['called_node_pixel_pairs']
                and node_records['full_view_countword_ledger_qualified_pixels'] == 257*257, 'Full direct node summary differs')
        cases.append({'path':name, 'domain':domain, 'nodes':node_result,'actualInputReceiptSHA256':input_shas})
    timed = timing.audit(packet)
    for key in ('accepted','main_fixture_qualified','main_differential_accepted'):
        require(result[key] is True, 'Producer summary contradicts independently qualified raw')
    require(result['status'] == 'PASS', 'Producer completion contradicts raw PASS')
    return {'schema':'aqualumen-prepared-main-independent-v1','status':'PASS','accepted':True,
            'auditorGLExecuted':False,'resultSHA256':sha(read(packet,'result.json')),
            'probeReceiptSHA256':receipt_sha, 'sourceSHA256':PINS, 'sourcesVerified':len(sources),
            'standaloneNodeAudit':{k:independent_node[k] for k in ('count','classes','rawRecordsVerified','intervalTriplesVerified','resultSHA256')},
            'cases':cases,'fullCaptureMapsIncludingDepthVerified':raw_maps,'all48DirectMapsVerified':6*48*6,
            'all48ProducerHashRecordsChecked':6*(48*21+47),
            'all48C0DepthTESRawIndependentlyRecomputed':False,
            'timing':timed,'IrisAccepted':False,'naturalVisualAccepted':False,'physicalEnergyAccepted':False,
            'shippingAccepted':False,'MinecraftFPSAccepted':False,
            'scope':'Full saved MAIN maps/repeats/source/input/typed-state differential and all48 direct raw/count ledger; fixed 9-pixel arithmetic subset only. All48 C0/depth/TES neutrality has producer in-memory hashes but no all48 raw slots0–4/depth archives. Standalone absent/unknown coverage is not MAIN branch coverage. Native draw timing is not Minecraft FPS.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("--probe-receipt", type=Path)
    parser.add_argument("--node-receipt", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.packet, args.probe_receipt, args.node_receipt)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as error:
        result = {"schema": "aqualumen-prepared-main-independent-v1", "status": "INCONCLUSIVE",
                  "accepted": False, "auditorGLExecuted": False, "error": str(error)}
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0 if result["accepted"] else 2 if result["status"] == "INCONCLUSIVE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
