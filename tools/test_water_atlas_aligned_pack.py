"""CPU-only address and reversible TEST archive qualification; not GPU tests."""
from fractions import Fraction
from io import BytesIO
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools/water_atlas_aligned_pack.py'
PARENTS = ROOT / 'reports/2026-10-03-water-gh-phase/cpu-pack'


def files(raw):
    with ZipFile(BytesIO(raw)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


class AtlasAlignedTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True)

    def build(self, directory, phase=0):
        parent = PARENTS / f'Aqualumen-ShoreProbe-world-gh-phase-{phase}-diagnostic-v1.zip'
        output = Path(directory) / f'Aqualumen-ShoreProbe-world-gh-phase-{phase}-diagnostic-aligned-v2.zip'
        result = self.run_cli('build', '--parent', parent, '--output', output)
        self.assertEqual(result.returncode, 0, result.stderr)
        return parent, output

    def test_old_binary32_expression_has_crosspanel_counterexample(self):
        # A source-arithmetic counterexample, NOT reproduced GPU interpolation.
        def f32(value):
            return struct.unpack('f', struct.pack('f', value))[0]
        observed = []
        for column in range(4):
            uv = f32((column * 400 + 3 + .5) / 1600)
            local = f32(f32(uv * 4) - column)
            observed.append(int(f32(local * 1600)))
        self.assertEqual(observed, [14, 13, 13, 13])

    def test_address_reference_all_pixels_eight_tiles_two_extents(self):
        from water_atlas_aligned_pack import source_pixel
        for width, height in ((1600, 900), (2560, 1440)):
            tw, th = width // 4, height // 2
            # Exhaustive separable axes cover every local pixel in every tile.
            for x in range(tw):
                expected = int(Fraction(2*x+1, 2*tw) * width)
                for column in range(4):
                    self.assertEqual(source_pixel(column*tw+x, 0, width, height)[0], expected)
            for y in range(th):
                expected = int(Fraction(2*y+1, 2*th) * height)
                for row in range(2):
                    self.assertEqual(source_pixel(0, row*th+y, width, height)[1], expected)
        for args in ((0, 0, 1601, 900), (0, 0, 1600, 901),
                     (-1, 0, 1600, 900), (1600, 0, 1600, 900), (0, 0, 0, 0)):
            with self.assertRaises(ValueError):
                source_pixel(*args)

    def test_both_archives_change_final_only_and_recover_exact_parent(self):
        from water_atlas_aligned_pack import ALIGNED_COORDINATES, ORIGINAL_COORDINATES
        with tempfile.TemporaryDirectory() as directory:
            for phase in (0, 45):
                parent, output = self.build(directory, phase)
                old, new = files(parent.read_bytes()), files(output.read_bytes())
                changed = [name for name in old if new[name] != old[name]]
                self.assertEqual(changed, ['shaders/final.fsh'])
                self.assertEqual(old['shaders/final.fsh'].count(ORIGINAL_COORDINATES), 1)
                self.assertEqual(new['shaders/final.fsh'].count(ALIGNED_COORDINATES), 1)
                self.assertEqual(new['shaders/final.fsh'].replace(ALIGNED_COORDINATES, ORIGINAL_COORDINATES),
                                 old['shaders/final.fsh'])
                self.assertEqual(new['ATLAS-ALIGNED-original/parent.zip'], parent.read_bytes())
                manifest = json.loads(new['WATER-ATLAS-ALIGNED.json'])
                self.assertFalse(manifest['Iris_accepted'])
                self.assertFalse(manifest['physical_band_fix_claim'])
                recovered = Path(directory) / f'recovered-{phase}.zip'
                result = self.run_cli('recover', '--candidate', output, '--output', recovered)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(recovered.read_bytes(), parent.read_bytes())
                repeat = self.run_cli('build', '--parent', parent, '--output', output)
                self.assertNotEqual(repeat.returncode, 0)
                self.assertEqual(files(output.read_bytes()), new)

    def test_reject_parent_tamper_symlink_wrong_name_and_protected_output(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            parent = PARENTS / 'Aqualumen-ShoreProbe-world-gh-phase-0-diagnostic-v1.zip'
            bad = directory / 'bad.zip'
            bad.write_bytes(parent.read_bytes() + b'tamper')
            linked = directory / 'link.zip'
            linked.symlink_to(parent)
            for supplied, output in (
                (bad, directory / 'Aqualumen-ShoreProbe-world-gh-phase-0-diagnostic-aligned-v2.zip'),
                (linked, directory / 'Aqualumen-ShoreProbe-world-gh-phase-0-diagnostic-aligned-v2.zip'),
                (parent, directory / 'Aqualumen-ShoreProbe-world-gh-phase-0-diagnostic-v1.zip'),
                (parent, ROOT / 'dist/atlas-aligned-forbidden.zip')):
                result = self.run_cli('build', '--parent', supplied, '--output', output)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Rejected aligned atlas TEST pack:', result.stderr)
                self.assertFalse(output.exists())

    def test_reject_candidate_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            _, output = self.build(directory)
            members = files(output.read_bytes())
            members['shaders/gbuffers_water.fsh'] += b'\n// tamper\n'
            tampered = Path(directory) / 'tampered.zip'
            with ZipFile(tampered, 'w') as archive:
                for name, content in members.items():
                    archive.writestr(name, content)
            recovered = Path(directory) / 'not-recovered.zip'
            result = self.run_cli('recover', '--candidate', tampered, '--output', recovered)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Rejected aligned atlas TEST pack:', result.stderr)
            self.assertFalse(recovered.exists())

    def test_deterministic_rebuild(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            _, a = self.build(first)
            _, b = self.build(second)
            self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_frozen_runtime_does_not_silently_accept_new_pack_or_old_alias(self):
        from water_gh_phase_runtime import _source_policy
        with tempfile.TemporaryDirectory() as directory:
            _, output = self.build(directory)
            for name in (output.name, 'Aqualumen-ShoreProbe-world-gh-phase-0-diagnostic-v1.zip'):
                with self.assertRaises((ValueError, AssertionError)):
                    _source_policy(output.read_bytes(), name)


if __name__ == '__main__':
    unittest.main()
