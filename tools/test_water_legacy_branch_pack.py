"""New passive ledger archive contracts; CPU only, not rendering acceptance."""
from pathlib import Path
import tempfile
import unittest
import water_legacy_branch_pack as b
import water_gh_phase_pack as gh

PARENTS = gh.ROOT / 'reports/2026-10-06-water-band-atlas/cpu-pack'


class BranchPackTests(unittest.TestCase):
    def parent(self, phase):
        return PARENTS / f'Aqualumen-ShoreProbe-world-gh-phase-{phase}-diagnostic-aligned-v2.zip'

    def test_actual_helper_records_every_failure_and_both_calls_without_changing_parent(self):
        for phase in (0, 45):
            for call in ('full', 'base'):
                raw = self.parent(phase).read_bytes()
                files, meta = b.files(raw, call)
                parent = gh._archive(raw)
                changed = [n for n in parent if files[n] != parent[n]]
                self.assertEqual(set(changed), {gh.RESIDUAL, gh.SUN, gh.WATER})
                for n in changed:
                    self.assertEqual(gh._erase_tags(files[n], 'WLB'), parent[n], n)
                helper = files[gh.RESIDUAL]
                for bit in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024):
                    self.assertIn(f'WLB_mask|={bit};'.encode(), helper)
                self.assertIn(b'WLB_note(WLB_mask,3*x+z,transmittedRay,reflectedRay,facing,tir);', helper)
                self.assertIn(f'    WGP_{call}WR=WGP_readLegacyStatus();\n// AQUALUMEN_WLB_BEGIN:SAVE\n    WLB_save();'.encode(), files[gh.SUN])
                other = 'base' if call == 'full' else 'full'
                self.assertNotIn(f'    WGP_{other}WR=WGP_readLegacyStatus();\n// AQUALUMEN_WLB_BEGIN:SAVE'.encode(), files[gh.SUN])
                self.assertIn(b'gl_FragData[4]=WLB_saved[3];', files[gh.WATER])
                self.assertFalse(meta['physicalAccepted'])
                self.assertEqual(meta['selectedCall'], call)

    def test_public_build_is_deterministic_recovers_parent_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as c:
            name = f'Aqualumen-ShoreProbe-world-legacy-branch-45-full-v{b.VERSION}.zip'
            p, q = Path(a) / name, Path(c) / name
            for out in (p, q):
                b.build(self.parent(45), 'full', out)
            self.assertEqual(p.read_bytes(), q.read_bytes())
            self.assertEqual(b.recover(p), self.parent(45).read_bytes())
            with self.assertRaises(FileExistsError):
                b.build(self.parent(45), 'full', p)

    def test_reject_wrong_call_parent_name_and_protected_path(self):
        raw = self.parent(0).read_bytes()
        for blob, call in ((raw + b'tamper', 'full'), (raw, 'FULL'), (raw, 0)):
            with self.assertRaises(ValueError):
                b.files(blob, call)
        with tempfile.TemporaryDirectory() as tmp:
            for out in (Path(tmp) / 'wrong.zip', gh.ROOT / 'dist/legacy-branch-forbidden.zip'):
                with self.assertRaises(ValueError):
                    b.build(self.parent(0), 'full', out)
                self.assertFalse(out.exists())

    def test_reject_recovered_candidate_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / f'Aqualumen-ShoreProbe-world-legacy-branch-0-base-v{b.VERSION}.zip'
            b.build(self.parent(0), 'base', out)
            files = gh._archive(out.read_bytes())
            files[gh.RESIDUAL] = files[gh.RESIDUAL].replace(b'WLB_mask|=128;', b'WLB_mask|=0;')
            bad = Path(tmp) / 'tampered.zip'
            bad.write_bytes(gh._zip(files))
            with self.assertRaises(ValueError):
                b.recover(bad)


if __name__ == '__main__':
    unittest.main()
