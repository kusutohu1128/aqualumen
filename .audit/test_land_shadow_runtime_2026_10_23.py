import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
import zlib

PATH = Path(__file__).with_name('land_shadow_runtime_2026_10_23.py')
SPEC = importlib.util.spec_from_file_location('land_shadow_runtime', PATH)
runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode())


def write_json(path, value):
    write(path, json.dumps(value))


def png(width=1600, height=900):
    def chunk(kind, value):
        return struct.pack('>I', len(value)) + kind + value + struct.pack('>I', zlib.crc32(kind + value))
    header = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(b'\0' * (height * (width * 3 + 1)))) + chunk(b'IEND', b'')


class RuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='land-runtime-cpu-')
        self.root = Path(self.temporary.name)
        self.game = self.root / 'instances/Aqualumen Lab/minecraft'
        for name in ('mods', 'shaderpacks', 'config', 'saves/' + runtime.WORLD, 'aqualumen-benchmark', 'logs'):
            (self.game / name).mkdir(parents=True)
        self.report = self.root / runtime.REPORT
        self.report.mkdir(parents=True)
        self.cache = self.root / 'private-cache'
        self.cache.mkdir()
        self.out = self.report / 'runtime-cpu-test'
        self.subject = runtime.LandShadowRuntime(self.out, self.game, self.root, self.cache)
        write(self.game / 'options.txt', '\n'.join(key + ':old' for key in runtime.OPTIONS) + '\nfov:70.0\n')
        write(self.game / 'config/iris.properties', '# Original date\nshaderPack=' + runtime.ORDINARY + '\nenableShaders=true\nallowUnknownShaders=false\n')
        write(self.game / 'config/aqualumen-benchmark.properties', 'schema=2\nworld=' + runtime.WORLD + '\nworld_id=' + runtime.WORLD_ID + '\nwidth=2560\nheight=1440\n')
        write(self.game / 'config/sodium-options.json', '{"unchanged":true}\n')
        write(self.game.parent / 'instance.cfg', '[General]\nname=Aqualumen Lab\nlastLaunchTime=123\nlastTimePlayed=10\ntotalTimePlayed=42\nOverrideMemory=true\n')
        write(self.game / 'saves/新規ワールド/level.dat', b'ordinary user data')
        marker = dict(schema='2', world_id=runtime.WORLD_ID, seed='308060', generator='minecraft:noise/overworld', minecraft='1.21.1')
        write(self.game / 'saves' / runtime.WORLD / 'aqualumen-world.properties', runtime.properties(marker))
        write(self.game / 'logs/latest.log', 'Prior normal launch\nStopping!\n')
        for name in runtime.NORMAL_MODS:
            write(self.game / 'mods' / name, ('normal jar ' + name).encode())
        ordinary = b'pinned ordinary CPU fixture'
        write(self.game / 'shaderpacks' / runtime.ORDINARY, ordinary)
        write(self.report / 'ordinary-0.6.zip', ordinary)
        benchmark = b'pinned benchmark CPU fixture'
        write(self.root / 'build' / runtime.BENCH, benchmark)
        self.pack = self.report / 'Aqualumen-Land-CPU.zip'
        with ZipFile(self.pack, 'w') as archive:
            archive.writestr('shaders/lib/land_shadows.glsl', 'float cpuFixture() { return 1.; }\n')
            archive.writestr('LICENSE', 'CPU fixture only\n')
        self.pack_hash = runtime.sha(self.pack)
        self.qualification = self.report / 'qualification.json'
        native = dict(schema='aqualumen-land-shadow-native-v1', algorithm='land', candidateQualified=True,
                      observedExit=0, positiveControlsPassed=True, renderer='NVIDIA GeForce RTX 3080 Ti/CPU fixture',
                      sourcePins={'shaders/lib/land_shadows.glsl': runtime.digest(b'float cpuFixture() { return 1.; }\n')})
        self.native = self.report / 'native.json'
        write_json(self.native, native)
        compile_stdout = self.report / 'compile.stdout'
        write(compile_stdout, 'NVIDIA CPU fixture, not a GPU observation\n')
        compiled = self.report / 'compile.json'
        write_json(compiled, dict(packSHA256=self.pack_hash, exitCode=0, renderer=native['renderer'], stdout=self.ref(compile_stdout)))
        motion = self.report / 'motion.json'
        write_json(motion, dict(packSHA256=self.pack_hash, exitCode=0, renderer=native['renderer'], passed=True))
        write_json(self.qualification, dict(schema='land-shadow-qualification-v1', packSHA256=self.pack_hash,
                   evidence=dict(native=self.ref(self.native), compile=self.ref(compiled), motion=self.ref(motion))))
        self.patches = [patch.object(runtime.shared, 'GAME', self.game), patch.object(runtime.shared.prior, 'GAME', self.game),
                        patch.object(runtime, 'lab_java_processes', return_value=[]),
                        patch.object(runtime, 'ORDINARY_SHA', runtime.digest(ordinary)),
                        patch.object(runtime, 'BENCH_SHA', runtime.digest(benchmark))]
        for item in self.patches:
            item.start()
        self.original = {name: (self.game / name).read_bytes() for name in runtime.CONFIGS}
        self.original_instance = (self.game.parent / 'instance.cfg').read_bytes()
        self.original_mods = runtime.tree(self.game / 'mods')

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temporary.cleanup()

    def ref(self, path):
        return dict(path=path.relative_to(self.root).as_posix(), sha256=runtime.sha(path))

    def setup_runtime(self):
        self.subject.setup(self.pack, self.qualification)

    def assert_normal(self):
        self.assertEqual({name: (self.game / name).read_bytes() for name in runtime.CONFIGS}, self.original)
        self.assertEqual((self.game.parent / 'instance.cfg').read_bytes(), self.original_instance)
        self.assertEqual(runtime.tree(self.game / 'mods'), self.original_mods)
        self.assertFalse((self.game / runtime.SENTINEL).exists())
        self.assertEqual((self.game / 'saves/新規ワールド/level.dat').read_bytes(), b'ordinary user data')

    def test_setup_and_restore_keep_physics_and_normal_bytes(self):
        self.setup_runtime()
        self.assertEqual((self.game / 'mods/aqualumen-physics-0.2.0.jar').read_bytes(), b'normal jar aqualumen-physics-0.2.0.jar')
        self.assertEqual({name: (self.game / name).read_bytes() for name in runtime.CONFIGS}, self.original)
        self.subject.select('ordinary')
        self.assertEqual(runtime.pairs((self.game / 'options.txt').read_bytes(), ':')['overrideWidth'], '1600')
        self.subject.restore()
        self.assert_normal()
        self.assertTrue((self.game / 'shaderpacks' / self.pack.name).exists())

    def test_live_lab_rejects_setup_before_any_write(self):
        with patch.object(runtime, 'lab_java_processes', return_value=[321]):
            with self.assertRaisesRegex(RuntimeError, 'live'):
                self.setup_runtime()
        self.assertFalse(self.out.exists())
        self.assert_normal()

    def test_wrong_world_rejects_setup_before_any_write(self):
        marker = self.game / 'saves' / runtime.WORLD / 'aqualumen-world.properties'
        marker.write_text(marker.read_text().replace(runtime.WORLD_ID, '00000000-0000-0000-0000-000000000000'))
        with self.assertRaisesRegex(RuntimeError, 'marker'):
            self.setup_runtime()
        self.assertFalse(self.out.exists())
        self.assert_normal()

    def test_identity_native_is_not_candidate_qualification(self):
        value = json.loads(self.native.read_text())
        value['candidateQualified'] = False
        write_json(self.native, value)
        proof = json.loads(self.qualification.read_text())
        proof['evidence']['native'] = self.ref(self.native)
        write_json(self.qualification, proof)
        with self.assertRaisesRegex(RuntimeError, 'native qualification'):
            self.setup_runtime()
        self.assertFalse(self.out.exists())
        self.assert_normal()

    def test_changed_evidence_rejects_setup(self):
        write(self.native, '{}')
        with self.assertRaisesRegex(RuntimeError, 'Evidence changed'):
            self.setup_runtime()
        self.assertFalse(self.out.exists())

    def test_native_shader_payload_must_match_pack(self):
        with ZipFile(self.pack, 'w') as archive:
            archive.writestr('shaders/lib/land_shadows.glsl', 'changed shader')
        proof = json.loads(self.qualification.read_text())
        proof['packSHA256'] = runtime.sha(self.pack)
        write_json(self.qualification, proof)
        with self.assertRaisesRegex(RuntimeError, 'Native shader inputs'):
            self.setup_runtime()
        self.assertFalse(self.out.exists())

    def test_partial_setup_restores_without_prepared_receipt(self):
        original_install = runtime.shared.install_new
        calls = []
        def interrupted_install(source, target, value):
            calls.append(target)
            if len(calls) == 2:
                raise RuntimeError('CPU simulated interruption')
            original_install(source, target, value)
        with patch.object(runtime.shared, 'install_new', side_effect=interrupted_install):
            with self.assertRaisesRegex(RuntimeError, 'simulated interruption'):
                self.setup_runtime()
        self.assertTrue((self.out / 'baseline.json').exists())
        self.assertFalse((self.out / 'prepared.json').exists())
        self.subject.restore()
        self.assert_normal()

    def test_partial_select_restores_individual_config_variants(self):
        self.setup_runtime()
        original_replace = self.subject.replace
        calls = []
        def interrupted_replace(path, value):
            calls.append(path)
            if len(calls) == 2:
                raise RuntimeError('CPU simulated interruption')
            original_replace(path, value)
        with patch.object(runtime.LandShadowRuntime, 'replace', side_effect=interrupted_replace):
            with self.assertRaisesRegex(RuntimeError, 'simulated interruption'):
                self.subject.select('ordinary')
        self.subject.restore()
        self.assert_normal()

    def test_staged_iris_after_fsync_is_recovered_without_broad_ignore(self):
        self.setup_runtime()
        replace = runtime.os.replace
        def interrupted_replace(source, target):
            if target == self.game / 'config/iris.properties':
                raise RuntimeError('CPU interruption after staged iris fsync')
            replace(source, target)
        with patch.object(runtime.os, 'replace', side_effect=interrupted_replace):
            with self.assertRaisesRegex(RuntimeError, 'after staged iris fsync'):
                self.subject.select('ordinary')
        staged = self.game / 'config/.iris.properties.land-20261023.pending'
        self.assertTrue(staged.is_file())
        self.subject.restore()
        self.assertFalse(staged.exists())
        self.assert_normal()

    def test_unowned_pending_config_is_not_ignored(self):
        self.setup_runtime()
        write(self.game / 'config/.unowned.land-20261023.pending', 'new user data')
        with self.assertRaisesRegex(RuntimeError, 'Unmanaged config changed'):
            self.subject.restore()
        self.assertEqual((self.game / 'config/.unowned.land-20261023.pending').read_bytes(), b'new user data')

    def test_restore_rejects_new_user_option_without_overwrite(self):
        self.setup_runtime()
        self.subject.select('ordinary')
        options = self.game / 'options.txt'
        options.write_text(options.read_text().replace('fov:70.0', 'fov:90.0'))
        before = options.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'Unmanaged setting'):
            self.subject.restore()
        self.assertEqual(options.read_bytes(), before)
        self.assertTrue((self.game / runtime.SENTINEL).exists())

    def test_restore_allows_only_known_launcher_telemetry(self):
        self.setup_runtime()
        self.subject.select('ordinary')
        instance = self.game.parent / 'instance.cfg'
        instance.write_text(instance.read_text().replace('lastTimePlayed=10', 'lastTimePlayed=65'))
        self.subject.restore()
        self.assert_normal()

    def test_restore_rejects_changed_instance_settings(self):
        self.setup_runtime()
        instance = self.game.parent / 'instance.cfg'
        instance.write_text(instance.read_text().replace('OverrideMemory=true', 'OverrideMemory=false'))
        with self.assertRaisesRegex(RuntimeError, 'instance settings'):
            self.subject.restore()
        self.assertIn('OverrideMemory=false', instance.read_text())

    def test_restore_rejects_save_drift_and_never_rolls_it_back(self):
        self.setup_runtime()
        save = self.game / 'saves/新規ワールド/level.dat'
        write(save, 'new user data')
        with self.assertRaisesRegex(RuntimeError, 'Ordinary save changed'):
            self.subject.restore()
        self.assertEqual(save.read_bytes(), b'new user data')

    def test_restore_rejects_live_owned_launcher_without_exit_receipt(self):
        self.setup_runtime()
        self.subject.save('ordinary-launcher-start.json', {'role': 'ordinary'})
        with self.assertRaisesRegex(RuntimeError, 'Missing or redirected file'):
            self.subject.restore()
        self.assertTrue((self.game / 'mods' / runtime.BENCH).exists())

    def test_candidate_selection_needs_completed_ordinary_capture(self):
        self.setup_runtime()
        with self.assertRaises(RuntimeError):
            self.subject.select('candidate')
        self.assertFalse((self.out / 'candidate-selected.json').exists())

    def test_symlinked_config_rejected_before_setup(self):
        iris = self.game / 'config/iris.properties'
        target = self.root / 'external-iris'
        iris.rename(target)
        iris.symlink_to(target)
        with self.assertRaisesRegex(RuntimeError, 'redirected'):
            self.setup_runtime()
        self.assertFalse(self.out.exists())

    def make_run(self):
        source = self.root / 'run-fixture'
        source.mkdir()
        identity = dict(world_id=runtime.WORLD_ID, pack_name=self.pack.name, pack_sha256=self.pack_hash,
                        shader_active=True, shader_fallback=False, resolution=[1600, 900], framebuffer_resolution=[1600, 900])
        write_json(source / 'run.json', identity | dict(run_id='cpu-run', scenarios=runtime.SCENES,
                   gl_renderer='NVIDIA GeForce RTX 3080 Ti/CPU fixture', warmup_seconds=5, sample_seconds=5,
                   native_motion_capture_active=False))
        write_json(source / 'complete.json', dict(run_id='cpu-run', status='complete', scenarios=runtime.SCENES, fixture_cleanup_complete=True))
        for scene in runtime.SCENES:
            write_json(source / (scene + '.json'), identity | dict(scenario=scene, run_id='cpu-run', frames=10,
                       camera_first_person=True, camera_eye_match=True, opaque_fixture=dict(camera_eye_match=True)))
            write(source / (scene + '.csv'), 'frame,ns,ms\n' + ''.join(str(frame) + ',10000000,10.0\n' for frame in range(10)))
            write(source / (scene + '.png'), png())
        return source

    def validate(self, source):
        return runtime.validate_run(source, dict(pack=self.pack.name, sha256=self.pack_hash), 'cpu-run')

    def test_complete_air_run_has_actual_game_flag_not_visual_or_perf_acceptance(self):
        observation = self.validate(self.make_run())
        self.assertTrue(observation['actualMinecraft'])
        self.assertFalse(observation['visualAccepted'])
        self.assertFalse(observation['performanceAcceptance'])
        self.assertEqual(observation['sceneFrameCounts'], {scene: 10 for scene in runtime.SCENES})

    def test_fallback_run_rejected(self):
        source = self.make_run()
        path = source / 'run.json'
        value = json.loads(path.read_text())
        value['shader_fallback'] = True
        write_json(path, value)
        with self.assertRaisesRegex(RuntimeError, 'shader/world identity'):
            self.validate(source)

    def test_pinned_039_static_capture_protocol_is_accepted(self):
        source = self.make_run()
        path = source / 'run.json'
        value = json.loads(path.read_text())
        del value['native_motion_capture_active']
        value['mods'] = {'aqualumen_benchmark': '0.3.9'}
        value['frame_method'] = 'System.nanoTime render-tail intervals; one start boundary discarded; setup/screenshots outside sample'
        write_json(path, value)
        self.assertTrue(self.validate(source)['actualMinecraft'])

    def test_missing_motion_witness_rejects_unknown_capture_protocol(self):
        source = self.make_run()
        path = source / 'run.json'
        value = json.loads(path.read_text())
        del value['native_motion_capture_active']
        write_json(path, value)
        with self.assertRaisesRegex(RuntimeError, 'Unknown capture protocol'):
            self.validate(source)

    def test_active_motion_capture_is_rejected(self):
        source = self.make_run()
        path = source / 'run.json'
        value = json.loads(path.read_text())
        value['native_motion_capture_active'] = True
        write_json(path, value)
        with self.assertRaisesRegex(RuntimeError, 'Motion capture'):
            self.validate(source)

    def test_incomplete_fixture_cleanup_rejected(self):
        source = self.make_run()
        path = source / 'complete.json'
        value = json.loads(path.read_text())
        value['fixture_cleanup_complete'] = False
        write_json(path, value)
        with self.assertRaisesRegex(RuntimeError, 'fixture cleanup'):
            self.validate(source)

    def test_missing_frame_rows_rejected(self):
        source = self.make_run()
        write(source / (runtime.SCENES[0] + '.csv'), 'frame,ns,ms\n0,10000000,10.0\n')
        with self.assertRaisesRegex(RuntimeError, 'frame count'):
            self.validate(source)

    def test_corrupt_screenshot_rejected(self):
        source = self.make_run()
        write(source / (runtime.SCENES[0] + '.png'), png()[:-10])
        with self.assertRaisesRegex(RuntimeError, 'Truncated PNG'):
            self.validate(source)

    def test_wrong_extent_rejected(self):
        source = self.make_run()
        write(source / (runtime.SCENES[0] + '.png'), png(800, 450))
        with self.assertRaisesRegex(RuntimeError, 'extent'):
            self.validate(source)

    def test_outside_evidence_path_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'escapes repository'):
            runtime.evidence_ref(self.root, dict(path='../outside', sha256='0' * 64))

    def test_owned_absolute_evidence_reference_is_accepted(self):
        path = self.native
        self.assertEqual(runtime.evidence_ref(self.root, dict(path=str(path), sha256=runtime.sha(path))), path)

    def test_outside_absolute_evidence_reference_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'escapes repository'):
            runtime.evidence_ref(self.root, dict(path=str(self.root.parent / 'outside'), sha256='0' * 64))

    def test_symlinked_absolute_evidence_reference_is_rejected(self):
        link = self.report / 'redirected-evidence.json'
        link.symlink_to(self.native)
        with self.assertRaisesRegex(RuntimeError, 'escapes repository'):
            runtime.evidence_ref(self.root, dict(path=str(link), sha256=runtime.sha(self.native)))


if __name__ == '__main__':
    unittest.main()
