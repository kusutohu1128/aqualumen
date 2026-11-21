"""Public control CLI tests use disposable fake directories, never the real Lab."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CONTROL = Path(__file__).resolve().parents[2] / "benchmark-control.py"
WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d"


class UnderwaterUpControlTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="aqualumen-up-control-")
        self.addCleanup(self.temporary.cleanup)
        self.game = Path(self.temporary.name) / "Aqualumen Lab" / "minecraft"
        (self.game / "config").mkdir(parents=True)
        self.world = self.game / "saves" / "AqualumenNaturalV2"
        self.world.mkdir(parents=True)
        self.configure()

    def configure(self, world="AqualumenNaturalV2", world_id=WORLD_ID, seed="308060"):
        (self.game / "config/aqualumen-benchmark.properties").write_text(
            f"schema=2\nworld={world}\nworld_id={world_id}\n")
        (self.world / "aqualumen-world.properties").write_text(
            f"schema=2\nworld_id={world_id}\nseed={seed}\ngenerator=minecraft:noise/overworld\n")

    def run_scene(self, *scenes):
        return subprocess.run([sys.executable, "-B", str(CONTROL), "--game", str(self.game), "start",
            "--run-id", "cpu-up-control", "--warmup", "5", "--sample", "5", "--scenes", *scenes],
            capture_output=True, text=True)

    def test_rain_close_declines_wrong_seed(self):
        self.configure(seed="308061")
        result = self.run_scene("coast-rain-close")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.game / "aqualumen-benchmark").exists())

    def test_public_cli_accepts_near_upward_control(self):
        result = self.run_scene("underwater-up-near")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["scenarios"], "underwater-up-near")

    def test_wrong_world_identity_rejects_before_any_request_directory(self):
        self.configure(world_id="00000000-0000-0000-0000-000000000000")
        result = self.run_scene("underwater-up-near")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.game / "aqualumen-benchmark").exists())

    def test_wrong_seed_rejects_before_any_request_directory(self):
        self.configure(seed="308061")
        result = self.run_scene("underwater-up-deep")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.game / "aqualumen-benchmark").exists())

    def test_public_cli_accepts_all_three_optional_controls(self):
        scenes = ("underwater-up-near", "underwater-up-deep", "underwater-up-tilt")
        result = self.run_scene(*scenes)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["scenarios"], ",".join(scenes))

    def test_other_world_folder_or_marker_is_rejected_without_requests(self):
        for world, marker_patch in (("AqualumenNaturalV1", None), ("AqualumenNaturalV2", "schema=1"),
                                    ("AqualumenNaturalV2", "generator=minecraft:flat")):
            with self.subTest(world=world, patch=marker_patch):
                self.configure(world=world)
                if marker_patch:
                    marker = self.world / "aqualumen-world.properties"
                    key = marker_patch.split("=",1)[0]
                    marker.write_text("\n".join(line for line in marker.read_text().splitlines() if not line.startswith(key+"="))+"\n"+marker_patch+"\n")
                result = self.run_scene("underwater-up-tilt")
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.game / "aqualumen-benchmark").exists())


if __name__ == "__main__":
    unittest.main()
