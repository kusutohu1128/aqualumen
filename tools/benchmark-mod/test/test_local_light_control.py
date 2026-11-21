"""Local-light public control CLI tests; disposable fake directories only, never the real Lab."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CONTROL = Path(__file__).resolve().parents[2] / "benchmark-control.py"
WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d"
SCENES = ["lamp-day-off", "lamp-day-torch", "lamp-day-wall", "lamp-day-wall-off", "lamp-night-off",
          "lamp-night-torch", "lamp-night-soul", "lamp-night-both", "lamp-night-wall", "lamp-night-wall-off",
          "lamp-night-water", "lamp-night-moving", "lamp-day-canopy", "lamp-night-glass", "lamp-night-glass-off",
          "lamp-night-walk", "lamp-night-walk-east", "lamp-night-walk-west"]


class LocalLightControlTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="aqualumen-lamp-control-")
        self.addCleanup(self.temporary.cleanup)
        self.game = Path(self.temporary.name) / "Aqualumen Lab" / "minecraft"
        (self.game / "config").mkdir(parents=True)
        self.world = self.game / "saves" / "AqualumenNaturalV2"
        self.world.mkdir(parents=True)
        self.configure()

    def configure(self, world="AqualumenNaturalV2", world_id=WORLD_ID, seed="308060", schema="2",
                  generator="minecraft:noise/overworld"):
        (self.game / "config/aqualumen-benchmark.properties").write_text(
            f"schema=2\nworld={world}\nworld_id={world_id}\n")
        (self.world / "aqualumen-world.properties").write_text(
            f"schema={schema}\nworld_id={world_id}\nseed={seed}\ngenerator={generator}\n")

    def run_scene(self, *scenes, warmup="20", sample="10"):
        return subprocess.run([sys.executable, "-B", str(CONTROL), "--game", str(self.game), "start",
            "--run-id", "cpu-lamp-control", "--warmup", warmup, "--sample", sample, "--scenes", *scenes],
            capture_output=True, text=True)

    def assert_rejected_without_request(self, result):
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.game / "aqualumen-benchmark").exists())

    def test_all_sibling_scenes_accepted_in_order(self):
        result = self.run_scene(*SCENES)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["scenarios"], ",".join(SCENES))

    def test_wrong_seed_uuid_folder_schema_or_generator_rejected(self):
        for patch in ({"seed": "308061"}, {"world_id": "00000000-0000-0000-0000-000000000000"},
                      {"world": "AqualumenNaturalV1"}, {"schema": "1"}, {"generator": "minecraft:flat"}):
            with self.subTest(patch=patch):
                self.configure(**patch)
                self.assert_rejected_without_request(self.run_scene("lamp-night-wall"))

    def test_short_warmup_rejected_for_mesh_and_light_updates(self):
        self.assert_rejected_without_request(self.run_scene("lamp-day-off", warmup="10"))

    def test_unknown_lamp_variant_is_not_a_choice(self):
        for scene in ("lamp-day-soul", "lamp-day-glass", "lamp-night-walk-mid"):
            with self.subTest(scene=scene):
                self.assert_rejected_without_request(self.run_scene(scene))

    def test_original_twelve_still_accept_five_second_sample(self):
        result = self.run_scene(*SCENES[:12], sample="5")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_walk_needs_route_plus_held_end_sample(self):
        self.assert_rejected_without_request(self.run_scene("lamp-night-walk", sample="8"))
        result = self.run_scene("lamp-night-walk", sample="9")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_fixed_walk_views_and_new_pairs_accept_short_sample(self):
        result = self.run_scene("lamp-day-canopy", "lamp-night-glass", "lamp-night-glass-off",
                                "lamp-night-walk-east", "lamp-night-walk-west", sample="5")
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
