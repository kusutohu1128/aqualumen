"""Accepted-run boundary requires measured, not guessed, underwater camera poses."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

spec = importlib.util.spec_from_file_location("up_report", Path(__file__).resolve().parents[2]/"report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)
WORLD_ID = "b22dbccb-2970-41e6-847f-f183b1ec923d"


class UnderwaterUpReportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="aqualumen-up-report-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.scenario = "underwater-up-near"
        surface, depth = 62.8889, .5
        eye = [448.5,surface-depth,-383.5]
        self.run = dict(run_id="cpu-up-report", expected_resolution=[2560,1440],
            world_generator="minecraft:noise/overworld", shader_active=True, shader_fallback=False,
            pack_sha256="cpu-pack", expected_pack_sha256="cpu-pack", world_id=WORLD_ID,
            world_directory="/isolated/saves/AqualumenNaturalV2", seed=308060,
            scenarios=[self.scenario], sample_seconds=5)
        self.row = dict(report.metrics([1.0]*10), scenario=self.scenario, run_id=self.run["run_id"],
            resolution=[2560,1440], framebuffer_resolution=[2560,1440], pack_sha256="cpu-pack", world_id=WORLD_ID,
            shader_active=True, shader_fallback=False, sample_seconds_actual=5, player_dimension="minecraft:overworld",
            camera_lock=True, camera_follows_local_player=True, expected_camera_rotation=[-45,-90], actual_camera_rotation=[-45,-90],
            actual_player_rotation=[-45,-90],
            actual_player_position=[448.5,surface-1.62-depth,-383.5], actual_eye_position=eye, actual_camera_position=eye,
            camera_first_person=True, camera_eye_match=True, workload="warmed-view",
            underwater_up=dict(scene=self.scenario, requested_player_position=[448.5,surface-1.62-depth,-383.5],
                requested_camera_rotation=[-45,-90], requested_eye_depth=depth, reference_surface_y=surface,
                measured_surface_y=surface, eye_tolerance_m=.05, requested_world_time=6000, terrain_placement=False,
                camera_first_person=True, camera_eye_match=True, player_touching_water=True, player_submerged_in_water=True,
                camera_submersion_type="WATER", actual_world_time=6000, actual_server_world_time=6000,
                actual_eye_depth=depth, actual_eye_position=eye, actual_camera_position=eye))
        def chunk(kind,data):
            return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data))
        image = b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",2560,1440,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(b"\0"*(1440*(1+2560*3))))+chunk(b"IEND",b"")
        (self.directory/(self.scenario+".png")).write_bytes(image)
        (self.directory/(self.scenario+".csv")).write_text("ms\n"+"1.0\n"*10)
        (self.directory/"complete.json").write_text(json.dumps(dict(run_id=self.run["run_id"],status="complete")))

    def load(self):
        (self.directory/"run.json").write_text(json.dumps(self.run))
        (self.directory/(self.scenario+".json")).write_text(json.dumps(self.row))
        return report.load_run(self.directory)

    def test_camera_outside_water_is_rejected_even_when_pose_is_claimed(self):
        self.row["underwater_up"]["camera_submersion_type"] = "NONE"
        with self.assertRaises(ValueError):
            self.load()

    def test_measured_head_and_first_person_booleans_are_required(self):
        for key in ("camera_first_person", "camera_eye_match", "player_touching_water", "player_submerged_in_water"):
            with self.subTest(key=key):
                self.row["underwater_up"][key] = False
                with self.assertRaises(ValueError):
                    self.load()
                self.row["underwater_up"][key] = True

    def test_complete_measured_near_control_is_accepted(self):
        self.assertEqual(len(self.load()[1]), 1)

    def test_fixed_ocean_pose_requires_the_exact_world_uuid_and_seed(self):
        for key, invalid in (("world_id","00000000-0000-0000-0000-000000000000"),
                             ("world_directory","/isolated/saves/AqualumenNaturalV1"), ("seed",308061)):
            with self.subTest(key=key):
                original = self.run[key]
                self.run[key] = invalid
                if key == "world_id": self.row[key] = invalid
                with self.assertRaises(ValueError):
                    self.load()
                self.run[key] = original
                if key == "world_id": self.row[key] = original

    def test_wrong_requested_or_measured_depth_and_daylight_are_rejected(self):
        invalid = {"scene":"underwater-up-deep", "requested_player_position":[448.5,60,-383.5],
            "requested_camera_rotation":[-45,-65], "requested_eye_depth":3.25, "reference_surface_y":63,
            "measured_surface_y":63, "eye_tolerance_m":1, "requested_world_time":18000,
            "actual_world_time":18000, "actual_server_world_time":18000, "terrain_placement":True, "actual_eye_depth":3.25}
        for key, value in invalid.items():
            with self.subTest(key=key):
                original = self.row["underwater_up"][key]
                self.row["underwater_up"][key] = value
                with self.assertRaises(ValueError):
                    self.load()
                self.row["underwater_up"][key] = original

    def test_actual_camera_and_player_eye_must_match_the_claimed_depth(self):
        for key in ("actual_player_position", "actual_eye_position", "actual_camera_position"):
            with self.subTest(key=key):
                original = self.row[key]
                self.row[key] = [original[0],original[1]+1,original[2]]
                with self.assertRaises(ValueError):
                    self.load()
                self.row[key] = original

    def test_deep_and_tilt_controls_accept_only_their_own_measured_poses(self):
        image = (self.directory/(self.scenario+".png")).read_bytes()
        for scene,depth,pitch in (("underwater-up-deep",3.25,-90), ("underwater-up-tilt",.5,-65)):
            with self.subTest(scene=scene):
                self.scenario = scene
                self.run["scenarios"] = [scene]
                eye = [448.5,62.8889-depth,-383.5]
                player = [448.5,62.8889-1.62-depth,-383.5]
                self.row.update(scenario=scene,actual_player_position=player,actual_eye_position=eye,actual_camera_position=eye,
                    expected_camera_rotation=[-45,pitch],actual_camera_rotation=[-45,pitch],actual_player_rotation=[-45,pitch])
                self.row["underwater_up"].update(scene=scene,requested_player_position=player,requested_camera_rotation=[-45,pitch],
                    requested_eye_depth=depth,actual_eye_depth=depth,actual_eye_position=eye,actual_camera_position=eye)
                (self.directory/(scene+".png")).write_bytes(image)
                (self.directory/(scene+".csv")).write_text("ms\n"+"1.0\n"*10)
                self.assertEqual(len(self.load()[1]),1)

    def test_nonfinite_or_different_rendered_and_player_angles_are_rejected(self):
        for key,invalid in (("actual_camera_rotation",[-45,float("nan")]), ("actual_player_rotation",[-45,-65])):
            with self.subTest(key=key):
                original = self.row[key]
                self.row[key] = invalid
                with self.assertRaises(ValueError):
                    self.load()
                self.row[key] = original


if __name__ == "__main__":
    unittest.main()
