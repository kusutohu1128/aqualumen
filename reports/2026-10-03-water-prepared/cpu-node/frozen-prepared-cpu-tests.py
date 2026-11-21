"""Literal old/prepared certificate CPU equivalence; no GL or adoption."""
import hashlib
import json
from pathlib import Path
import subprocess
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'shaders/lib/water_sun_support.glsl'
CANDIDATE=ROOT/'tools/water_sun_prepared.glsl'
OLD_SHA='f9aa1c6763065f776d26b46385ecf82c2b16ac171783b19fa2353de1cef4be7a'

# Type/builtin bridge only; both certificates compile their literal source.
HOST=r'''
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
using uint=std::uint32_t;
struct vec3 { float x,y,z; vec3(float a,float b,float c):x(a),y(b),z(c){} };
uint floatBitsToUint(float x) { uint r;std::memcpy(&r,&x,4);return r; }
float uintBitsToFloat(uint x) { float r;std::memcpy(&r,&x,4);return r; }
namespace old {
#include "OLD_PATH"
}
namespace prepared {
#include "CANDIDATE_PATH"
}
bool same(old::WSPInterval a,prepared::WSPInterval b) {
    return a.lo==b.lo && a.hi==b.hi && a.valid==b.valid;
}
int main() {
    std::string bits[7];
    std::string previous[4];bool haveContext=false;
    prepared::WSPViewContext cached;
    while(std::cin>>bits[0]) {
        for(int i=1;i<7;++i) if(!(std::cin>>bits[i])) return 2;
        float a[7];for(int i=0;i<7;++i) a[i]=uintBitsToFloat(uint(std::stoul(bits[i],nullptr,16)));
        vec3 v(a[0],a[1],a[2]),t(a[3],a[4],a[5]);
        bool reused=haveContext && previous[0]==bits[0] && previous[1]==bits[1]
            && previous[2]==bits[2] && previous[3]==bits[6];
        if(!reused) {
            cached=prepared::waterSunSupportPrepareView(v,a[6]);haveContext=true;
            previous[0]=bits[0];previous[1]=bits[1];previous[2]=bits[2];previous[3]=bits[6];
        }
        auto c=cached;
        auto vx=old::WSP_point(v.x),vy=old::WSP_point(v.y),vz=old::WSP_point(v.z);
        auto e=old::WSP_point(a[6]),one=old::WSP_interval(16777216,16777216);
        auto E=old::WSP_mul(e,e);
        auto V=old::WSP_add(old::WSP_add(old::WSP_mul(vx,vx),old::WSP_mul(vy,vy)),old::WSP_mul(vz,vz));
        auto K2=old::WSP_add(one,old::WSP_mul(E,old::WSP_sub(V,one)));
        auto down=old::WSP_mul(E,old::WSP_mul(vy,vy));
        bool intervals=same(vx,c.vx)&&same(vy,c.vy)&&same(vz,c.vz)
            &&same(E,c.E)&&same(K2,c.K2)&&same(down,c.downScale);
        std::cout<<"{\"old\":"<<old::waterSunSupportClass(v,t,a[6])
            <<",\"prepared\":"<<prepared::waterSunSupportClassPrepared(c,t)
            <<",\"wrapped\":"<<prepared::waterSunSupportClass(v,t,a[6])
            <<",\"intervalsEqual\":"<<(intervals?"true":"false")
            <<",\"contextValid\":"<<(c.valid?"true":"false")
            <<",\"contextReused\":"<<(reused?"true":"false")
            <<",\"nativeGLExecuted\":false}"<<'\n';
    }
}
'''


class PreparedSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if hashlib.sha256(OLD.read_bytes()).hexdigest()!=OLD_SHA:
            raise RuntimeError('Frozen old certificate differs')
        cls.temporary=tempfile.TemporaryDirectory(prefix='aqualumen-prepared-')
        folder=Path(cls.temporary.name);source=folder/'host.cpp';cls.binary=folder/'host'
        source.write_text(HOST.replace('OLD_PATH',str(OLD)).replace('CANDIDATE_PATH',str(CANDIDATE)))
        r=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',
            '-fno-fast-math','-ffp-contract=off',str(source),'-o',str(cls.binary)],
            capture_output=True,text=True)
        if r.returncode:
            cls.temporary.cleanup();raise RuntimeError(r.stderr)

    @classmethod
    def tearDownClass(cls): cls.temporary.cleanup()

    def replay(self,cases):
        r=subprocess.run([str(self.binary)],input=''.join(' '.join(c)+'\n' for c in cases),
            capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        values=[json.loads(line) for line in r.stdout.splitlines()]
        self.assertEqual(len(values),len(cases))
        for value in values:
            self.assertEqual(value['prepared'],value['old'])
            self.assertEqual(value['wrapped'],value['old'])
            self.assertTrue(value['intervalsEqual'])
            self.assertFalse(value['nativeGLExecuted'])
        return values

    def test_prepared_normal_incidence_matches_literal_old_and_public_wrapper(self):
        value=self.replay([['00000000','bf800000','00000000','00000000',
            '3f800000','00000000','3faa9fbe']])[0]
        self.assertEqual(value['old'],1)
        self.assertTrue(value['contextValid'])

    def test_reused_view_context_matches_all_frozen_344_exact_class_bits_and_intervals(self):
        raw=(ROOT/'reports/2026-10-03-water-sun-support/cpu-certificate/cases.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
            '24fdd6ed4ab983a99207883a22ec3b8140fc2aa3fbe364a023308a3b95916e48')
        cases=json.loads(raw)['cases'];self.assertEqual(len(cases),344)
        values=self.replay([c['inputBits'] for c in cases])
        histogram={-1:0,0:0,1:0}
        for case,value in zip(cases,values):
            with self.subTest(name=case['name']):
                self.assertEqual(value['old'],case['cpuClass'])
                histogram[value['prepared']]+=1
        self.assertEqual(histogram,{-1:3,0:29,1:312})
        self.assertGreaterEqual(sum(v['contextReused'] for v in values),282)

    def test_invalid_and_boundary_inputs_never_change_unknown_to_absent_or_supported(self):
        base=['00000000','bf800000','00000000','00000000','3f800000','00000000','3faa9fbe']
        mutations=[(0,'7f800000'),(0,'ff800000'),(0,'7fc00001'),
            (2,'00000001'),(2,'807fffff'),(0,'40400000'),
            (1,'00000000'),(1,'80000000'),(1,'3f800000'),
            (3,'7f800000'),(3,'7fc00001'),(5,'00000001'),
            (4,'00000000'),(4,'80000000'),(4,'bf800000'),
            (6,'3f800000'),(6,'40000001'),(6,'80000000'),(6,'7f800000')]
        cases=[]
        for index,bits in mutations:
            value=base.copy();value[index]=bits;cases.append(value)
        def packed(values):
            return [struct.pack('>f',v).hex() for v in values]
        cases.extend([packed([0,-.5,0,0,1,0,2]),
            packed([2,-2,2,2,2,2,2]),
            packed([0,-1,0,.75,1,0,1.25]),
            packed([1,-.5,0,2,1.25,0,1.25]),
            packed([0,-1,0,.8814129829406738,1,0,1.3329999446868896])])
        values=self.replay(cases)
        self.assertEqual(len(values),24)
        self.assertTrue(all(value['old']==-1 for value in values))

    def test_reused_context_preserves_signed_zero_and_raw_nonunit_inputs(self):
        values=[]
        for raw_vy in (-1.0,-.9):
            for sign in ('00000000','80000000'):
                for target_height in (1.0,2.0):
                    values.append([sign,struct.pack('>f',raw_vy).hex(),sign,
                        sign,struct.pack('>f',target_height).hex(),sign,'3faa9fbe'])
        self.assertTrue(all(v['old']==1 for v in self.replay(values)))

    def test_candidate_retains_literal_frozen_integer_primitives(self):
        original=OLD.read_text().split('int waterSunSupportClass(',1)[0]
        candidate=CANDIDATE.read_text().split('// Standalone CPU-only candidate.',1)[0]
        self.assertEqual(candidate.replace('AQUALUMEN_WATER_SUN_PREPARED_GLSL',
            'AQUALUMEN_WATER_SUN_SUPPORT_GLSL'),original)
        self.assertEqual(hashlib.sha256(OLD.read_bytes()).hexdigest(),OLD_SHA)


if __name__=='__main__': unittest.main()
