"""TEST ZIP public packaging contracts; no shader behavioral/GPU proof."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile


PARENT_SHA = "3a83e837628f4b0b21617d1468baa3d2e6fd659b5a758800cfa301d75646ab26"
INCLUDE = ('// AQUALUMEN_RESIDUAL_INCLUDE_BEGIN\n'
           '#include "/lib/wave_residual.glsl"\n'
           '#include "/lib/water_residual.glsl"\n'
           '// AQUALUMEN_RESIDUAL_INCLUDE_END\n')
HOOK = ('// AQUALUMEN_RESIDUAL_HOOK_BEGIN\n'
        '    vec3 residualRipple=rippleState(absolutePosition.xz);\n'
        '    vec3 residualMean=normalize(vec3(-wave.y,1.0,-wave.z));\n'
        '    if (dot(residualMean,geometricNormal)<0.0) residualMean=-residualMean;\n'
        '    bool residualEligible=underwater && upperSurface && localColumnKnown && localColumn.x>=0.8\n'
        '        && dot(residualRipple.yz,residualRipple.yz)<1e-12 && length(n-residualMean)<1e-5\n'
        '        && receiverKind!=1 && reflectedHit.a<0.0 && abs(n.y)>0.5;\n'
        '    color=waterResidualInterface(color,n,v,worldPosition,viewPos,max(footprint*1.25,0.035),\n'
        '        localColumnKnown?localColumn.x:0.0,skyAccess,caveAmbient,scatter,residualEligible);\n'
        '// AQUALUMEN_RESIDUAL_HOOK_END\n')


class ResidualPackTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]
    parent_relative = Path('reports/2026-10-03-underwater-resolved-normal/Aqualumen-ShoreProbe-world-underwater-resolved-normal-086-phase120-v1.zip')

    def test_public_cli_creates_pinned_test_pack_preserving_parent_except_tagged_fs_hook(self):
        parent = self.root / self.parent_relative
        self.assertEqual(hashlib.sha256(parent.read_bytes()).hexdigest(), PARENT_SHA)
        sources = {p: p.read_bytes() for p in (self.root / 'shaders').rglob('*') if p.is_file()}
        with tempfile.TemporaryDirectory(prefix='aqualumen-residual-cpu-test-') as temporary:
            target = Path(temporary) / 'residual.zip'
            result = subprocess.run([sys.executable, '-B', str(self.root/'tools/water_residual_pack.py'), str(target)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            repeated = Path(temporary) / 'residual-repeat.zip'
            repeat = subprocess.run([sys.executable, '-B', str(self.root/'tools/water_residual_pack.py'), str(repeated)],
                                    capture_output=True, text=True)
            self.assertEqual(repeat.returncode, 0, repeat.stderr)
            self.assertEqual(target.read_bytes(), repeated.read_bytes())
            with ZipFile(parent) as old, ZipFile(target) as new:
                water = new.read('shaders/gbuffers_water.fsh').decode()
                self.assertEqual(water.count(INCLUDE), 1)
                self.assertEqual(water.count(HOOK), 1)
                self.assertEqual(water.replace(INCLUDE, '').replace(HOOK, ''), old.read('shaders/gbuffers_water.fsh').decode())
                for name in old.namelist():
                    if name in ('UNDERWATER-PROBE.txt', 'WATER-TESSELLATION-PROBE.txt', 'UNDERWATER-RESOLVED-PROBE.txt'):
                        self.assertEqual(new.read('PARENT-RESIDUAL-' + name), old.read(name), name)
                        self.assertIn(b'WATER-RESIDUAL-PROBE.json', new.read(name))
                    elif name != 'shaders/gbuffers_water.fsh':
                        self.assertEqual(new.read(name), old.read(name), name)
                for name in ('shaders/lib/wave_residual.glsl', 'shaders/lib/water_residual.glsl'):
                    self.assertEqual(new.read(name), sources[self.root/name])
                metadata = json.loads(new.read('WATER-RESIDUAL-PROBE.json'))
                self.assertEqual(metadata['schema'], 'aqualumen-water-residual-probe-v1')
                self.assertEqual(metadata['mode'], 'residual-interface-atlas')
                self.assertEqual(metadata['parent_pack_sha256'], PARENT_SHA)
                self.assertEqual(metadata['geometry_factor'], 4)
                self.assertEqual(metadata['fixed_phase_seconds'], 120.0)
                self.assertEqual(metadata['quadrature_order'], 3)
                self.assertEqual(metadata['quadrature_nodes'], 9)
                self.assertEqual(metadata['model'], 'independent-missing-power-gaussian-discrete-quadrature-approximation')
                self.assertIs(metadata['test_only'], True)
                for key in ('shipping_fix', 'energy_accepted', 'reciprocity_accepted', 'runtime_accepted',
                            'visual_accepted', 'performance_accepted', 'pack_enforces_world_guard'):
                    self.assertIs(metadata[key], False, key)
            self.assertEqual(sources, {p:p.read_bytes() for p in sources})
            self.assertEqual(hashlib.sha256(parent.read_bytes()).hexdigest(), PARENT_SHA)

    def test_public_api_rejects_wrong_default_order_without_creating_output(self):
        from water_residual_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-residual-order-cpu-') as temporary:
            folder = Path(temporary)
            source = folder/'source'
            parent = source/self.parent_relative
            parent.parent.mkdir(parents=True)
            shutil.copyfile(self.root/self.parent_relative, parent)
            (source/'shaders/lib').mkdir(parents=True)
            for name in ('wave_residual.glsl', 'water_residual.glsl'):
                shutil.copyfile(self.root/'shaders/lib'/name, source/'shaders/lib'/name)
            helper = source/'shaders/lib/water_residual.glsl'
            helper.write_text(helper.read_text().replace('#define WATER_RESIDUAL_ORDER 3', '#define WATER_RESIDUAL_ORDER 4'))
            target = folder/'output-not-created'/'residual.zip'
            with self.assertRaises(ValueError):
                build_pack(source, target)
            self.assertFalse(target.parent.exists())

    def test_public_api_never_overwrites_or_writes_shipping_trees_even_through_alias(self):
        from water_residual_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-residual-guards-cpu-') as temporary:
            folder = Path(temporary)
            source = folder/'source'
            source.mkdir()
            existing = folder/'existing.zip'
            existing.write_bytes(b'keep existing archive')
            with self.assertRaises(FileExistsError):
                build_pack(source, existing)
            self.assertEqual(existing.read_bytes(), b'keep existing archive')
            dangling = folder/'dangling.zip'
            dangling.symlink_to(folder/'absent.zip')
            with self.assertRaises(FileExistsError):
                build_pack(source, dangling)
            self.assertTrue(dangling.is_symlink())
            for shipping_tree in ('shaders', 'dist'):
                (source/shipping_tree).mkdir()
                alias = folder/('alias-' + shipping_tree)
                alias.symlink_to(source/shipping_tree, target_is_directory=True)
                for target in (source/shipping_tree/'probe.zip', alias/'probe.zip'):
                    with self.assertRaises(ValueError):
                        build_pack(source, target)
                    self.assertFalse(target.exists())

    def test_public_api_rejects_unpinned_parent_before_output_creation(self):
        from water_residual_pack import build_pack
        with tempfile.TemporaryDirectory(prefix='aqualumen-residual-pin-cpu-') as temporary:
            folder = Path(temporary)
            source = folder/'source'
            parent = source/self.parent_relative
            parent.parent.mkdir(parents=True)
            parent.write_bytes(b'not the approved parent archive')
            target = folder/'output-not-created'/'residual.zip'
            with self.assertRaises(ValueError):
                build_pack(source, target)
            self.assertFalse(target.parent.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
