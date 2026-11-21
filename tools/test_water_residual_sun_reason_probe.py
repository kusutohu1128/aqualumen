"""CPU-only public source recovery tests; never invokes native GL."""
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("SUN_REASON_PROBE_BINARY", str(ROOT / "build/water_residual_sun_reason_probe-v1")))
ORIGINAL = Path(os.environ.get("SUN_REASON_ORIGINAL", "/home/kusutohu/.cache/aqualumen-sun-iris.Y3DNmT/guarded1/shaders"))
REASON = Path(os.environ.get("SUN_REASON_ROOT", "/home/kusutohu/.cache/aqualumen-sun-reasons.EdiKSW/reason/shaders"))


class PublicReasonConstruction(unittest.TestCase):
    def test_observation_erasure_recovers_actual_pinned_helper(self):
        result = subprocess.run([str(BINARY), "--cpu-recovery", str(ORIGINAL)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("actual helper", result.stdout)

    def test_public_loop_accounting_accepts_48_hemisphere_rejections(self):
        # Synthetic category plumbing only; this is not GPU branch evidence.
        result = subprocess.run([str(BINARY), "--cpu-accounting", "3", "48", "0", "0", "1", "0", "48", "1", "1"], text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.strip(), "QUALIFIED")

    def test_actual_reason_pack_recovers_original_geometry_helper_and_main(self):
        result = subprocess.run([str(BINARY), "--cpu-contract", str(ORIGINAL), str(REASON)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("actual pack", result.stdout)

    def test_public_accounting_group_priority_and_negative_payloads(self):
        # CPU integer/accounting constructions only; not actual rejected-node evidence.
        cases = [
            ((9,48,0,0,1,0,48,1,1), True),
            ((8,0,0,48,1,0,48,1,1), True),
            ((6,0,48,0,1,0,48,1,1), True),
            ((0,0,0,0,1,0,1,1,1), True),
            ((0,0,0,0,1,0,0,1,0), True),
            ((3,47,0,0,1,0,48,1,1), False),
            ((3,0,48,0,1,0,48,1,1), False),
            ((8,48,0,0,1,0,48,1,1), False),
            ((0,0,0,0,1,0,48,1,1), False),
            ((3,48,0,0,1,1,48,1,1), False),
            ((3,48,0,0,0,0,48,0,1), False),
            ((3,48,0,0,1,0,48,1,0), False),
            (("nan",0,0,0,1,0,1,1,1), False),
            ((3,47.5,0.5,0,1,0,48,1,1), False),
            ((10,0,0,48,1,0,48,1,1), False),
        ]
        for values, expected in cases:
            with self.subTest(values=values):
                result = subprocess.run([str(BINARY), "--cpu-accounting", *map(str, values)], text=True, capture_output=True, check=True)
                self.assertEqual(result.stdout.strip(), "QUALIFIED" if expected else "REJECTED")


if __name__ == "__main__":
    unittest.main()
