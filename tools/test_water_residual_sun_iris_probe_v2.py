"""CPU-only public actual-saved-output regression; never invokes native GL."""
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("SUN_IRIS_PROBE_BINARY", str(ROOT / "build/water_residual_sun_iris_probe-v2")))
SAVED = ROOT / "reports/2026-10-03-water-residual-sun-iris/root-native-passivity"


class SavedNativeProtocol(unittest.TestCase):
    def test_actual_saved_eight_cases_have_public_parseable_sample_arrays(self):
        result = subprocess.run([str(BINARY), "--cpu-saved-samples", str(SAVED)], text=True, capture_output=True, check=True)
        report = json.loads(result.stdout)
        self.assertFalse(report["native_execution"])
        self.assertEqual(len(report["cases"]), 8)
        self.assertEqual({len(case["samples"]) for case in report["cases"]}, {6})
        sample = report["cases"][0]["samples"][0]
        self.assertEqual(sample["pixel"], [128, 128])
        self.assertEqual(sample["covariance_original_flags"][3], 15)

    def test_actual_saved_pure_observer_stage_roundoff_keeps_entire_fixed_roi(self):
        result = subprocess.run([str(BINARY), "--cpu-stage-contract", str(SAVED)], text=True, capture_output=True, check=True)
        report = json.loads(result.stdout)
        self.assertFalse(report["native_execution"])
        self.assertEqual(len(report["cases"]), 8)
        for case in report["cases"]:
            self.assertEqual(case["ROI_points"], 5025)
            self.assertEqual(case["qualified_stage_points"], 5025)
            self.assertEqual(case["literal_one_points"], 2002)
            self.assertTrue(case["pure_observer_exact"])

    def test_public_stage_contract_rejects_missing_marker_nonfinite_and_wrong_simplex(self):
        for values in [("0.25", "0.25", "0.5", "0.9999999403953552")]:
            result = subprocess.run([str(BINARY), "--cpu-stage-vector", *values], text=True, capture_output=True, check=True)
            self.assertEqual(result.stdout.strip(), "QUALIFIED")
        for values in [("0.25", "0.25", "0.5", "0"), ("0.2", "0.2", "0.2", "1"),
                       ("-0.001", "0.5", "0.501", "1"), ("nan", "0.5", "0.5", "1"),
                       ("0.25", "0.25", "0.5", "1.000002")]:
            with self.subTest(values=values):
                result = subprocess.run([str(BINARY), "--cpu-stage-vector", *values], text=True, capture_output=True, check=True)
                self.assertEqual(result.stdout.strip(), "REJECTED")


if __name__ == "__main__":
    unittest.main()
