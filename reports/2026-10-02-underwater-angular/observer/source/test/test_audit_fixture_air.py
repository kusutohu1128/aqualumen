"""Synthetic boundary tests for the read-only saved-fixture audit; no world I/O."""
import importlib.util
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("fixture_audit", ROOT / "tools/audit-fixture-air.py")
AUDIT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(AUDIT)


class FixtureAuditTest(unittest.TestCase):
    def test_approved_plots_have_exact_390_unique_cells(self):
        cells, plots = AUDIT.approved_cells()
        self.assertEqual(len(cells), 390)
        self.assertEqual([plot["cells"] for plot in plots], [81,49,81,49,81,49])
        self.assertEqual(plots[-2]["bounds"], [432,157,-387,432,165,-379])
        self.assertEqual(plots[-1]["bounds"], [426,158,-386,426,164,-380])
        self.assertEqual(len({(x//16,z//16) for x,y,z in cells}), 8)
        self.assertTrue(all((x//512,z//512)==(0,-1) for x,y,z in cells))

    def test_exact_name_uuid_seed_authorization(self):
        marker = {"world_id": AUDIT.UUID, "seed": AUDIT.SEED, "schema": "2", "generator": "minecraft:noise/overworld"}
        AUDIT.validate_marker("AqualumenNaturalV2", marker)
        for field, wrong in (("world_id", "00000000-0000-0000-0000-000000000000"), ("seed", "0"),
                             ("schema", "1"), ("generator", "minecraft:flat")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                AUDIT.validate_marker("AqualumenNaturalV2", {**marker, field:wrong})
        with self.assertRaises(ValueError):
            AUDIT.validate_marker("UserWorld", marker)

    def test_nbt_rejects_truncation_negative_oversized_and_nested_payloads(self):
        # Valid empty compound root, then controlled malformed external input.
        self.assertEqual(AUDIT.NBT(b"\x0a\x00\x00\x00").root(), {})
        for payload in (b"", b"\x0a\x00\x00", b"\x0a\x00\x00\x00\x00",
                        b"\x0a\x00\x00\x09\x00\x00\x01" + struct.pack(">i", -1),
                        b"\x0a\x00\x00\x09\x00\x00\x01" + struct.pack(">i", AUDIT.LIMIT+1),
                        b"\x0a\x00\x00" * 67 + b"\x00" * 67):
            with self.subTest(payload=payload[:20]), self.assertRaises(ValueError):
                AUDIT.NBT(payload).root()

    def test_padded_palette_words_decode_actual_cell_and_do_not_assume_air(self):
        palette = [{"Name": "minecraft:air"}] + [{"Name": f"test:block_{i}"} for i in range(1,17)]
        # 5-bit values use 12 entries per long, not cross-long contiguous bits.
        words = [0] * 342
        for index in (11,12,4095):
            words[index//12] |= 16 << ((index%12)*5)
        chunk = {"sections": [{"Y":9, "block_states": {"palette":palette, "data":words}}]}
        for x,y,z in ((11,144,0),(12,144,0),(15,159,15)):
            self.assertEqual(AUDIT.block_state(chunk,x,y,z), {"Name":"test:block_16"})
        self.assertEqual(AUDIT.block_state(chunk,0,144,0), {"Name":"minecraft:air"})
        with self.assertRaises(ValueError):
            AUDIT.block_state({"sections":[]},0,144,0)
        chunk["sections"][0]["block_states"]["data"] = []
        with self.assertRaises(ValueError):
            AUDIT.block_state(chunk,0,144,0)

    def test_anvil_chunk_lengths_codecs_and_coordinates_fail_closed(self):
        def named_int(name, value):
            key = name.encode()
            return b"\x03" + struct.pack(">H",len(key)) + key + struct.pack(">i",value)
        payload = b"\x0a\x00\x00" + named_int("DataVersion",3955) + named_int("xPos",27) + named_int("zPos",-23) + b"\x00"
        import zlib
        compressed = zlib.compress(payload)
        region = bytearray(12288)
        slot = 27 + (-23 % 32) * 32
        region[slot*4:slot*4+4] = struct.pack(">I",(2<<8)|1)
        region[8192:8196] = struct.pack(">I",len(compressed)+1)
        region[8196] = 2
        region[8197:8197+len(compressed)] = compressed
        actual, record = AUDIT.decode_chunk(region,None,27,-23)
        self.assertEqual((actual["xPos"],actual["zPos"]),(27,-23))
        self.assertEqual(record["codec"],2)
        for codec in (1,4,130):
            region[8196] = codec
            with self.subTest(codec=codec), self.assertRaises(ValueError):
                AUDIT.decode_chunk(region,None,27,-23)
        region[8196] = 2
        region[8192:8196] = struct.pack(">I",5000)
        with self.assertRaises(ValueError):
            AUDIT.decode_chunk(region,None,27,-23)


if __name__ == "__main__":
    unittest.main()
