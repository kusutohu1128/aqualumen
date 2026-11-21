"""Public saved-output contracts; synthetic CPU tests are not native evidence."""
import json
import copy
import hashlib
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from tools import water_sun_prepared_audit as prepared

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/water_sun_prepared_audit.py"


class PreparedAuditTests(unittest.TestCase):
    @staticmethod
    def normal_maps():
        # Analytic CPU fixture: v=(0,-1,0), target=(0,1,0), eta=1.5.
        # These are synthetic integer records, NOT claimed GPU observations.
        bits = [0, 0xbf800000, 0, 0, 0x3f800000, 0, 0x3fc00000]
        signed = lambda x: x & 0xffffffff
        rows = [[2, *bits[:3]], bits[3:], [0, 0, 1, 2],
                [signed(-16777216), signed(-16777216), 1, 1],
                [0, 0, 1, 1], [37748736, 37748736, 1, 0],
                [16777216, 16777216, 1, 0], [37748736, 37748736, 1, 0]]
        return [(bits, 1)], {role: [[row.copy() for row in rows] for _ in range(2)]
                            for role in ("old", "wrapper", "reused")}

    def test_literal_normal_record_checks_intervals_and_has_no_native_claim(self):
        cases, maps = self.normal_maps()
        result = prepared.validate_maps(cases, maps)
        self.assertEqual(result["classes"], {"unknown": 0, "absent": 0, "supported": 1})
        self.assertEqual(result["intervalTriplesVerified"], 36)
        self.assertFalse(result["nativeGLExecuted"])

    def test_missing_packet_is_explicitly_inconclusive_not_native_success(self):
        with tempfile.TemporaryDirectory(prefix="aqualumen-prepared-audit-") as tmp:
            run = subprocess.run([sys.executable, str(TOOL), str(Path(tmp)/"missing")],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            result = json.loads(run.stdout)
            self.assertEqual(result["status"], "INCONCLUSIVE")
            self.assertFalse(result["accepted"])
            self.assertFalse(result["nativeGLExecuted"])

    def test_synthetic_completed_result_cannot_become_native_proof(self):
        with tempfile.TemporaryDirectory(prefix="aqualumen-prepared-synthetic-") as tmp:
            packet = Path(tmp)
            (packet/"result.json").write_text(json.dumps({"syntheticOnly": True,
                                                         "status": "PASS", "accepted": True}))
            with self.assertRaisesRegex(ValueError, "[Ss]ynthetic"):
                prepared.audit(packet)

    def test_changed_endpoint_is_detected_despite_unchanged_class(self):
        cases, maps = self.normal_maps()
        for repeat in maps["reused"]:
            repeat[5][0] += 1
        with self.assertRaisesRegex(ValueError, "Interval"):
            prepared.validate_maps(cases, maps)

    def test_lost_signed_zero_input_bit_is_rejected(self):
        cases, maps = self.normal_maps()
        cases[0][0][0] = 0x80000000
        with self.assertRaisesRegex(ValueError, "echo"):
            prepared.validate_maps(cases, maps)

    def test_repeat_ulp_or_missing_role_is_rejected(self):
        cases, maps = self.normal_maps()
        maps["wrapper"][1][7][0] += 1
        with self.assertRaisesRegex(ValueError, "Repeat"):
            prepared.validate_maps(cases, maps)
        cases, maps = self.normal_maps()
        del maps["wrapper"]
        with self.assertRaisesRegex(ValueError, "role"):
            prepared.validate_maps(cases, maps)

    def test_invalid_uint32_or_boolean_cannot_be_observed_integer(self):
        cases, maps = self.normal_maps()
        for invalid in (-1, 0x100000000, True, 1.0):
            corrupted = copy.deepcopy(maps)
            corrupted["old"][0][0][0] = corrupted["old"][1][0][0] = invalid
            with self.subTest(value=invalid), self.assertRaisesRegex(ValueError, "uint32"):
                prepared.validate_maps(cases, corrupted)

    def test_stale_or_duplicate_manifest_cannot_be_native_evidence(self):
        with tempfile.TemporaryDirectory(prefix="aqualumen-prepared-stale-") as tmp:
            packet = Path(tmp)
            for raw in ('{"schema":"old-schema"}', '{"schema":"x","schema":"x"}',
                        '{"schema":NaN}'):
                (packet/"result.json").write_text(raw)
                with self.assertRaises(ValueError):
                    prepared.audit(packet)

    def test_completed_root_native_packet_replays_with_executed_not_agent_binary(self):
        packet = ROOT/"reports/2026-10-03-water-prepared/node-native-v1"
        receipt = packet.parent/"root-node-receipt.json"
        if not receipt.is_file():
            self.skipTest("Actual root GPU packet is not present; no synthetic replacement")
        result = prepared.audit(packet, receipt)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["count"], 376)
        self.assertEqual(result["classes"], {"unknown": 27, "absent": 29, "supported": 320})
        self.assertEqual(result["probeBinarySHA256"],
                         "41703de8168f0877b04793e99fb2221f571ea3fa9398b2d04df6c563bd75aa93")
        self.assertFalse(result["waterMainAccepted"])

    def test_saved_actual_routes_storage_and_chronology_corruptions_fail_closed(self):
        original = ROOT/"reports/2026-10-03-water-prepared/node-native-v1"
        receipt = original.parent/"root-node-receipt.json"
        if not receipt.is_file():
            self.skipTest("Actual packet absent; no fabricated native replacement")
        with tempfile.TemporaryDirectory(prefix="aqualumen-prepared-corrupt-") as tmp:
            packet = Path(tmp)/original.name
            shutil.copytree(original, packet)
            base = json.loads((packet/"result.json").read_text())
            for kind in ("routes", "storage", "chronology", "summary"):
                corrupted = copy.deepcopy(base)
                if kind == "routes":
                    corrupted["uploads"][0]["actualState"]["allEightDrawBuffers"][7] = 0
                elif kind == "storage":
                    corrupted["targets"][7]["internalFormat"] = 34836
                elif kind == "chronology":
                    corrupted["uploads"][1]["selected"] += 1
                else:
                    corrupted["results"][0]["classes"][0] = True
                (packet/"result.json").write_text(json.dumps(corrupted))
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    prepared.audit(packet, receipt)

    def test_saved_raw_changed_endpoint_cannot_pass_by_updating_digest_ledger(self):
        original = ROOT/"reports/2026-10-03-water-prepared/node-native-v1"
        receipt = original.parent/"root-node-receipt.json"
        if not receipt.is_file():
            self.skipTest("Actual packet absent; no fabricated native replacement")
        with tempfile.TemporaryDirectory(prefix="aqualumen-prepared-endpoint-") as tmp:
            packet = Path(tmp)/original.name
            shutil.copytree(original, packet)
            result = json.loads((packet/"result.json").read_text())
            for name in ("reused-slot5.rgba32ui", "reused-repeat-slot5.rgba32ui"):
                raw = bytearray((packet/name).read_bytes())
                raw[0] ^= 1
                (packet/name).write_bytes(raw)
                result["rawSHA256"][name] = hashlib.sha256(raw).hexdigest()
            (packet/"result.json").write_text(json.dumps(result))
            with self.assertRaisesRegex(ValueError, "Interval"):
                prepared.audit(packet, receipt)

    def test_every_old_and_wrapper_record_is_checked_even_when_both_repeats_match(self):
        original = ROOT/"reports/2026-10-03-water-prepared/node-native-v1"
        receipt = original.parent/"root-node-receipt.json"
        if not receipt.is_file():
            self.skipTest("Actual packet absent; no fabricated native replacement")
        for role in ("old", "wrapper"):
            for kind, slot, word in (("endpoint", 5, 0), ("class", 0, 0), ("input", 0, 1)):
                with self.subTest(role=role, kind=kind), tempfile.TemporaryDirectory(
                        prefix="aqualumen-prepared-every-role-") as tmp:
                    packet = Path(tmp)/original.name
                    shutil.copytree(original, packet)
                    result = json.loads((packet/"result.json").read_text())
                    for prefix in (role+"-", role+"-repeat-"):
                        name = prefix+f"slot{slot}.rgba32ui"
                        raw = bytearray((packet/name).read_bytes())
                        raw[word*4] ^= 1
                        (packet/name).write_bytes(raw)
                        result["rawSHA256"][name] = hashlib.sha256(raw).hexdigest()
                    (packet/"result.json").write_text(json.dumps(result))
                    with self.assertRaises(ValueError):
                        prepared.audit(packet, receipt)


if __name__ == "__main__":
    unittest.main()
