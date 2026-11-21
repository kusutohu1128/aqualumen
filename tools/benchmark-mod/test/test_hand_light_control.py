"""Carried-light (lamp-hand-*) public control CLI tests; disposable fake directories only, never the real Lab.

Layout mirrors the carried-light runner: <tmp>/Aqualumen Lab/minecraft is the untouched original and
<tmp>/Aqualumen Lab/carried-matrix-<random>/Aqualumen Lab/minecraft is the private duplicated TEST game.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CONTROL = Path(__file__).resolve().parents[2] / "benchmark-control.py"
WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d"
HAND = ["lamp-hand-empty", "lamp-hand-main", "lamp-hand-off", "lamp-hand-soul", "lamp-hand-both",
        "lamp-hand-pillar", "lamp-hand-pillar-empty", "lamp-hand-hidden", "lamp-hand-hidden-off",
        "lamp-hand-hidden-empty", "lamp-hand-walk", "lamp-hand-walk-empty", "lamp-hand-putaway"]
FIXED = [scene for scene in HAND if scene not in ("lamp-hand-walk", "lamp-hand-walk-empty", "lamp-hand-putaway")]


class HandLightControlTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="aqualumen-hand-control-")
        self.addCleanup(self.temporary.cleanup)
        root = Path(os.path.realpath(self.temporary.name))
        self.instance = root / "Aqualumen Lab"
        self.original = self.instance / "minecraft"
        self.matrix = self.instance / "carried-matrix-Q7x9Lp2"
        self.game = self.matrix / "Aqualumen Lab" / "minecraft"
        for game in (self.original, self.game):
            (game / "config").mkdir(parents=True)
            region = game / "saves" / "AqualumenNaturalV2" / "region"
            region.mkdir(parents=True)
            (region.parent / "level.dat").write_bytes(b"level")
            (region / "r.50.-26.mca").write_bytes(b"region")
        self.world = self.game / "saves" / "AqualumenNaturalV2"
        self.configure()
        self.configure(game=self.original)

    def configure(self, world="AqualumenNaturalV2", world_id=WORLD_ID, seed="308060", schema="2",
                  generator="minecraft:noise/overworld", game=None):
        game = game or self.game
        (game / "config/aqualumen-benchmark.properties").write_text(
            f"schema=2\nworld={world}\nworld_id={world_id}\n")
        (game / "saves" / "AqualumenNaturalV2" / "aqualumen-world.properties").write_text(
            f"schema={schema}\nworld_id={world_id}\nseed={seed}\ngenerator={generator}\n")

    def run_scene(self, *scenes, warmup="20", sample="10", game=None, opt_in=True):
        return subprocess.run([sys.executable, "-B", str(CONTROL), "--game", str(game or self.game), "start",
                               "--run-id", "cpu-hand-control", "--warmup", warmup, "--sample", sample, "--scenes", *scenes]
                              + (["--carried-light-test"] if opt_in else []),
                              capture_output=True, text=True)

    def assert_rejected_without_request(self, result, *games):
        self.assertNotEqual(result.returncode, 0)
        for game in (self.game, self.original) + games:
            self.assertFalse((game / "aqualumen-benchmark").exists(), game)

    def test_all_hand_scenes_accepted_in_order(self):
        result = self.run_scene(*HAND)
        self.assertEqual(result.returncode, 0, result.stderr)
        request = json.loads(result.stdout)
        self.assertEqual(request["scenarios"], ",".join(HAND))
        self.assertEqual(request["world_id"], WORLD_ID)
        self.assertEqual(request["carried_light_test"], "private-duplicate-v1")
        self.assertEqual(request["carried_light_test_game"], str(self.game))
        self.assertEqual(request["carried_light_original_game"], str(self.original))
        written = (self.game / "aqualumen-benchmark/request.properties").read_text()
        self.assertIn(f"carried_light_test_game={self.game}\n", written)
        self.assertFalse((self.original / "aqualumen-benchmark").exists())

    def test_opt_in_required_and_only_for_hand_scenes(self):
        self.assert_rejected_without_request(self.run_scene("lamp-hand-main", opt_in=False))
        self.assert_rejected_without_request(self.run_scene("lamp-night-torch"))
        result = self.run_scene("lamp-night-torch", opt_in=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("carried_light_test", json.loads(result.stdout))

    def test_original_game_refused_even_with_opt_in(self):
        self.assert_rejected_without_request(self.run_scene("lamp-hand-main", game=self.original))

    def test_symlink_escapes_refused(self):
        # TEST game directory is a symlink to the untouched original.
        linked = self.instance / "carried-matrix-Link0001" / "Aqualumen Lab"
        linked.mkdir(parents=True)
        (linked / "minecraft").symlink_to(self.original, target_is_directory=True)
        self.assert_rejected_without_request(self.run_scene("lamp-hand-main", game=linked / "minecraft"))
        # Matrix directory is a symlink to the real duplicate.
        alias = self.instance / "carried-matrix-Link0002"
        alias.symlink_to(self.matrix, target_is_directory=True)
        self.assert_rejected_without_request(self.run_scene("lamp-hand-main", game=alias / "Aqualumen Lab" / "minecraft"))
        # Saves/world inside the duplicate points at the original world.
        moved = self.world.with_name("AqualumenNaturalV2-real")
        self.world.rename(moved)
        self.world.symlink_to(self.original / "saves" / "AqualumenNaturalV2", target_is_directory=True)
        self.assert_rejected_without_request(self.run_scene("lamp-hand-main"))
        self.world.unlink()
        moved.rename(self.world)
        # A region file symlinked or hard-linked to the original's.
        source = self.original / "saves/AqualumenNaturalV2/region/r.50.-26.mca"
        for make in (lambda target: target.symlink_to(source), lambda target: os.link(source, target)):
            target = self.world / "region" / "r.0.0.mca"
            make(target)
            self.assert_rejected_without_request(self.run_scene("lamp-hand-main"))
            target.unlink()
        result = self.run_scene("lamp-hand-main")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_directory_convention_refused(self):
        for matrix in ("carried-matrix-", "carried-matrix-ab", "matrix-Q7x9Lp2", "carried-matrix-Q7x9Lp2!"):
            with self.subTest(matrix=matrix):
                other = self.instance / matrix / "Aqualumen Lab" / "minecraft"
                (other / "config").mkdir(parents=True)
                (other / "saves" / "AqualumenNaturalV2").mkdir(parents=True)
                (other / "config/aqualumen-benchmark.properties").write_text(
                    (self.game / "config/aqualumen-benchmark.properties").read_text())
                (other / "saves/AqualumenNaturalV2/aqualumen-world.properties").write_text(
                    (self.world / "aqualumen-world.properties").read_text())
                self.assert_rejected_without_request(self.run_scene("lamp-hand-main", game=other), other)

    def test_missing_original_refused(self):
        moved = self.original.with_name("minecraft-moved")
        self.original.rename(moved)
        self.assert_rejected_without_request(self.run_scene("lamp-hand-main"))

    def test_wrong_seed_uuid_folder_schema_or_generator_rejected(self):
        for patch in ({"seed": "308061"}, {"world_id": "00000000-0000-0000-0000-000000000000"},
                      {"world": "AqualumenNaturalV1"}, {"schema": "1"}, {"generator": "minecraft:flat"}):
            with self.subTest(patch=patch):
                self.configure(**patch)
                self.assert_rejected_without_request(self.run_scene("lamp-hand-main"))

    def test_sequences_need_schedule_plus_settled_end(self):
        for scene in ("lamp-hand-walk", "lamp-hand-walk-empty", "lamp-hand-putaway"):
            with self.subTest(scene=scene):
                self.assert_rejected_without_request(self.run_scene(scene, sample="8"))
        result = self.run_scene("lamp-hand-walk", "lamp-hand-walk-empty", "lamp-hand-putaway", sample="9")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_fixed_pairs_accept_short_sample(self):
        result = self.run_scene(*FIXED, sample="5")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_short_warmup_rejected(self):
        self.assert_rejected_without_request(self.run_scene("lamp-hand-empty", warmup="10"))

    def test_unknown_hand_variant_is_not_a_choice(self):
        for scene in ("lamp-hand-red", "lamp-hand-main-off", "lamp-hand"):
            with self.subTest(scene=scene):
                self.assert_rejected_without_request(self.run_scene(scene))

    def test_mixing_with_original_lamp_scenes_keeps_guards(self):
        result = self.run_scene("lamp-night-torch", "lamp-hand-main", "lamp-hand-empty")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["carried_light_test_game"], str(self.game))

    def test_only_isolated_lab_directory(self):
        other = Path(self.temporary.name) / "Survival" / "minecraft"
        other.mkdir(parents=True)
        result = self.run_scene("lamp-hand-main", game=other)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((other / "aqualumen-benchmark").exists())
        self.assertFalse((self.original / "aqualumen-benchmark").exists())


if __name__ == "__main__":
    unittest.main()
