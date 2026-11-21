"""Public source/build contract; no Minecraft or GL."""
import pathlib
import unittest
import tempfile

import water_sun_profile_build as profile

ROOT=pathlib.Path(__file__).resolve().parents[1]

class ProfileBuildTests(unittest.TestCase):
    def test_generated_sources_recover_all_exact_frozen_parents(self):
        generated=profile.construct(ROOT)
        for name,data in generated.items():
            self.assertEqual(profile.recover(name,data),(ROOT/name).read_bytes())

    def test_changed_source_is_refused_before_generation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=pathlib.Path(temporary);name=next(iter(profile.PINS));target=root/name
            target.parent.mkdir(parents=True);target.write_bytes((ROOT/name).read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'source pin mismatch'):
                profile.construct(root)

    def test_existing_output_is_not_overwritten(self):
        output=ROOT/'reports/2026-10-03-water-performance/cpu-profile/pair-v1'
        with self.assertRaisesRegex(ValueError,'expected NEW output'):
            profile.build(output)

    def test_generated_hash_retains_exact_original_data_and_boolean(self):
        generated=profile.construct(ROOT)
        name=profile.BENCH+'dev/aqualumen/bench/BathymetrySnapshot.java'
        original=profile.HASH_BODY.encode()
        literal=generated[name].split(b'SunPerformance.hash(()->',1)[1].split(b';',1)[0][:-1]
        self.assertEqual(literal.replace(b'SunPerformance.bytes('+profile.HASH_READ.encode()+b')',profile.HASH_READ.encode()),original)

if __name__=="__main__":
    unittest.main()
