"""Public CPU GH-pack contracts; no GPU/Iris/runtime acceptance."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools/water_gh_phase_pack.py'
PARENT = ROOT / 'reports/2026-10-03-water-prepared-iris/cpu-pack/Aqualumen-ShoreProbe-world-sun-prepared-physical-v1.zip'
RESIDUAL = 'shaders/lib/water_residual.glsl'
MANIFEST = 'WATER-GH-PHASE.json'
OLD_NODE = b'        vec2 perturbation=vec2(rootX*nodes[x],crossTerm*nodes[x]+rootZ*nodes[z]);\n'


def cli(*args):
    return subprocess.run([sys.executable, '-B', str(SCRIPT), *map(str, args)],
                          text=True, capture_output=True)


def strip_tags(source, family):
    prefix = b'// AQUALUMEN_' + family.encode() + b'_BEGIN:'
    while prefix in source:
        a = source.index(prefix)
        name_end = source.index(b'\n', a)
        tag = source[a + len(prefix):name_end]
        end = b'// AQUALUMEN_' + family.encode() + b'_END:' + tag + b'\n'
        b = source.index(end, name_end) + len(end)
        source = source[:a] + source[b:]
    return source


class GHPhasePackTests(unittest.TestCase):
    def test_public_zero_physical_pack_preserves_original_expression_and_recovers_exact_parent(self):
        with tempfile.TemporaryDirectory(prefix='gh-phase-cpu-') as temporary:
            first = Path(temporary) / 'Aqualumen-ShoreProbe-world-gh-phase-0-physical-v1.zip'
            second = Path(temporary) / 'again/Aqualumen-ShoreProbe-world-gh-phase-0-physical-v1.zip'
            for output in (first, second):
                result = cli('build', '--parent', PARENT, '--phase', '0', '--role', 'physical', '--output', output)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with ZipFile(PARENT) as parent, ZipFile(first) as candidate:
                for name in parent.namelist():
                    if name != RESIDUAL:
                        self.assertEqual(candidate.read(name), parent.read(name), name)
                helper = candidate.read(RESIDUAL)
                self.assertEqual(helper.count(OLD_NODE), 1)
                self.assertEqual(strip_tags(helper, 'GH_PHASE'), parent.read(RESIDUAL))
                metadata = json.loads(candidate.read(MANIFEST))
                self.assertEqual(metadata['schema'], 'aqualumen-water-gh-phase-v1')
                self.assertEqual(metadata['phase_degrees'], 0)
                self.assertEqual(metadata['role'], 'physical')
                self.assertEqual(metadata['changed_existing_members'], [RESIDUAL])
                self.assertIs(metadata['FINAL_physical_byte_exact'], True)
                self.assertIs(metadata['runtime_accepted'], False)
                self.assertEqual(candidate.read(metadata['parent_archive_member']), PARENT.read_bytes())
            recovered = Path(temporary) / 'parent.zip'
            result = cli('recover', '--candidate', first, '--output', recovered)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(recovered.read_bytes(), PARENT.read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)
