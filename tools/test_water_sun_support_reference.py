"""Public support-certificate behavior, CPU only; not shader adoption."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from tools.water_sun_support_reference import binary32, classify

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'tools/water_sun_support_reference.py'

# Tiny type/builtin adapter only. Candidate arithmetic is literal GLSL include.
HOST = r'''
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
using uint = std::uint32_t;
struct vec3 { float x, y, z; vec3(float a,float b,float c):x(a),y(b),z(c){} };
uint floatBitsToUint(float x) { uint r; std::memcpy(&r,&x,4); return r; }
float uintBitsToFloat(uint x) { float r; std::memcpy(&r,&x,4); return r; }
#include "GLSL_PATH"
int main(int argc,char** argv) {
    if(argc!=8) return 2;
    float a[7]; for(int i=0;i<7;i++) a[i]=uintBitsToFloat(uint(std::stoul(argv[i+1],nullptr,16)));
    std::cout << "{\"class\":" << waterSunSupportClass(vec3(a[0],a[1],a[2]),
        vec3(a[3],a[4],a[5]),a[6]) << ",\"nativeGLExecuted\":false}" << '\n';
}
'''


class SupportReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='aqualumen-support-')
        folder = Path(cls.temporary.name)
        source = folder / 'host.cpp'
        source.write_text(HOST.replace('GLSL_PATH',
            str(ROOT / 'shaders/lib/water_sun_support.glsl')))
        cls.binary = folder / 'host'
        result = subprocess.run(['g++', '-std=c++17', '-O2',
            '-Wall', '-Wextra', '-Werror', '-fno-fast-math',
            '-ffp-contract=off', '-fsingle-precision-constant', str(source),
            '-o', str(cls.binary)], capture_output=True, text=True)
        if result.returncode:
            cls.temporary.cleanup()
            raise RuntimeError(result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def host_bits(self, bits):
        result = subprocess.run([str(self.binary), *bits],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertFalse(value['nativeGLExecuted'])
        return value['class']

    def host(self, view, target, eta=1.3329999446868896):
        return self.host_bits([binary32(v)[1] for v in list(view)+list(target)+[eta]])

    def test_normal_incidence_is_certified_supported_through_cli(self):
        result = subprocess.run([sys.executable, '-B', str(CLI), '--node',
            '0', '-1', '0', '0', '1', '0', '1.3329999446868896'],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value['class'], 1)
        self.assertEqual(value['viewBits'], ['00000000', 'bf800000', '00000000'])
        self.assertFalse(value['nativeGLExecuted'])

    def test_actual_glsl_normal_incidence_is_certified_supported(self):
        self.assertEqual(self.host((0, -1, 0), (0, 1, 0)), 1)

    def test_captured_iris_ten_absent_four_supported_are_certified(self):
        file = ROOT / 'reports/2026-10-03-water-snell-main/iris-old-inputs/input-audit.json'
        raw = file.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
            '0e8885806c818b7bcc0782efb4d6117174268b3ca1c233834969e2e8a9159a99')
        points = [p for p in json.loads(raw)['points'] if p['firstReason']]
        self.assertEqual(len(points), 14)
        histogram = {0: 0, 1: 0}
        for point in points:
            with self.subTest(pixel=(point['x'], point['y'])):
                view, target = point['view_requested'][:3], point['first_target_reason'][:3]
                exact = classify(view, target)['class']
                references = point['reference']['references']
                self.assertEqual([p['precision'] for p in references], [80, 120])
                self.assertTrue(all(p['supported'] == (exact == 1) for p in references))
                self.assertEqual(self.host(view, target), exact)
                histogram[exact] += 1
        self.assertEqual(histogram, {0: 10, 1: 4})

    def test_exact_forward_boundary_unknown_and_strict_ulp_neighbors_certified(self):
        # eta=5/4, v=-Y, t=(3/4,1,0) gives K2*U=E*B^2 exactly.
        view, eta = (0, -1, 0), 1.25
        targets = [struct.unpack('>f', struct.pack('>I', bits))[0]
                   for bits in (0x3f3fffff, 0x3f400000, 0x3f400001)]
        self.assertEqual([classify(view, (x, 1, 0), eta)['class']
                          for x in targets], [1, -1, 0])
        # One ULP here is one exact Q24 unit; directed intervals separate the
        # strict signs. Equality, rather than an arbitrary ULP radius, is unknown.
        self.assertEqual([self.host(view, (x, 1, 0), eta)
                          for x in targets], [1, -1, 0])

    def test_exact_downward_boundary_stays_unknown_even_if_other_gate_absent(self):
        # Both sides of the downward comparison are 2225/1024 exactly.
        view, target, eta = (1, -.5, 0), (2, 1.25, 0), 1.25
        self.assertEqual(classify(view, target, eta)['class'], -1)
        self.assertEqual(self.host(view, target, eta), -1)

    def test_strict_supported_but_overlapping_interval_remains_unknown(self):
        # Actual binary32 target lies just inside support; Q24 multiplication
        # intervals overlap. Exact support is not authority to guess shader0/1.
        target = (.8814129829406738, 1, 0)
        self.assertEqual(classify((0, -1, 0), target)['class'], 1)
        self.assertEqual(self.host((0, -1, 0), target), -1)

    def test_invalid_singular_subnormal_and_overflow_domains_never_zero(self):
        base = ['0', 'bf800000', '0', '0', '3f800000', '0', '3faa9fbe']
        mutations = [(0, '7f800000'), (0, '7fc00001'), (2, '00000001'),
            (2, '807fffff'), (6, '3f800000'), (6, '80000000'),
            (6, '7f800000'), (1, '0'), (4, 'bf800000'), (0, '40400000')]
        for index, bits in mutations:
            with self.subTest(index=index, bits=bits):
                values = base.copy()
                values[index] = bits
                self.assertEqual(self.host_bits(values), -1)
        # Positive raw-view transmitted norm is required; K2=-2 here.
        self.assertEqual(self.host((0, -.5, 0), (0, 1, 0), 2), -1)
        # Bounded inputs but intermediate K2*U exceeds Q24 int endpoint range.
        self.assertEqual(self.host((2, -2, 2), (2, 2, 2), 2), -1)

    def test_raw_nonunit_view_and_target_direction_are_not_normalized_away(self):
        view = (0, -.9, 0)
        for target in ((0, 1, 0), (0, 2, 0)):
            with self.subTest(target=target):
                self.assertEqual(classify(view, target)['class'], 1)
                self.assertEqual(self.host(view, target), 1)
        # Normalizing this raw view would change its K2 sign and falsely support.
        self.assertEqual(classify((0, -.5, 0), (0, 1, 0))['class'], -1)
        self.assertEqual(self.host((0, -.5, 0), (0, 1, 0)), -1)

    def test_fixed_325_raw_nodes_never_receive_a_false_certificate(self):
        folder = ROOT / 'reports/2026-10-03-water-snell-boundary/fixed-inputs'
        raw = (folder / 'cases.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
            'a844555de190b04afd6989f6b1125a051950e4d441bc12ec7a6b4240ede8e792')
        packed = (folder / 'inputs.f32').read_bytes()
        self.assertEqual(hashlib.sha256(packed).hexdigest(),
            '7e181a8d6b4494a6952e1d51af369b935273dda94039eaba2e362ad6affb2d06')
        cases = json.loads(raw)['cases']
        self.assertEqual(len(cases), 325)
        histogram = {0: 0, 1: 0, -1: 0}
        for index, case in enumerate(cases):
            with self.subTest(name=case['name']):
                values = case['input']
                self.assertEqual(struct.pack('<7f', *values),
                                 packed[28*index:28*(index+1)])
                exact = classify(values[:3], values[3:6], values[6])['class']
                reference = case['reference']['references']
                self.assertEqual([p['precision'] for p in reference], [80, 120])
                self.assertIn(exact, (0, 1))
                self.assertTrue(all(p['supported'] == (exact == 1) for p in reference))
                candidate = self.host(values[:3], values[3:6], values[6])
                self.assertIn(candidate, (-1, exact))
                histogram[candidate] += 1
        self.assertGreaterEqual(histogram[1], 289) # saved288+normal control.
        self.assertGreater(histogram[0], 0)


if __name__ == '__main__':
    unittest.main()
