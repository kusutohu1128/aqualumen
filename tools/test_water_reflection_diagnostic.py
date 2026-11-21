import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from build_water_reflection_diagnostic import ROOT, SEAM, build


class DiagnosticTest(unittest.TestCase):
    def test_only_output_and_display_change(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'diagnostic.zip'
            build(target)
            with ZipFile(target) as archive:
                modified = archive.read('shaders/gbuffers_water.fsh').decode()
                original = (ROOT / 'shaders/gbuffers_water.fsh').read_text()
                self.assertEqual(modified.split('    vec3 diagnostic=color;')[0], original.split(SEAM)[0])
                for name in archive.namelist():
                    if name not in {'shaders/gbuffers_water.fsh', 'shaders/final.fsh'}:
                        self.assertEqual(archive.read(name), (ROOT / name).read_bytes())
                self.assertNotIn('shaders/composite1.fsh', archive.namelist())
            with self.assertRaises(FileExistsError):
                build(target)


if __name__ == '__main__':
    unittest.main()
