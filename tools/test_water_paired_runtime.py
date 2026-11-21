"""Recovery fault points use disposable files, never the installed Lab."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import water_paired_runtime as runtime


class RecoveryTests(unittest.TestCase):
    def fixture(self, base, stage):
        game = base / 'Aqualumen Lab/minecraft'
        out, backup = base / 'evidence', base / 'backup'
        out.mkdir()
        backup.mkdir()
        for folder in ('mods', 'config', 'shaderpacks', 'saves/AqualumenNaturalV2', 'saves/新規ワールド', 'aqualumen-benchmark'):
            (game / folder).mkdir(parents=True, exist_ok=True)
        (game / 'saves/新規ワールド/original').write_bytes(b'ordinary save never changes')
        (game / 'saves/AqualumenNaturalV2/aqualumen-world.properties').write_text('test')
        for name in runtime.CONFIG:
            (backup / name).parent.mkdir(exist_ok=True, parents=True)
            (backup / name).write_text('normal ' + name)
            (game / name).write_text('test ' + name)
        (backup / 'instance.cfg').write_bytes(b'normal instance')
        (game.parent / 'instance.cfg').write_bytes(b'test instance')
        normal = 'aqualumen-physics-0.2.0.jar'
        (game / 'mods/iris.jar').write_bytes(b'iris')
        (game / 'mods' / normal).write_bytes(b'normal physics')
        mods = {p.name: runtime.sha(p) for p in (game / 'mods').glob('*.jar')}
        if stage >= 1:
            (game / 'mods' / normal).rename(backup / normal)
        tests = {f'test-{i}.jar': runtime.hashlib.sha256(f'test {i}'.encode()).hexdigest() for i in range(3)}
        for i, name in enumerate(tests):
            if stage >= 2 and (stage != 2 or i == 0):
                (game / 'mods' / name).write_bytes(f'test {i}'.encode())
        if stage == 4:
            (game / 'mods/test-0.jar').rename(backup / 'test-0.jar')
        pack_hash = runtime.hashlib.sha256(b'pack').hexdigest()
        if stage >= 3:
            (game / 'shaderpacks' / runtime.PACK).write_bytes(b'pack')
        data = dict(backup=str(backup), config={n: runtime.sha(backup / n) for n in runtime.CONFIG}, mods=mods,
                    ordinarySave={'original': runtime.sha(game / 'saves/新規ワールド/original')},
                    instanceSHA256=runtime.sha(backup / 'instance.cfg'), testMods=tests, packSHA256=pack_hash)
        (out / 'baseline.json').write_text(json.dumps(data))
        return game, out, backup

    def test_restore_converges_from_interrupted_setup_or_restore(self):
        for stage in range(5):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                game, out, backup = self.fixture(Path(directory), stage)
                with patch.object(runtime, 'GAME', game), patch.object(runtime, 'OUT', out), \
                        patch.object(runtime.prior, 'GAME', game), patch.object(runtime.prior, 'stopped'), \
                        contextlib.redirect_stdout(io.StringIO()):
                    runtime.restore()
                    runtime.restore()
                result = json.loads((out / 'restored.json').read_text())
                self.assertTrue(result['normalConfigExact'] and result['normalModsExact'] and result['ordinarySaveExact'])
                self.assertEqual((game / 'mods/aqualumen-physics-0.2.0.jar').read_bytes(), b'normal physics')

    def test_changed_backup_rejected_before_any_restore_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            game, out, backup = self.fixture(Path(directory), 3)
            (backup / 'config/iris.properties').write_bytes(b'corrupt')
            before = {str(p.relative_to(game)): p.read_bytes() for p in game.rglob('*') if p.is_file()}
            with patch.object(runtime, 'GAME', game), patch.object(runtime, 'OUT', out), \
                    patch.object(runtime.prior, 'GAME', game), patch.object(runtime.prior, 'stopped'):
                with self.assertRaisesRegex(RuntimeError, 'Backup config changed'):
                    runtime.restore()
            self.assertEqual(before, {str(p.relative_to(game)): p.read_bytes() for p in game.rglob('*') if p.is_file()})

    def test_symlinked_config_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            game, out, backup = self.fixture(Path(directory), 3)
            path = game / 'config/iris.properties'
            path.rename(game / 'config/iris.saved')
            path.symlink_to(backup / 'config/iris.properties')
            with patch.object(runtime, 'GAME', game):
                with self.assertRaisesRegex(RuntimeError, 'redirected'):
                    runtime.owned_paths()

    def test_partial_staging_is_preserved_and_normal_runtime_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            game, out, backup = self.fixture(Path(directory), 1)
            partial = runtime.staging_path(game / 'mods/test-0.jar')
            partial.write_bytes(b'incomplete owned staged file')
            pack = runtime.staging_path(game / 'shaderpacks' / runtime.PACK)
            pack.write_bytes(b'incomplete pack')
            with patch.object(runtime, 'GAME', game), patch.object(runtime, 'OUT', out), \
                    patch.object(runtime.prior, 'GAME', game), patch.object(runtime.prior, 'stopped'), \
                    contextlib.redirect_stdout(io.StringIO()):
                runtime.restore()
            self.assertEqual((backup / partial.name).read_bytes(), b'incomplete owned staged file')
            self.assertEqual((backup / pack.name).read_bytes(), b'incomplete pack')
            self.assertTrue((game / 'mods/aqualumen-physics-0.2.0.jar').is_file())

    def test_install_hash_mismatch_never_publishes_active_jar(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / 'source', Path(directory) / 'active.jar'
            source.write_bytes(b'incomplete source')
            with self.assertRaisesRegex(RuntimeError, 'Incomplete staged install'):
                runtime.install_new(source, target, '0' * 64)
            self.assertFalse(target.exists())
            self.assertEqual(runtime.staging_path(target).read_bytes(), b'incomplete source')


if __name__ == '__main__':
    unittest.main()
