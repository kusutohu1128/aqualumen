"""CPU-only checks for extracting a timed scene with an unpublished pack."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "2026-11-21-animal-light/timing"))
import measure


class StagedPackTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.enterContext(patch.object(measure, "root", root))
        self.enterContext(patch.object(measure, "packet", root))
        self.run_dir = root / "fixture"
        self.run_dir.mkdir()
        self.pack = root / "Aqualumen-1.9.0-preview.8.zip"
        with ZipFile(self.pack, "w") as archive:
            archive.writestr("LICENSE", "fixture")
        capture = self.run_dir / "both-west-ingame.png"
        capture.write_bytes(b"fixture capture")
        receipt = {
            "complete": True, "originalWorldAndConfigUnchanged": True, "shaderpackLogged": True,
            "gl": {"renderer": "fixture RTX 3080 Ti"}, "size": [2560, 1440],
            "packSha256": hashlib.sha256(self.pack.read_bytes()).hexdigest(),
            "screenshots": {"both-west": {"ingame": hashlib.sha256(capture.read_bytes()).hexdigest()}},
        }
        (self.run_dir / "complete.json").write_text(json.dumps(receipt))

    def write_window(self, batches=13, still=True):
        records = ["Changing view distance to 12", "[Server] AQLAVA_READY_both-west_END",
                   "fixture.pngとして保存しました"]
        for index in range(batches):
            records.append(f"AQ_RENDER_INTERVALS_US {(index + 1) * 1000} " + " ".join(["25000"] * 40))
        if still:
            records.append("[Server] AQLAVA_STILL_both-west_END")
        (self.run_dir / "client.log").write_text("\n".join(records))

    def extract(self):
        return measure.extract("fixture", "both-west", 8, pack_path=self.pack)

    def test_staged_archive_without_dist(self):
        self.write_window()
        row = self.extract()
        self.assertEqual((row["frames"], row["seconds"], row["meanFps"], row["p99Ms"]),
                         (400, 10.0, 40.0, 25.0))

    def test_substituted_archive_under_same_name(self):
        self.write_window()
        with ZipFile(self.pack, "w") as archive:
            archive.writestr("LICENSE", "different bytes")
        with self.assertRaises(AssertionError):
            self.extract()

    def test_missing_still(self):
        self.write_window(still=False)
        with self.assertRaises(ValueError):
            self.extract()

    def test_truncated_sample(self):
        self.write_window(batches=12)
        with self.assertRaises(AssertionError):
            self.extract()


if __name__ == "__main__":
    unittest.main()
