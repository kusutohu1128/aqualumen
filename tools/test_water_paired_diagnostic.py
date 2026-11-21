"""CPU-only tests for the paired water TEST pack generator; not GPU or Iris tests."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import water_paired_diagnostic as wpd  # noqa: E402

ASSIGNMENT = re.compile(r'([A-Za-z_]\w*(?:\[\d+\])?)\s*=(?!=)')


def read_tree(root):
    root = Path(root)
    paths = [path for path in (root / 'shaders').rglob('*') if path.is_file()] + [root / 'LICENSE']
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in paths}


def pins(root):
    return {name: hashlib.sha256(data).hexdigest() for name, data in read_tree(root).items()}


def snapshot(directory):
    root = Path(directory) / 'src'
    shutil.copytree(ROOT / 'shaders', root / 'shaders', symlinks=True)
    shutil.copyfile(ROOT / 'LICENSE', root / 'LICENSE')
    return root


def mutate(root, name, old, new):
    path = root / name
    data = path.read_bytes()
    if old not in data:
        raise AssertionError(f'Mutation anchor absent in {name}')
    path.write_bytes(data.replace(old, new, 1))


def added_lines(original, transformed):
    """Lines of transformed that are not the in-order original subsequence."""
    old, added, index = original.decode().splitlines(), [], 0
    for line in transformed.decode().splitlines():
        if index < len(old) and line == old[index]:
            index += 1
        else:
            added.append(line)
    return added if index == len(old) else None


class PairedWaterDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = read_tree(ROOT)
        cls.control = wpd.variant_files(ROOT, 'control')
        cls.paired = wpd.variant_files(ROOT, 'paired')

    def changed(self, files):
        return {name for name in self.original if files[name] != self.original[name]}

    def test_member_sets_and_changed_files(self):
        for files in (self.control, self.paired):
            self.assertEqual(set(files), set(self.original))
            self.assertIn('LICENSE', files)
            self.assertTrue(all(name == 'LICENSE' or name.startswith('shaders/') for name in files))
        self.assertEqual(self.changed(self.control), {wpd.WAVES, wpd.RIPPLES})
        self.assertEqual(self.changed(self.paired), {wpd.WAVES, wpd.RIPPLES, wpd.WATER, wpd.FINAL,
                                                     wpd.PREPARE, wpd.PROPERTIES})

    def test_wave_override_both_variants(self):
        for files in (self.control, self.paired):
            waves = files[wpd.WAVES]
            self.assertEqual(waves.count(b'time=17.0;'), 1)
            self.assertEqual(waves.count(wpd.WAVE_ENTRY + wpd.WAVE_FREEZE), 1)
            self.assertEqual(waves.replace(wpd.WAVE_FREEZE, b''), self.original[wpd.WAVES])
        self.assertEqual(self.control[wpd.WAVES], self.paired[wpd.WAVES])

    def test_ripple_disabled_both_variants(self):
        for files in (self.control, self.paired):
            ripples = files[wpd.RIPPLES]
            self.assertIn(b'vec3 rippleState(vec2 worldXZ) {\n    return vec3(0.0);', ripples)
            self.assertEqual(ripples.replace(wpd.RIPPLE_OFF, b''), self.original[wpd.RIPPLES])
        self.assertEqual(self.control[wpd.RIPPLES], self.paired[wpd.RIPPLES])

    def test_time_uniform_preserved(self):
        for files in (self.control, self.paired):
            self.assertEqual(files[wpd.UNIFORMS], self.original[wpd.UNIFORMS])
            self.assertIn(b'uniform float frameTimeCounter;\n', files[wpd.UNIFORMS])
            self.assertEqual(files[wpd.CLOUDS], self.original[wpd.CLOUDS])
            self.assertIn(b'frameTimeCounter', files[wpd.CLOUDS])
            self.assertIn(b'localWaveState(absolutePosition.xz,frameTimeCounter,', files[wpd.WATER])
            for data in files.values():
                self.assertIsNone(wpd.TIME_OVERRIDE.search(data))

    def test_no_plant_defines(self):
        for files in (self.control, self.paired):
            for name, data in files.items():
                self.assertIsNone(wpd.PLANT_DEFINE.search(data), name)
        with tempfile.TemporaryDirectory() as directory:
            root = snapshot(directory)
            mutate(root, 'shaders/lib/settings.glsl', b'#define AQUALUMEN_SETTINGS\n',
                   b'#define AQUALUMEN_SETTINGS\n#define AQUALUMEN_PLANT_RECEIVER\n')
            for variant in wpd.VARIANTS:
                with self.assertRaises(wpd.SourceShapeError):
                    wpd.variant_files(root, variant)

    def test_control_has_no_observer_stores(self):
        for data in self.control.values():
            for token in (b'colortex12', b'aqualumenPairedView', b'RENDERTARGETS: 0,12'):
                self.assertNotIn(token, data)
        self.assertNotIn(b'gl_FragData[1]', self.control[wpd.WATER])
        self.assertEqual(self.control[wpd.WATER], self.original[wpd.WATER])

    def test_paired_c12_producer_shape(self):
        water = self.paired[wpd.WATER]
        self.assertIn(b'/* RENDERTARGETS: 0,12 */\n', water)
        self.assertNotIn(b'DRAWBUFFERS', water)
        self.assertIn(b'void main() {\n    gl_FragData[1]=vec4(0.0);', water)
        self.assertEqual(water.count(b'gl_FragData[1]'), 2)
        self.assertLess(water.index(b'gl_FragData[1]=vec4(0.0);'), water.index(b'discard;'))
        self.assertEqual(water.count(b'reflectionTrace(viewPos'), 1)
        self.assertLess(water.index(wpd.WATER_SSR), water.index(b'pairedRoute=5.0'))
        self.assertLess(water.index(b'pairedRoute=reflectedReceiver.sourceReady'),
                        water.index(b'if (reflectedReceiver.sourceReady)'))
        self.assertIn(b'gl_FragData[1]=underwater?vec4(pairedRoute,fresnel,pairedTravel,1.0):vec4(0.0);', water)
        prepare = self.paired[wpd.PREPARE]
        self.assertIn(b'const int colortex12Format = RGBA32F;', prepare)
        self.assertIn(b'const bool colortex12Clear = true;', prepare)
        clear = re.search(rb'const vec4 colortex12ClearColor = vec4\(([^)]*)\);', prepare)
        self.assertEqual([float(part) for part in clear.group(1).split(b',')], [0.0] * 4)
        self.assertLess(prepare.index(b'colortex12Format'), prepare.index(b'*/'))

    def test_beauty_c0_untouched(self):
        original = self.original[wpd.WATER].replace(wpd.WATER_DRAWBUFFERS, wpd.WATER_RENDERTARGETS)
        added = added_lines(original, self.paired[wpd.WATER])
        self.assertIsNotNone(added, 'original water source is not an in-order subsequence')
        self.assertTrue(added)
        for line in added:
            code = line.split('//')[0]
            self.assertNotIn('gl_FragData[0]', code)
            self.assertNotIn('return', code)
            self.assertNotIn('discard', code)
            for target in ASSIGNMENT.findall(code):
                self.assertIn(target, {'pairedRoute', 'pairedTravel', 'gl_FragData[1]'}, line)
        self.assertEqual(self.paired[wpd.WATER].count(b'gl_FragData[0]'), 2)

    def test_final_preview_selector_and_properties(self):
        final = self.paired[wpd.FINAL]
        added = added_lines(self.original[wpd.FINAL], final)
        self.assertIsNotNone(added)
        self.assertIn('uniform sampler2D colortex12;', added)
        self.assertIn('uniform int aqualumenPairedView;', added)
        lines = final.decode().splitlines()
        assignments = [index for index, line in enumerate(lines) if 'gl_FragColor=' in line]
        self.assertEqual(len(assignments), 2)
        self.assertEqual(lines[assignments[1] - 1].strip(), 'if (aqualumenPairedView!=0)')
        self.assertIn('texelFetch(colortex12', lines[assignments[1]])
        properties = self.paired[wpd.PROPERTIES]
        self.assertIn(b'\nblend.gbuffers_water.colortex12=off\n', properties)
        self.assertIn(b'\nuniform.int.aqualumenPairedView=0\n', properties)
        self.assertIn(wpd.WATER_BLEND, properties)

    def test_unknown_variant(self):
        for variant in ('', 'Paired', 'production', None):
            with self.assertRaises(ValueError):
                wpd.variant_files(ROOT, variant)

    def test_unknown_root_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'LICENSE').write_bytes(b'x')
            with self.assertRaises(wpd.SourceShapeError):
                wpd.variant_files(root, 'control')
        with tempfile.TemporaryDirectory() as directory:
            root = snapshot(directory)
            (root / 'LICENSE').unlink()
            with self.assertRaises(wpd.SourceShapeError):
                wpd.variant_files(root, 'control')
        with tempfile.TemporaryDirectory() as directory:
            root = snapshot(directory)
            os.symlink(root / 'shaders/lib/waves.glsl', root / 'shaders/lib/alias.glsl')
            with self.assertRaises(wpd.SourceShapeError):
                wpd.variant_files(root, 'control')

    def test_missing_and_duplicate_anchors(self):
        cases = [
            ('wave entry shape', wpd.WAVES, b'vec3 waveSurfaceLocal(vec2 x, float time,',
             b'vec3 waveSurfaceLocal(vec2 x,float time,', ('control', 'paired')),
            ('wave definition duplicate', 'shaders/lib/wave_residual.glsl', b'#endif\n',
             b'vec3 waveSurfaceLocal(vec2 x);\n#endif\n', ('control', 'paired')),
            ('ripple guard', wpd.RIPPLES, b'if(aqualumenActive==0)', b'if(aqualumenActive<1)', ('control', 'paired')),
            ('receiver anchor', wpd.WATER, wpd.RECEIVER_ASSIGN,
             b'            : waterReceiverFirst(worldPosition+n*0.06,reflected);\n', ('paired',)),
            ('final duplicate', wpd.FINAL, wpd.FINAL_SAMPLER, wpd.FINAL_SAMPLER * 2, ('paired',)),
            ('blend missing', wpd.PROPERTIES, wpd.WATER_BLEND, b'', ('paired',)),
        ]
        for label, name, old, new, failing in cases:
            with self.subTest(label), tempfile.TemporaryDirectory() as directory:
                root = snapshot(directory)
                mutate(root, name, old, new)
                for variant in wpd.VARIANTS:
                    if variant in failing:
                        with self.assertRaises(wpd.SourceShapeError):
                            wpd.variant_files(root, variant)
                    else:
                        wpd.variant_files(root, variant)

    def test_active_c12_collisions(self):
        cases = [
            ('C12 sampler', 'shaders/composite.fsh', b'/* DRAWBUFFERS:0 */\n',
             b'/* DRAWBUFFERS:0 */\nuniform sampler2D colortex12;\n'),
            ('C12 target', 'shaders/composite.fsh', b'/* DRAWBUFFERS:0 */', b'/* RENDERTARGETS:0,12 */'),
            ('unknown directive', 'shaders/composite.fsh', b'/* DRAWBUFFERS:0 */', b'/* DRAWBUFFERS:0C */'),
            ('C12 property', wpd.PROPERTIES, wpd.WATER_BLEND, wpd.WATER_BLEND + b'size.buffer.colortex12=1 1\n'),
            ('time constant', wpd.UNIFORMS, b'uniform float frameTimeCounter;',
             b'uniform float frameTimeCounter;\nconst float frameTimeCounter=17.0;'),
        ]
        for label, name, old, new in cases:
            with self.subTest(label), tempfile.TemporaryDirectory() as directory:
                root = snapshot(directory)
                mutate(root, name, old, new)
                for variant in wpd.VARIANTS:
                    with self.assertRaises(wpd.SourceShapeError):
                        wpd.variant_files(root, variant)

    def test_hash_mismatch_and_key_set(self):
        with tempfile.TemporaryDirectory() as directory:
            root = snapshot(directory)
            good = pins(root)
            altered = dict(good, **{wpd.WATER: '0' * 64})
            missing = {name: value for name, value in good.items() if name != 'LICENSE'}
            extra = dict(good, **{'shaders/extra.glsl': '0' * 64})
            for label, expected in (('value', altered), ('missing', missing), ('extra', extra)):
                with self.subTest(label):
                    out = Path(directory) / f'out-{label}'
                    with self.assertRaises(wpd.SourceShapeError):
                        wpd.generate(root, out, expected)
                    self.assertFalse(out.exists())
            mutate(root, 'shaders/composite.fsh', b'/* DRAWBUFFERS:0 */', b'/* DRAWBUFFERS:0 */ ')
            with self.assertRaises(wpd.SourceShapeError):
                wpd.generate(root, Path(directory) / 'out-drift', good)
            with self.assertRaises(ValueError):
                wpd.generate(root, Path(directory) / 'out-bad', {wpd.WATER: 'not-a-hash'})

    def test_deterministic_archives_across_tempdirs(self):
        before = pins(ROOT)
        outputs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as directory:
                out = Path(directory) / 'paired-water'
                manifest = wpd.generate(ROOT, out, before)
                self.assertEqual(sorted(path.name for path in out.iterdir()),
                                 ['control.zip', 'manifest.json', 'paired.zip'])
                outputs.append({path.name: path.read_bytes() for path in out.iterdir()})
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(pins(ROOT), before)
        for variant, expected in (('control', self.control), ('paired', self.paired)):
            raw = outputs[0][f'{variant}.zip']
            self.assertEqual(manifest['variants'][variant]['sha256'], hashlib.sha256(raw).hexdigest())
            with ZipFile(io.BytesIO(raw)) as archive:
                infos = archive.infolist()
                self.assertEqual([info.filename for info in infos], sorted(expected))
                self.assertTrue(all(info.date_time == wpd.ZIP_TIME for info in infos))
                self.assertEqual({info.filename: archive.read(info) for info in infos}, expected)
        recorded = json.loads(outputs[0]['manifest.json'])
        self.assertEqual(recorded, manifest)
        self.assertEqual(recorded['inputs']['sha256'], before)
        verification = recorded['verification']
        for claim in ('glsl_compiled', 'native_c0_invariance_tested', 'iris_loaded', 'minecraft_capture',
                      'observer_present', 'physical_acceptance', 'shader_fix_claim', 'performance_claim'):
            self.assertIs(verification[claim], False)
        self.assertEqual(recorded['c12_record']['routes']['5'], 'PRODUCER_UNAVAILABLE')

    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = snapshot(directory)
            out = Path(directory) / 'out'
            out.mkdir()
            (out / 'evidence').write_bytes(b'keep')
            with self.assertRaises(FileExistsError):
                wpd.generate(root, out, pins(root))
            self.assertEqual([path.name for path in out.iterdir()], ['evidence'])
            self.assertEqual((out / 'evidence').read_bytes(), b'keep')

    def test_protected_output_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = snapshot(directory)
            (root / 'dist').mkdir()
            alias = Path(directory) / 'alias'
            os.symlink(root / 'dist', alias)
            expected = pins(root)
            for out in (root / 'dist' / 'pack', root / 'shaders' / 'diag', root / 'dist', alias / 'pack'):
                with self.subTest(str(out)):
                    with self.assertRaises((ValueError, FileExistsError)):
                        wpd.generate(root, out, expected)
            self.assertEqual(list((root / 'dist').iterdir()), [])
            self.assertEqual(pins(root), expected)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = snapshot(directory)
            good = Path(directory) / 'pins.json'
            good.write_text(json.dumps(pins(root)))
            out = Path(directory) / 'out'
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                wpd.main(['--root', str(root), '--out', str(out), '--expected-hashes', str(good)])
            self.assertEqual(set(json.loads(stdout.getvalue())), {'out', 'control.zip', 'paired.zip'})
            bad = Path(directory) / 'bad.json'
            bad.write_text(json.dumps(dict(pins(root), LICENSE='0' * 64)))
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit_:
                wpd.main(['--root', str(root), '--out', str(Path(directory) / 'out2'),
                          '--expected-hashes', str(bad)])
            self.assertEqual(exit_.exception.code, 1)
            self.assertFalse((Path(directory) / 'out2').exists())


if __name__ == '__main__':
    unittest.main()
