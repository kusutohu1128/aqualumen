"""Public CPU/build contracts only; these tests never create a GL context."""
import json
from pathlib import Path
import subprocess
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
HELPER=ROOT/'shaders/lib/water_snell_inverse.glsl'

class Construction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch=tempfile.TemporaryDirectory()
        cls.binary=Path(cls.scratch.name)/'probe'
        libs=subprocess.check_output(['pkg-config','--libs','epoxy','egl'],text=True).split()
        subprocess.run(['g++','-std=c++17','-O0','-Wall','-Wextra',
                        str(ROOT/'tools/water_snell_boundary_gpu.cpp'),'-o',str(cls.binary),*libs],check=True)

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def test_public_cpu_construction_contains_literal_actual_helper_and_node_outputs(self):
        result=subprocess.run([str(self.binary),'--cpu-construction',str(HELPER)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout)
        self.assertFalse(report['glExecuted'])
        self.assertIn(HELPER.read_text(),report['fragmentSource'])
        self.assertIn('waterSnellNode(wsView,wsTarget,wsEta)',report['fragmentSource'])
        self.assertIn('vec4(node.transmittedCosine,node.transmission,node.jacobian,1.0)',report['fragmentSource'])
        self.assertTrue(report['fragmentSource'].startswith('#version 330 compatibility\n'))

    def test_invalid_binary_length_is_rejected_before_output_or_gl(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=Path(directory)/'bad.f32';fixture.write_bytes(b'x'*27)
            output=Path(directory)/'output'
            result=subprocess.run([str(self.binary),str(HELPER),str(fixture),str(output)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('seven-float records',result.stderr)
            self.assertFalse(output.exists())

    def test_nonfinite_fixture_is_rejected_before_output_or_gl(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=Path(directory)/'bad.f32'
            fixture.write_bytes(struct.pack('<7f',0,-1,0,0,1,float('nan'),1.333))
            output=Path(directory)/'output'
            result=subprocess.run([str(self.binary),str(HELPER),str(fixture),str(output)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('finite input',result.stderr)
            self.assertFalse(output.exists())

if __name__=='__main__':unittest.main()
