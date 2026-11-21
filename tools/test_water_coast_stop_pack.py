import unittest
from water_coast_stop_pack import ROOT,transform,verify


class CoastStopPackTest(unittest.TestCase):
    def setUp(self):
        self.original={p.relative_to(ROOT).as_posix():p.read_bytes() for p in sorted([*(ROOT/'shaders').rglob('*'),ROOT/'LICENSE']) if p.is_file()}
        self.files=transform(self.original)

    def test_exact_original_source_recovery(self):
        self.assertEqual(len(verify(self.original,self.files)),5)

    def test_one_original_trace_and_depth_lookup(self):
        old=self.original['shaders/gbuffers_water.fsh'].decode()
        new=self.files['shaders/gbuffers_water.fsh'].decode()
        for call in ('reflectionTrace(','refractionTrace(','texture(depthtex1,'):
            self.assertEqual(old.count(call),new.count(call))

    def test_literal_nonwater_zero_and_iris_annotations(self):
        fs=self.files['shaders/gbuffers_water.fsh'].decode()
        branch=fs[fs.index('if (materialId!=10000.0)'):fs.index('vec3 viewPos=')]
        for i in range(1,8):self.assertIn(f'gl_FragData[{i}]=vec4(0.0);',branch)
        prepare=self.files['shaders/prepare.fsh'].decode()
        for i in range(9,16):self.assertIn(f'colortex{i}ClearColor = vec4(0.0,0.0,0.0,0.0);',prepare)


if __name__=='__main__':unittest.main()
