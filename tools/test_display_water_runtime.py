import json
import ast
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import display_water_runtime as runtime


class RuntimeSafetyTests(unittest.TestCase):
    def test_restore_before_selection_without_enabled_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory) / 'game'
            backup = Path(directory) / 'backup'
            output = Path(directory) / 'evidence'
            for folder in (game / 'mods', game / 'config', backup, output):
                folder.mkdir(parents=True)
            (game / 'mods/test.jar').write_bytes(b'test')
            (backup / 'aqualumen-physics-0.2.0.jar').write_bytes(b'normal')
            (backup / 'config').mkdir()
            (backup / 'config/options.txt').write_bytes(b'original')
            (game.parent / 'instance.cfg').write_bytes(b'instance')
            data = dict(backup=str(backup), ordinarySave={},
                        config={'config/options.txt': runtime.sha(backup / 'config/options.txt')},
                        mods={'aqualumen-physics-0.2.0.jar': runtime.sha(backup / 'aqualumen-physics-0.2.0.jar')},
                        instanceConfigSHA256=runtime.sha(game.parent / 'instance.cfg'))
            with patch.object(runtime, 'GAME', game), patch.object(runtime, 'OUT', output), \
                 patch.object(runtime, 'MODS', {'test.jar': runtime.sha(game / 'mods/test.jar')}), \
                 patch.object(runtime, 'NAMES', ['config/options.txt']), \
                 patch.object(runtime, 'baseline', return_value=data), \
                 patch.object(runtime, 'ordinary_tree', return_value={}), \
                 patch.object(runtime, 'stopped'):
                runtime.restore()
            self.assertTrue(json.loads((output / 'runtime-restored.json').read_text())['normalModsExact'])

    def test_jfr_zero_exit_without_start_confirmation_is_rejected(self):
        for response, accepted in (('Could not start recording, not able to write to file', False),
                                   ('Started recording 1.', True)):
            with self.subTest(accepted=accepted), tempfile.TemporaryDirectory() as directory:
                game=Path(directory)/'game'; output=Path(directory)/'evidence'
                (game/'aqualumen-benchmark').mkdir(parents=True); output.mkdir()
                (output/'candidate-launcher-start.json').write_text(json.dumps(dict(
                    world_id=runtime.WORLD_ID,pack=runtime.PACKS['candidate'])))
                (game/'aqualumen-benchmark/status.json').write_text(json.dumps(dict(
                    run_id='display-water-candidate-'+runtime.RUN_SUFFIX,state='sampling')))
                result=runtime.subprocess.CompletedProcess([],0,stdout=response,stderr='')
                with patch.object(runtime,'GAME',game), patch.object(runtime,'OUT',output), \
                     patch.object(runtime.os,'readlink',return_value=str(game)), \
                     patch.object(runtime.subprocess,'check_output',return_value='123\n'), \
                     patch.object(runtime.subprocess,'run',return_value=result):
                    if accepted:
                        runtime.profile_start('candidate')
                        receipt=json.loads((output/'candidate-profile-start.json').read_text())
                        self.assertTrue(receipt['recording_start_confirmed'])
                        self.assertFalse(receipt['recording_finalized'])
                    else:
                        with self.assertRaisesRegex(RuntimeError,'did not confirm'):
                            runtime.profile_start('candidate')
                        self.assertFalse((output/'candidate-profile-start.json').exists())

    def test_natural_review_packet_routing_does_not_reuse_region_baseline(self):
        for packet, suffix, artifact, scene_count in (
                ('receiver-plant-owner-halo-v100','20261011-v100','plant-owner-halo-probe-v110.jar',2),
                ('receiver-plant-fluid-publication-v99','20261011-v99','plant-fluid-probe-v106.jar',2),
                ('receiver-plant-tiled-v98','20261011-v98','plant-tiled-probe-v104.jar',2),
                ('receiver-plant-window-v97','20261011-v97','plant-receiver-window-v102.jar',2),
                ('receiver-plant-owner-bounds-v96','20261011-v96','plant-owner-probe-v100.jar',2),
                ('underwater-raw-unknown-v95','20261011-v95','raw-unknown-tags-v97.jar',2),
                ('underwater-raw-rejection-v94','20261011-v94','material-region-gpu-v96.jar',2),
                ('underwater-raw-receiver-v93','20261011-v93','material-region-gpu-v96.jar',2),
                ('underwater-coupled-beauty-v92','20261011-v92','material-region-gpu-v96.jar',2),
                ('underwater-coupled-normal-v91','20261011-v91','material-region-gpu-v96.jar',2),
                ('underwater-raw-exit-v90','20261011-v90','material-region-gpu-v96.jar',2),
                ('underwater-raw-exit-v89','20261011-v89','material-region-gpu-v96.jar',2),
                ('underwater-exit-direction-v88','20261011-v88','material-region-gpu-v96.jar',2),
                ('underwater-interface-v87','20261011-v87','material-region-gpu-v96.jar',2),
                ('receiver-plant-material-v86','20261011-v86','material-region-gpu-v96.jar',2),
                ('receiver-plant-material-v85','20261011-v85','plant-material-gpu-v90.jar',2),
                ('receiver-pack-predicate-v84','20261011-v84','pack-predicate-v86.jar',2),
                ('receiver-classification-v83','20261011-v83','classification-switch-v85.jar',2),
                ('receiver-owner-profile-v82','20261011-v82','allocation-free-owner-v83.jar',2),
                ('receiver-owner-profile-v81','20261011-v81','allocation-free-owner-v83.jar',2),
                ('underwater-normal-comparison-v80','20261011-v80','plant-draw-state-guard-v82.jar',2),
                ('receiver-natural-sun-v77','20261011-v77','plant-draw-state-guard-v82.jar',4),
                ('receiver-natural-review-v76','20261011-v76','plant-draw-state-guard-v82.jar',4),
                ('receiver-plant-region-v69','20261011-v69','plant-region-runtime-v76.jar',2)):
            tree=ast.parse(Path(runtime.__file__).read_text())
            entry=tree.body[-1]
            self.assertIsInstance(entry,ast.If)
            self.assertIsInstance(entry.body[-1],ast.If)
            entry.body.pop()
            namespace=dict(__name__='__main__',__file__=runtime.__file__)
            with patch.object(sys,'argv',['display_water_runtime.py','setup','--packet',packet]), patch.object(Path,'mkdir'):
                exec(compile(tree,runtime.__file__,'exec'),namespace)
            self.assertEqual(namespace['OUT'].name,packet)
            self.assertEqual(namespace['RUN_SUFFIX'],suffix)
            self.assertTrue(namespace['PHYS_PATH'].name.endswith(artifact))
            self.assertEqual(len(namespace['SCENES']),scene_count)
            self.assertEqual(namespace['REFLECTION_NORMAL_COMPARISON'],
                             packet == 'underwater-normal-comparison-v80')
            self.assertEqual(namespace['INTERFACE_NORMAL_COMPARISON'],
                             packet == 'underwater-coupled-beauty-v92')
            if packet=='receiver-natural-sun-v77':
                namespace['require_scene_capability']()
            elif packet=='receiver-natural-review-v76':
                with self.assertRaisesRegex(RuntimeError,'qualified Sun-view'):
                    namespace['require_scene_capability']()

    def test_current_pipeline_rejects_previous_log_and_append(self):
        old = b'Preparing start region for dimension minecraft:overworld\nCreating pipeline for dimension minecraft:overworld\n'
        previous = dict(bytes=len(old), sha256=runtime.hashlib.sha256(old).hexdigest())
        for log in (old, old+b'late previous-client flush\n'):
            with self.assertRaisesRegex(RuntimeError, 'previous client'):
                runtime.require_current_pipeline(log, previous)
        for log in (b'new launch\n', b'new launch\nCreating pipeline for dimension minecraft:overworld\n'):
            with self.assertRaisesRegex(RuntimeError, 'not loaded'):
                runtime.require_current_pipeline(log, previous)
        runtime.require_current_pipeline(b'new launch\n'+old, previous)

    def test_crash_log_is_not_a_clean_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory)
            (game / 'logs').mkdir()
            (game / 'logs/latest.log').write_text('Stopping worker threads\n')
            with patch.object(runtime, 'GAME', game), patch.object(runtime, 'stopped'), patch.object(runtime, 'RECOVER_STOPPED_PACKET', None):
                with self.assertRaisesRegex(RuntimeError, 'explicit owned recovery'):
                    runtime.verify_previous_exit()

    def test_clean_exit_still_requires_no_live_java(self):
        with patch.object(runtime, 'stopped', side_effect=RuntimeError('live')):
            with self.assertRaisesRegex(RuntimeError, 'live'):
                runtime.verify_previous_exit()

    def test_live_java_blocks_file_changes(self):
        with patch.object(runtime.subprocess, 'run') as command:
            command.return_value.returncode = 0
            with self.assertRaisesRegex(RuntimeError, 'live'):
                runtime.stopped()

    def test_failed_process_inventory_is_not_stopped(self):
        with patch.object(runtime.subprocess, 'run') as command:
            command.return_value.returncode = 2
            with self.assertRaises(RuntimeError):
                runtime.stopped()

    def test_ordinary_save_is_hashed_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory)
            save = game / 'saves/新規ワールド'
            save.mkdir(parents=True)
            (save / 'level.dat').write_bytes(b'original')
            with patch.object(runtime, 'GAME', game):
                self.assertEqual(runtime.ordinary_tree(), {'level.dat': runtime.sha(save / 'level.dat')})
            self.assertEqual((save / 'level.dat').read_bytes(), b'original')

    def test_symlinked_save_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory)
            save = game / 'saves/新規ワールド'
            save.mkdir(parents=True)
            (game / 'outside').write_bytes(b'private')
            (save / 'level.dat').symlink_to(game / 'outside')
            with patch.object(runtime, 'GAME', game):
                with self.assertRaisesRegex(RuntimeError, 'symlinks'):
                    runtime.ordinary_tree()

    def test_fallback_run_is_not_archived(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory)
            run = game / 'aqualumen-benchmark/runs/display-water-control-20261011-v1'
            run.mkdir(parents=True)
            (run / 'run.json').write_text(json.dumps(dict(world_id=runtime.WORLD_ID,
                pack_name=runtime.PACKS['control'], shader_active=True, shader_fallback=True)))
            with patch.object(runtime, 'GAME', game), patch.object(runtime, 'OUT', game / 'evidence'):
                with self.assertRaisesRegex(RuntimeError, 'activation'):
                    runtime.collect('control')
            self.assertFalse((game / 'evidence').exists())

    def test_receiver_receipt_excludes_other_log_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory)
            run = game / 'aqualumen-benchmark/runs' / ('display-water-candidate-'+runtime.RUN_SUFFIX)
            run.mkdir(parents=True)
            pack = game / 'shaderpacks' / runtime.PACKS['candidate']
            pack.parent.mkdir()
            pack.write_bytes(b'fixture-pack')
            (run / 'run.json').write_text(json.dumps(dict(world_id=runtime.WORLD_ID,
                pack_name=runtime.PACKS['candidate'], shader_active=True, shader_fallback=False,
                gl_renderer='NVIDIA fixture', pack_sha256=runtime.sha(pack))))
            for scene in runtime.SCENES:
                (run / (scene+'.json')).write_text(json.dumps(dict(scenario=scene, frames=1,
                    shader_active=True, shader_fallback=False)))
                (run / (scene+'.png')).write_bytes(b'fixture')
                (run / (scene+'.csv')).write_text('fixture')
            (game / 'logs').mkdir()
            receipt = '[Render thread/INFO]: [STDOUT]: [Aqualumen Receiver] ready=2'
            (game / 'logs/latest.log').write_text('private unrelated line\n'+receipt+'\n')
            output = game / 'evidence'
            with patch.object(runtime, 'GAME', game), patch.object(runtime, 'OUT', output):
                runtime.collect('candidate')
            self.assertEqual((output / 'candidate-receiver-runtime.log').read_text(), receipt+'\n')

    def test_failed_run_is_preserved_without_success_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory)
            run_id = 'display-water-candidate-'+runtime.RUN_SUFFIX
            run = game / 'aqualumen-benchmark/runs' / run_id
            run.mkdir(parents=True)
            pack = game / 'shaderpacks' / runtime.PACKS['candidate']
            pack.parent.mkdir()
            pack.write_bytes(b'failed-fixture-pack')
            (run / 'run.json').write_text(json.dumps(dict(world_id=runtime.WORLD_ID,
                pack_name=runtime.PACKS['candidate'], shader_active=True, shader_fallback=False,
                gl_renderer='NVIDIA fixture', pack_sha256=runtime.sha(pack))))
            failure = dict(run_id=run_id, status='aborted', fixture_cleanup_complete=False)
            (run / 'aborted.json').write_text(json.dumps(failure))
            (game / 'logs').mkdir()
            (game / 'logs/latest.log').write_text('private unrelated line\n')
            output = game / 'evidence'
            with patch.object(runtime, 'GAME', game), patch.object(runtime, 'OUT', output), patch.object(runtime, 'stopped'):
                with self.assertRaisesRegex(RuntimeError, 'unclean'):
                    runtime.collect_failed('candidate')
                failure['fixture_cleanup_complete'] = True
                (run / 'aborted.json').write_text(json.dumps(failure))
                runtime.collect_failed('candidate')
            self.assertTrue((output / 'candidate-aborted-runtime/aborted.json').is_file())
            self.assertFalse((output / 'candidate-runtime').exists())
            self.assertFalse((output / 'candidate-receiver-runtime.log').exists())


if __name__ == '__main__':
    unittest.main()
