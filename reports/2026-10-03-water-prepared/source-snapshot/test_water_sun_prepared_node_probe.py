"""Public differential certificate construction; NEVER execute successful GL."""
import hashlib
import ast
import json
from pathlib import Path
import subprocess
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'shaders/lib/water_sun_support.glsl'
PREPARED=ROOT/'tools/water_sun_prepared.glsl'
CORPUS=ROOT/'reports/2026-10-03-water-sun-support/cpu-certificate/cases.json'


class Construction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch=tempfile.TemporaryDirectory(prefix='aqualumen-prepared-node-')
        cls.binary=Path(cls.scratch.name)/'probe'
        libs=subprocess.check_output(['pkg-config','--libs','epoxy','egl'],text=True).split()
        result=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',
            '-fno-fast-math','-ffp-contract=off',str(ROOT/'tools/water_sun_prepared_node_probe.cpp'),
            '-o',str(cls.binary),*libs,'-lcrypto'],capture_output=True,text=True)
        if result.returncode:
            cls.scratch.cleanup();raise RuntimeError(result.stderr)

    @classmethod
    def tearDownClass(cls): cls.scratch.cleanup()

    def test_public_cpu_contract_constructs_literal_old_wrapper_and_reused_programs(self):
        result=subprocess.run([str(self.binary),'--cpu-contract',str(OLD),str(PREPARED),str(CORPUS)],
            capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        value=json.loads(result.stdout)
        self.assertEqual(value['schema'],'aqualumen-prepared-node-construction-v1')
        self.assertFalse(value['nativeGLExecuted'])
        self.assertEqual(value['count'],376)
        self.assertEqual(value['frozenCount'],344)
        self.assertEqual(value['additionalCount'],32)
        self.assertEqual(value['roles'],['old','wrapper','reused'])
        self.assertEqual(value['intervals'],['vx','vy','vz','E','K2','downScale'])
        self.assertEqual(value['targetCount'],8)
        self.assertEqual(value['sourceSHA256']['old'],hashlib.sha256(OLD.read_bytes()).hexdigest())
        self.assertEqual(value['sourceSHA256']['prepared'],hashlib.sha256(PREPARED.read_bytes()).hexdigest())
        sources=value['fragmentSources']
        self.assertIn(OLD.read_text(),sources['old'])
        for role in ('wrapper','reused'): self.assertIn(PREPARED.read_text(),sources[role])
        self.assertIn('waterSunSupportClassPrepared(context,t)',sources['reused'])
        self.assertLess(sources['reused'].index('waterSunSupportPrepareView'),sources['reused'].index('for (int node='))

    def test_existing_gpu_output_rejects_before_any_gl_and_preserves_user_file(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-prepared-existing-') as folder:
            path=Path(folder);marker=path/'keep.txt';marker.write_text('user')
            result=subprocess.run([str(self.binary),'--gpu',str(OLD),str(PREPARED),str(CORPUS),str(path)],
                capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertIn('NEW output required',result.stderr)
            self.assertEqual(list(path.iterdir()),[marker])
            self.assertEqual(marker.read_text(),'user')

    def test_additional_fixture_exactly_reuses_pinned_cpu_inputs_and_literal_classes(self):
        from tools.test_water_sun_prepared import HOST
        fixture=ROOT/'tools/test_water_sun_prepared.py'
        self.assertEqual(hashlib.sha256(fixture.read_bytes()).hexdigest(),
            'f4abe4cbde553c44258e2c2f2f9e437809f67af9c350823ac4627dcfb1a5bb67')
        tree=ast.parse(fixture.read_text());cases=[]
        names={'test_invalid_and_boundary_inputs_never_change_unknown_to_absent_or_supported':'cases',
            'test_reused_context_preserves_signed_zero_and_raw_nonunit_inputs':'values'}
        for name,key in names.items():
            method=next(node for node in ast.walk(tree) if isinstance(node,ast.FunctionDef) and node.name==name)
            prefix=[]
            for statement in method.body:
                if any(isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
                    and node.func.attr=='replay' for node in ast.walk(statement)): break
                prefix.append(statement)
            env={'struct':struct}
            exec(compile(ast.Module(body=prefix,type_ignores=[]),str(fixture),'exec'),env)
            cases.extend(env[key])
        result=subprocess.run([str(self.binary),'--cpu-contract',str(OLD),str(PREPARED),str(CORPUS)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        additional=json.loads(result.stdout)['additionalInputs']
        self.assertFalse(additional['physicalOracle'])
        self.assertEqual([entry['inputBits'] for entry in additional['cases']],
            [[int(bits,16) for bits in case] for case in cases])
        with tempfile.TemporaryDirectory(prefix='aqualumen-prepared-literal-') as folder:
            source=Path(folder)/'host.cpp';binary=Path(folder)/'host'
            source.write_text(HOST.replace('OLD_PATH',str(OLD)).replace('CANDIDATE_PATH',str(PREPARED)))
            compiled=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',
                '-fno-fast-math','-ffp-contract=off',str(source),'-o',str(binary)],capture_output=True,text=True)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            replay=subprocess.run([str(binary)],input=''.join(' '.join(c)+'\n' for c in cases),capture_output=True,text=True)
            self.assertEqual(replay.returncode,0,replay.stderr)
            values=[json.loads(line) for line in replay.stdout.splitlines()]
            self.assertEqual(len(values),32)
            self.assertEqual([v['old'] for v in values],[c['cpuClass'] for c in additional['cases']])
            self.assertTrue(all(v['old']==v['prepared']==v['wrapped'] and v['intervalsEqual'] for v in values))

    def test_changed_old_prepared_or_corpus_rejects_before_gl_or_output_creation(self):
        for index,original in enumerate((OLD,PREPARED,CORPUS)):
            with self.subTest(source=original.name),tempfile.TemporaryDirectory(prefix='aqualumen-prepared-tamper-') as folder:
                changed=Path(folder)/original.name;changed.write_bytes(original.read_bytes()+b'\n')
                arguments=[str(OLD),str(PREPARED),str(CORPUS)];arguments[index]=str(changed)
                output=Path(folder)/'never-created'
                result=subprocess.run([str(self.binary),'--gpu',*arguments,str(output)],capture_output=True,text=True)
                self.assertEqual(result.returncode,2)
                self.assertIn('source SHA differs',result.stderr)
                self.assertFalse(output.exists())

    def test_public_construction_declares_complete_actual_route_storage_and_location_evidence(self):
        result=subprocess.run([str(self.binary),'--cpu-contract',str(OLD),str(PREPARED),str(CORPUS)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['runtimeCaptureFields'],
            ['allEightDrawBuffers','targets','actualOutputLocations'])


if __name__=='__main__': unittest.main()
