"""CPU-only validation of the public local-control/report fixture contract."""
import importlib.util
import copy
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONTROL = load("control", "tools/benchmark-control.py")
REPORT = load("report", "tools/report.py")


def capture_row(scene):
    time = 1000 if scene == "air-sunlit-front" else 11000
    opened = scene == "air-backlit-open"
    eye = [448.5, 161.62, -383.5]
    return {"workload": "air-sun-shadow-test", "actual_eye_position": eye,
            "actual_camera_position": eye, "actual_player_position": [448.5,160,-383.5],
            "actual_camera_rotation": [90,0], "expected_camera_rotation": [90,0],
            "opaque_fixture": {"range": "west-air", "wall_present": not opened,
                "background_color": "magenta", "wall_material": "minecraft:white_concrete",
                "target_material": "minecraft:magenta_concrete", "wall_plane_axis": "x",
                "wall_bounds": [432,157,-387,432,165,-379], "target_bounds": [426,158,-386,426,164,-380],
                "fixed_lights": [[426,164,-386],[426,164,-380]], "placed_cells": 49 if opened else 130,
                "reserved_air_cells": 130, "requested_world_time": time, "actual_world_time": time,
                "actual_server_world_time": time, "requested_player_position": [448.5,160,-383.5],
                "requested_camera_rotation": [90,0], "camera_first_person": True, "camera_eye_match": True,
                "eye_tolerance_m": .05, "actual_eye_position": eye, "actual_camera_position": eye}}


class AirShadowContractTest(unittest.TestCase):
    def test_only_approved_names_and_exact_disposable_uuid_are_authorized(self):
        for scene in ("air-shadow-backlit", "air-sunlit-front", "air-backlit-open"):
            self.assertIn(scene, CONTROL.OPTIONAL_SCENARIOS)
            CONTROL.validate_fixture_world({"world": CONTROL.FIXTURE_WORLD, "world_id": CONTROL.FIXTURE_WORLD_ID}, [scene])
            with self.assertRaises(ValueError):
                CONTROL.validate_fixture_world({"world": "AqualumenNaturalV1", "world_id": CONTROL.FIXTURE_WORLD_ID}, [scene])
            with self.assertRaises(ValueError):
                CONTROL.validate_fixture_world({"world": CONTROL.FIXTURE_WORLD, "world_id": "00000000-0000-0000-0000-000000000000"}, [scene])
        self.assertNotIn("air-shadow-east", CONTROL.OPTIONAL_SCENARIOS)

    def test_report_accepts_exact_sun_controls_and_rejects_false_evidence(self):
        for scene in CONTROL.AIR_SHADOW_SCENARIOS:
            row = capture_row(scene)
            REPORT.validate_opaque_fixture(row, scene)
            for key, wrong in (("wall_plane_axis", "z"), ("wall_bounds", [431,157,-387,432,165,-379]),
                    ("target_material", "minecraft:lime_concrete"), ("actual_world_time", 6000),
                    ("actual_server_world_time", 6000), ("requested_camera_rotation", [0,0]),
                    ("fixed_lights", [[426,164,-386]]), ("reserved_air_cells", 129),
                    ("camera_first_person", False)):
                invalid = copy.deepcopy(row)
                invalid["opaque_fixture"][key] = wrong
                with self.subTest(scene=scene, invalid=key), self.assertRaises(ValueError):
                    REPORT.validate_opaque_fixture(invalid, scene)
            moved = copy.deepcopy(row)
            moved["opaque_fixture"]["actual_camera_position"] = moved["actual_camera_position"] = [448.5,161.62,-387.5]
            with self.assertRaises(ValueError):
                REPORT.validate_opaque_fixture(moved, scene)

    def test_existing_accepted_runs_still_recompute(self):
        # Existing checked-in evidence is optional for a standalone tooling build.
        artifacts = [ROOT / "reports/2026-10-01-v0.3.0" / kind for kind in ("natural", "functional", "cave")]
        artifacts += [ROOT / "reports/2026-10-02-v0.3.1/opaque"]
        for path in artifacts:
            if (path / "complete.json").exists():
                with self.subTest(run=str(path)):
                    run, rows = REPORT.load_run(path)
                    self.assertEqual(len(rows), len(run["scenarios"]))


if __name__ == "__main__":
    unittest.main()
