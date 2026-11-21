"""Public saved-packet audit controls; only external capture bytes are replaced."""
import array
from pathlib import Path
import shutil
import tempfile
import unittest
from water_receiver_main_audit import OUT, audit


class CapturedMainAudit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aqualumen-receiver-main-audit-")
        self.packet = Path(self.temp.name)
        for name in ("native-v2-receipt.json", "native-v2.log", "native-v2-probe"):
            shutil.copy2(OUT / name, self.packet / name)
        for name in ("native-v2", "frozen-source-v2"):
            shutil.copytree(OUT / name, self.packet / name)

    def tearDown(self):
        self.temp.cleanup()

    def replace_capture(self, name, x, y, channel, value):
        path = self.packet / "native-v2" / name
        data = array.array("f")
        data.frombytes(path.read_bytes())
        data[(y * 129 + x) * 4 + channel] = value
        with path.open("wb") as stream:
            stream.write(data.tobytes())

    def test_actual_qualified_capture_passes(self):
        self.assertTrue(audit(self.packet)["boundedFirstSourceTransportPassed"])

    def test_missing_camera_hidden_response_is_rejected(self):
        path = self.packet / "native-v2/neutral-C0.rgba32f"
        baseline = array.array("f")
        baseline.frombytes(path.read_bytes())
        self.replace_capture("hidden-tag-C0.rgba32f", 65, 53, 1, baseline[(53 * 129 + 65) * 4 + 1])
        with self.assertRaises(ValueError):
            audit(self.packet)

    def test_borrowed_far_radiance_is_rejected(self):
        self.replace_capture("visible-tag-C0.rgba32f", 65, 41, 1, .5)
        with self.assertRaises(ValueError):
            audit(self.packet)

    def test_wrong_outgoing_geometry_path_is_rejected(self):
        self.replace_capture("witness-state3.rgba32f", 65, 53, 3, 20)
        with self.assertRaises(ValueError):
            audit(self.packet)

    def test_nonpassive_observation_is_rejected(self):
        self.replace_capture("witness-C0.rgba32f", 65, 53, 0, .7)
        with self.assertRaises(ValueError):
            audit(self.packet)


if __name__ == "__main__":
    unittest.main()
