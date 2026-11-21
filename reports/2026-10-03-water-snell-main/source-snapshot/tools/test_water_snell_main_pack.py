"""Public CPU packaging contracts; no GL/game or physical acceptance."""
from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
PARENT = ROOT / 'reports/2026-10-03-water-residual-sun-reasons/cpu-pack/Aqualumen-ShoreProbe-world-native-sun-reasons-v1.zip'


class SnellMainPackTests(unittest.TestCase):
    def build(self, destination, mode):
        return subprocess.run([
            sys.executable, '-B', str(ROOT/'tools/water_snell_main_pack.py'),
            str(destination), '--mode', mode,
        ], capture_output=True, text=True)

    def test_old_cli_preserves_every_parent_shader_byte(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-snell-pack-') as folder:
            destination = Path(folder)/'old.zip'
            result = self.build(destination, 'old')
            self.assertEqual(result.returncode, 0, result.stderr)
            with ZipFile(PARENT) as parent, ZipFile(destination) as built:
                for name in parent.namelist():
                    if name.startswith('shaders/'):
                        self.assertEqual(built.read(name), parent.read(name), name)

    def test_stable_cli_recovers_parent_and_hoists_only_extension_directive(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-snell-pack-') as folder:
            destination = Path(folder)/'stable.zip'
            result = self.build(destination, 'stable')
            self.assertEqual(result.returncode, 0, result.stderr)
            from water_snell_main_pack import recover_helper, EXTENSION, NODE_EXTENSION_GUARD
            with ZipFile(PARENT) as parent, ZipFile(destination) as built:
                helper = built.read('shaders/lib/water_residual_sun.glsl')
                self.assertEqual(recover_helper(helper), parent.read('shaders/lib/water_residual_sun.glsl'))
                water = built.read('shaders/gbuffers_water.fsh')
                self.assertTrue(water.startswith(b'#version 330 compatibility\n'+EXTENSION.encode()))
                self.assertEqual(water.replace(EXTENSION.encode(), b'', 1), parent.read('shaders/gbuffers_water.fsh'))
                original = built.read('PARENT-SNELL-MAIN-node.glsl')
                self.assertEqual(hashlib.sha256(original).hexdigest(),
                    '4338e67785ec1bb5cf9fb7dca99f31d1913081277bae5afcbf9f46e3d4330e27')
                adapted = built.read('shaders/lib/water_snell_inverse.glsl')
                self.assertEqual(adapted, original.replace(NODE_EXTENSION_GUARD.encode(), b'', 1))

    def test_inputs_cli_recovers_each_reason_variant_and_captures_same_draw_reason(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-snell-pack-') as folder:
            for mode in ('old','stable'):
                reason = Path(folder)/(mode+'-reason.zip')
                inputs = Path(folder)/(mode+'-inputs.zip')
                self.assertEqual(self.build(reason,mode).returncode,0)
                result = subprocess.run([
                    sys.executable,'-B',str(ROOT/'tools/water_snell_main_pack.py'),
                    str(inputs),'--mode',mode,'--observe','inputs',
                ],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                from water_snell_main_pack import recover_inputs, INPUT_STORE, STORE
                with ZipFile(reason) as parent, ZipFile(inputs) as built:
                    helper = built.read('shaders/lib/water_residual_sun.glsl')
                    self.assertEqual(recover_inputs(helper),parent.read('shaders/lib/water_residual_sun.glsl'))
                    water = built.read('shaders/gbuffers_water.fsh')
                    self.assertEqual(water.replace(INPUT_STORE.encode(),STORE.encode()),
                                     parent.read('shaders/gbuffers_water.fsh'))
                    self.assertIn(b'float(r*12+j+1)+64.0*WNS_reasons.x',helper)
                    self.assertEqual(built.read('shaders/final.fsh'),parent.read('shaders/final.fsh'))

    def test_stable_pack_preserves_whole_rejection_and_external_negative_policies(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-snell-pack-') as folder:
            destination = Path(folder)/'stable.zip'
            self.assertEqual(self.build(destination,'stable').returncode,0)
            with ZipFile(destination) as built:
                helper = built.read('shaders/lib/water_residual_sun.glsl').decode()
                self.assertIn('nodeValid=snell.status==1;',helper)
                self.assertEqual(helper.count('if (!nodeValid) { valid=false; WNS_status.w+=1.0; continue; }'),5)
                for policy in (
                    'bool valid=fullApplied && baseApplied && WNS_finite(full) && WNS_finite(base);',
                    'vec3 reflected=reflect(-viewToEye,facet);',
                    'vec3 reconstruction=abs(transmitted-k*target);',
                    'max(max(reconstruction.x,reconstruction.y),reconstruction.z)<=inverseBound',
                    'dot(transmitted,transmitted)>=1e-6 && transmitted.y>0.0 && reflected.y<0.0;',
                    'nodeValid=kind!=1 && reflection.a<=0.0 && WNS_finite(skyWeight);',
                    'WNS_status.w=max(WNS_status.w,1.0);\n        return full;',
                ):
                    self.assertIn(policy,helper)

    def test_public_cli_never_overwrites_existing_destination(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-snell-pack-') as folder:
            destination = Path(folder)/'existing.zip'
            destination.write_bytes(b'preserve-me')
            self.assertNotEqual(self.build(destination,'old').returncode,0)
            self.assertEqual(destination.read_bytes(),b'preserve-me')


if __name__ == '__main__':
    unittest.main()
