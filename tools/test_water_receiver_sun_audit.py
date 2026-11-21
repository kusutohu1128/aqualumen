"""Actual saved packet reader controls; replace only external capture bytes."""
import array
from pathlib import Path
import shutil
import tempfile
import unittest
from water_receiver_sun_audit import OUT, audit


class WorldSunAudit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aqualumen-world-sun-audit-")
        self.packet = Path(self.temp.name)
        shutil.copytree(OUT / "native-v1", self.packet / "native-v1")

    def tearDown(self):
        self.temp.cleanup()

    def mutate(self, name, index, value):
        path = self.packet / "native-v1/raw" / name
        data = array.array("f")
        data.frombytes(path.read_bytes())
        data[index] = value
        with path.open("wb") as stream:
            stream.write(data.tobytes())

    def test_actual_positive_and_invalid_controls_pass(self):
        self.assertTrue(audit(self.packet)["nonzeroWorldSourceSunValidatedForFlatSyntheticFixture"])

    def test_missing_positive_power_is_rejected(self):
        self.mutate("world-sun-positive-C0.rgba32f", (53 * 129 + 65) * 4, 0)
        self.mutate("world-sun-positive-witness-C0.rgba32f", (53 * 129 + 65) * 4, 0)
        with self.assertRaises(ValueError):
            audit(self.packet)

    def test_unrelated_channel_power_is_rejected(self):
        self.mutate("world-sun-positive-C0.rgba32f", (53 * 129 + 65) * 4 + 1, 1)
        self.mutate("world-sun-positive-witness-C0.rgba32f", (53 * 129 + 65) * 4 + 1, 1)
        with self.assertRaises(ValueError):
            audit(self.packet)

    def test_missing_direct_source_cannot_acquire_material(self):
        self.mutate("missing-direct-tag-C0.rgba32f", (53 * 129 + 65) * 4, 1)
        with self.assertRaises(ValueError):
            audit(self.packet)

    def test_zero_cache_is_not_a_nonzero_solar_test(self):
        self.mutate("positive-solar-cache.rgba32f", (31 * 64) * 4, 0)
        with self.assertRaises(ValueError):
            audit(self.packet)


if __name__ == "__main__":
    unittest.main()
