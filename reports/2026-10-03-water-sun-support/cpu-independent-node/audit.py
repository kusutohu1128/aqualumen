"""Read-only CPU audit of saved pure-support GPU344 captures. NEVER GL/app."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
MODULE_SHA = 'f9aa1c6763065f776d26b46385ecf82c2b16ac171783b19fa2353de1cef4be7a'
CORPUS_SHA = '24fdd6ed4ab983a99207883a22ec3b8140fc2aa3fbe364a023308a3b95916e48'
SOURCE_PINS = {
    'tools/water_sun_support_node_probe.cpp': 'f183963ee155c89dcbd8be3e36ccd7d313ccadccde4d1d9bb5b4c2ab16ae16f7',
    'tools/water_snell_boundary_reference.py': '511770d7c090a8ea5423cb7afd30dd655a2a09253c10f27ef0921215ba0bc9e0',
    'reports/2026-10-03-water-snell-boundary/fixed-inputs/cases.json': 'a844555de190b04afd6989f6b1125a051950e4d441bc12ec7a6b4240ede8e792',
    'reports/2026-10-03-water-snell-main/iris-old-inputs/input-audit.json': '0e8885806c818b7bcc0782efb4d6117174268b3ca1c233834969e2e8a9159a99',
}
PREFIX = b'#version 330 compatibility\n'
VERTEX = PREFIX + b'void main(){gl_Position=gl_Vertex;}\n'
SUFFIX = b'''\nuniform uvec3 wspViewBits; uniform uvec3 wspTargetBits; uniform uint wspEtaBits;
layout(location=0) out uvec4 wspClassAndView;
layout(location=1) out uvec4 wspTargetAndEta;
void main(){vec3 v=uintBitsToFloat(wspViewBits);vec3 t=uintBitsToFloat(wspTargetBits);
float eta=uintBitsToFloat(wspEtaBits);int c=waterSunSupportClass(v,t,eta);
wspClassAndView=uvec4(uint(c+1),floatBitsToUint(v));
wspTargetAndEta=uvec4(floatBitsToUint(t),floatBitsToUint(eta));}
'''
HOST = r'''
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <string>
using uint=std::uint32_t;
struct vec3 {float x,y,z; vec3(float a,float b,float c):x(a),y(b),z(c){}};
uint floatBitsToUint(float x){uint b;std::memcpy(&b,&x,4);return b;}
float uintBitsToFloat(uint b){float x;std::memcpy(&x,&b,4);return x;}
#include "MODULE_PATH"
int main(int argc,char** argv){
static_assert(sizeof(float)==4 && std::numeric_limits<float>::is_iec559);
if(argc!=8)return 2;
float a[7];
for(int i=0;i<7;i++)a[i]=uintBitsToFloat(uint(std::stoul(argv[i+1],nullptr,16)));
std::cout<<waterSunSupportClass(vec3(a[0],a[1],a[2]),vec3(a[3],a[4],a[5]),a[6])<<'\n';}
'''


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, why):
    if not condition:
        raise ValueError(why)


def independent_fraction(bits):
    """Direct homogeneous polynomial proof; no candidate/oracle imports."""
    values = struct.unpack('<7f', struct.pack('<7I', *bits))
    v, t, eta = list(map(Fraction, values[:3])), list(map(Fraction, values[3:6])), Fraction(values[6])
    require(eta > 1 and v[1] < 0 and t[1] > 0, 'unexpected physical corpus domain')
    E, V, U, B = eta*eta, sum(x*x for x in v), sum(x*x for x in t), sum(x*y for x, y in zip(v, t))
    K2 = 1+E*(V-1)
    require(V > 0 and U > 0 and K2 > 0, 'unexpected singular physical corpus domain')
    downward, forward = E*v[1]*v[1]*U-K2*t[1]*t[1], E*B*B-K2*U
    if downward == 0 or forward == 0 or B == 0:
        return -1
    return 0 if downward < 0 or forward < 0 or B > 0 else 1


def fresh_cpu(module, cases):
    with tempfile.TemporaryDirectory(prefix='aqualumen-independent-support-') as folder:
        root = Path(folder)
        host = HOST.replace('MODULE_PATH', str(module.resolve()).replace('\\', '\\\\').replace('"', '\\"'))
        source, binary = root / 'host.cpp', root / 'host'
        source.write_text(host)
        flags = ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                 '-fno-fast-math', '-ffp-contract=off', '-fsingle-precision-constant']
        compiled = subprocess.run(['g++', *flags, str(source), '-o', str(binary)],
                                  capture_output=True, text=True)
        require(compiled.returncode == 0, 'CPU host compile: '+compiled.stderr)
        result = []
        for case in cases:
            replay = subprocess.run([str(binary), *case['inputBits']], capture_output=True, text=True)
            require(replay.returncode == 0, 'CPU host replay: '+replay.stderr)
            result.append(int(replay.stdout.strip()))
        return result, sha(host.encode()), flags


def audit(native):
    source_hashes = {}
    for name, expected in SOURCE_PINS.items():
        source_hashes[name] = sha((ROOT / name).read_bytes())
        require(source_hashes[name] == expected, 'changed frozen source/input: '+name)
    files = {name: (native / name).read_bytes() for name in (
        'module.glsl', 'cases.json', 'attached-vertex.glsl', 'attached-fragment.glsl',
        'input-bits.u32', 'slot0.rgba32ui', 'slot1.rgba32ui',
        'repeat-slot0.rgba32ui', 'repeat-slot1.rgba32ui', 'result.json')}
    digests = {name: sha(raw) for name, raw in files.items()}
    require(digests['module.glsl'] == MODULE_SHA, 'saved module pin differs')
    require(digests['cases.json'] == CORPUS_SHA, 'saved corpus pin differs')
    require(files['attached-vertex.glsl'] == VERTEX, 'actual vertex bytes differ')
    require(files['attached-fragment.glsl'] == PREFIX+files['module.glsl']+SUFFIX,
            'actual fragment does not contain exact literal module/caller/output contract')
    corpus, metadata = json.loads(files['cases.json']), json.loads(files['result.json'])
    cases, count = corpus['cases'], corpus['count']
    require(count == 344 and len(cases) == count, 'fixed344 count differs')
    bits = [[int(value, 16) for value in case['inputBits']] for case in cases]
    require(all(len(values) == 7 for values in bits), 'seven raw bit fields required')
    packed = b''.join(struct.pack('<7I', *values) for values in bits)
    require(files['input-bits.u32'] == packed, 'actual saved input bytes differ')
    require(metadata['count'] == count and metadata['width'] == count and metadata['height'] == 1,
            'actual capture dimensions differ')
    require(metadata['targetInternalFormat'] == 36208 and metadata['actualOutputLocations'] == [0, 1],
            'actual unsigned integer storage/routing differs')
    require('RTX 3080 Ti' in metadata['renderer'], 'actual RTX3080Ti renderer not recorded')
    require(metadata['nativeGLExecuted'] and not metadata['waterMainExecuted']
            and not metadata['IrisAccepted'] and not metadata['shippingAccepted'], 'scope flags differ')
    require(metadata['rawByteOrder'] == 'little-endian uint32', 'raw byte order differs')
    require(metadata['moduleSHA256'] == MODULE_SHA and metadata['corpusSHA256'] == CORPUS_SHA
            and metadata['queriedVertexSHA256'] == digests['attached-vertex.glsl']
            and metadata['queriedFragmentSHA256'] == digests['attached-fragment.glsl']
            and metadata['inputBitsSHA256'] == digests['input-bits.u32'], 'declared source/input digest differs')
    uniforms = metadata['uniforms']
    require([(u['name'], u['type'], u['size']) for u in uniforms] ==
        [('wspViewBits', 36295, 1), ('wspTargetBits', 36295, 1), ('wspEtaBits', 5125, 1)],
        'actual active integer uniform contract differs')
    require(len({u['location'] for u in uniforms}) == 3 and all(u['location'] >= 0 for u in uniforms),
            'active integer locations invalid')
    uploads = metadata['uploads']
    require(len(uploads) == 2*count, 'two full actual upload/query records required')
    fixed_state = None
    for number, upload in enumerate(uploads):
        repeat, index = divmod(number, count)
        require(upload['repeat'] == repeat and upload['index'] == index, 'actual upload ordering differs')
        require(upload['beforeBits'] == bits[index] and upload['afterBits'] == bits[index],
                'actual integer uniform before/after differs')
        state = upload['actualState']
        require(state['program'] > 0 and state['drawFBO'] > 0 and state['readFBO'] == state['drawFBO']
            and state['viewport'] == [index, 0, 1, 1] and state['packAlignment'] == 1
            and state['pixelPackBuffer'] == 0 and state['disabledRasterCapabilities']
            and state['drawBuffers'] == [36064, 36065], 'actual draw state differs')
        triple = (state['program'], state['drawFBO'], state['readFBO'])
        if fixed_state is None:
            fixed_state = triple
        require(triple == fixed_state, 'actual program/framebuffer changed')
    captures = []
    for repeat in range(2):
        row = []
        for slot in range(2):
            base = ('repeat-' if repeat else '')+'slot'+str(slot)
            name = base+'.rgba32ui'
            require(len(files[name]) == count*16, 'actual raw unsigned target length differs')
            require(metadata['rawSHA256'][base] == digests[name], 'declared raw digest differs')
            row.append(struct.unpack('<'+str(count*4)+'I', files[name]))
        captures.append(row)
    require(captures[0] == captures[1], 'actual unsigned captures are not repeat byte-identical')
    cpu, host_sha, flags = fresh_cpu(native / 'module.glsl', cases)
    exact, gpu = [], []
    require(len(metadata['results']) == count, 'saved result record count differs')
    for index, case in enumerate(cases):
        raw0, raw1 = captures[0][0][4*index:4*index+4], captures[0][1][4*index:4*index+4]
        require(list(raw0[1:])+list(raw1) == bits[index], 'actual shader raw7bit echo differs')
        require(raw0[0] in (0, 1, 2), 'unqualified integer class code')
        gpu.append(raw0[0]-1)
        exact.append(independent_fraction(bits[index]))
        require(exact[-1] == case['exactClass'], 'stored exact class disagrees with direct Fraction proof')
        require(cpu[index] == case['cpuClass'], 'fresh CPU differs from frozen corpus')
        saved = metadata['results'][index]
        require(saved['index'] == index and saved['gpuClass'] == gpu[-1]
                and saved['cpuClass'] == cpu[index] and saved['exactClass'] == exact[-1]
                and saved['rawInputEchoExact'], 'declared result differs from actual integer readback')
    # Verify339 pre-existing references independently of the corpus class tags.
    old = json.loads((ROOT / 'reports/2026-10-03-water-snell-boundary/fixed-inputs/cases.json').read_text())['cases']
    actual = json.loads((ROOT / 'reports/2026-10-03-water-snell-main/iris-old-inputs/input-audit.json').read_text())['points']
    refs = [case['reference'] for case in old] + [p['reference'] for p in actual if p['firstReason']]
    require(len(refs) == 339, 'frozen339 reference count differs')
    for index, reference in enumerate(refs):
        comparisons = reference['references']
        require([r['precision'] for r in comparisons] == [80, 120]
                and all(r['supported'] == (exact[index] == 1) for r in comparisons),
                'independent exact proof disagrees with frozen Decimal80/120')
    same = gpu == cpu
    safe = all(g == -1 or g == e for g, e in zip(gpu, exact))
    census = Counter(gpu)
    report = dict(schema='aqualumen-support-node-independent-cpu-audit-v1',
        status='PASS' if same and safe else 'RED', accepted=same and safe, count=count,
        savedNativeRenderer=metadata['renderer'], savedNativeGL=metadata['GL'], savedNativeGLSL=metadata['GLSL'],
        sourceSHA256=source_hashes, nativeArtifactSHA256=digests,
        auditSourceSHA256=sha(Path(__file__).read_bytes()), freshCPUHostSourceSHA256=host_sha,
        freshCPUCompileFlags=flags, literalSourcesAndCorpusPinned=True,
        actualTypedUniformBeforeAfterAndStateQualified=True, actualUniformQueries=2*count,
        rawSevenInputBitsExact=True, rawIntegerStorageAndRoutingQualified=True,
        repeatByteIdentical=True, freshLiteralCPUReplayExact=same,
        noFalseIndependentFractionCertificate=safe, frozenDecimal80_120For339Agree=True,
        classes=dict(absent=census[0], supported=census[1], unknown=census[-1]),
        unknownIndices=[i for i, value in enumerate(gpu) if value == -1],
        newBoundaryWitnesses=[dict(index=i, name=cases[i]['name'], rawBits=cases[i]['inputBits'],
            actualGPUClass=gpu[i], freshCPUClass=cpu[i], independentFractionClass=exact[i]) for i in range(339, 344)],
        nativeGLExecutedByAudit=False, savedGPUCaptureIndependentlyQualified=True,
        waterMainAccepted=False, continuousCapAccepted=False, energyAccepted=False,
        visualAccepted=False, performanceAccepted=False, IrisAccepted=False, shippingAccepted=False,
        scope='Saved pure-module344 raw unsigned captures only. Fresh CPU literal replay and direct Fraction proof, not native water-main/whole-cap/pixel-AA/energy/visual adoption. No GL/app or raw mutation.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native', type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.native)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0 if result['accepted'] else 1
    except (ValueError, OSError, KeyError, TypeError, struct.error) as failure:
        print(json.dumps(dict(status='INCONCLUSIVE', reason=str(failure),
            nativeGLExecutedByAudit=False, shippingAccepted=False)))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
