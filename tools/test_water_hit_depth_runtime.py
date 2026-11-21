import os
from pathlib import Path
import tempfile
import unittest

from water_hit_depth_runtime import lab_java_processes, references_game


class OwnedLabJavaTest(unittest.TestCase):
    def test_unrelated_java_does_not_own_lab(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);game=root/'Lab';game.mkdir()
            for pid,comm,cwd in [('11','java',game),('12','java',root/'Android'),('13','bash',game)]:
                process=root/pid;process.mkdir()
                (process/'comm').write_text(comm+'\n')
                (process/'cmdline').write_bytes(b'/usr/bin/java\x00example')
                (process/'fd').mkdir()
                os.symlink(cwd,process/'cwd')
            self.assertEqual(lab_java_processes(game,root),[11])

    def test_long_classpath_preserves_alias_ownership(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);game=root/'Lab';game.mkdir()
            alias=root/'Mapped';alias.symlink_to(game)
            other=os.pathsep.join(str(root/f'library{i}.jar') for i in range(300))
            self.assertGreater(len(other),4096)
            self.assertFalse(references_game(other,game))
            self.assertTrue(references_game(other+os.pathsep+str(alias/'file.jar'),game))

    def test_two_owned_processes_are_not_hidden(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);game=root/'Lab';game.mkdir()
            for pid in ('21','22'):
                process=root/pid;process.mkdir()
                (process/'comm').write_text('java\n');os.symlink(game,process/'cwd')
                (process/'cmdline').write_bytes(b'java\x00example');(process/'fd').mkdir()
            self.assertEqual(lab_java_processes(game,root),[21,22])

    def test_alias_command_and_open_file_are_all_owned(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);game=root/'Lab';game.mkdir();other=root/'Other';other.mkdir()
            alias=root/'Alias';os.symlink(game,alias)
            for pid,cwd,command,fd in [('31',alias,b'java',None),
                    ('32',other,('java\x00'+str(game)).encode(),None),('33',other,b'java',game/'level.dat')]:
                process=root/pid;process.mkdir();(process/'comm').write_text('java\n')
                os.symlink(cwd,process/'cwd');(process/'cmdline').write_bytes(command);(process/'fd').mkdir()
                if fd is not None:os.symlink(fd,process/'fd/7')
            self.assertEqual(lab_java_processes(game,root),[31,32,33])


if __name__=='__main__':
    unittest.main()
