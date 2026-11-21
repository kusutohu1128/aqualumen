"""Public pure-node GPU probe construction only. NEVER execute GL here."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'shaders/lib/water_sun_support.glsl'
CORPUS = ROOT / 'reports/2026-10-03-water-sun-support/cpu-certificate/cases.json'


class Construction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix='aqualumen-support-node-')
        cls.binary = Path(cls.scratch.name) / 'probe'
        libs = subprocess.check_output(['pkg-config', '--libs', 'epoxy', 'egl'], text=True).split()
        result = subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra',
            '-Werror', '-fno-fast-math', '-ffp-contract=off',
            str(ROOT / 'tools/water_sun_support_node_probe.cpp'),
            '-o', str(cls.binary), *libs, '-lcrypto'], capture_output=True, text=True)
        if result.returncode:
            cls.scratch.cleanup()
            raise RuntimeError(result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def test_cpu_contract_pins_inputs_and_constructs_literal_integer_capture(self):
        result = subprocess.run([str(self.binary), '--cpu-contract', str(MODULE), str(CORPUS)],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertFalse(value['nativeGLExecuted'])
        self.assertEqual(value['count'], 344)
        self.assertEqual(value['classes'], {'absent': 29, 'supported': 312, 'unknown': 3})
        self.assertEqual(value['moduleSHA256'],
            'f9aa1c6763065f776d26b46385ecf82c2b16ac171783b19fa2353de1cef4be7a')
        self.assertEqual(value['corpusSHA256'],
            '24fdd6ed4ab983a99207883a22ec3b8140fc2aa3fbe364a023308a3b95916e48')
        self.assertTrue(value['fragmentSource'].startswith('#version 330 compatibility\n'))
        self.assertIn(MODULE.read_text(), value['fragmentSource'])
        self.assertEqual(value['rawFormat'], 'two RGBA32UI targets; class+1 and seven raw binary32 bit patterns')

    def test_changed_module_is_rejected_before_gpu_or_output_creation(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-support-bad-module-') as folder:
            path = Path(folder)
            changed = path / 'changed.glsl'
            changed.write_bytes(MODULE.read_bytes() + b'\n// changed\n')
            output = path / 'never-created'
            result = subprocess.run([str(self.binary), '--gpu', str(changed),
                str(CORPUS), str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('module source SHA differs', result.stderr)
            self.assertFalse(output.exists())

    def test_changed_corpus_is_rejected_before_gpu_or_output_creation(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-support-bad-corpus-') as folder:
            path = Path(folder)
            changed = path / 'changed.json'
            changed.write_bytes(CORPUS.read_bytes() + b'\n')
            output = path / 'never-created'
            result = subprocess.run([str(self.binary), '--gpu', str(MODULE),
                str(changed), str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('corpus source SHA differs', result.stderr)
            self.assertFalse(output.exists())

    def test_existing_output_is_preserved_and_rejected_before_gpu(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-support-existing-') as folder:
            output = Path(folder)
            marker = output / 'user-marker.txt'
            marker.write_text('preserve me')
            result = subprocess.run([str(self.binary), '--gpu', str(MODULE),
                str(CORPUS), str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('NEW output required', result.stderr)
            self.assertEqual(marker.read_text(), 'preserve me')
            self.assertEqual(list(output.iterdir()), [marker])


if __name__ == '__main__':
    unittest.main()
