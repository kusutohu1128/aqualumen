"""CPU-only regression checks for completed screenshot evidence."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

REPORT = Path(__file__).resolve().parents[2] / "report.py"
spec = importlib.util.spec_from_file_location("aqualumen_report", REPORT)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def chunk(kind, data=b""):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png(width=2, height=2, color=2, scanlines=None):
    channels = 3 if color == 2 else 4
    if scanlines is None:
        scanlines = b"\0" * (height * (1 + width * channels))
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND"))


class PngIntegrityTest(unittest.TestCase):
    def test_truncated_screenshot_is_not_accepted_as_visual_evidence(self):
        with self.assertRaises(ValueError):
            report.check_png_bytes(png()[:-1], (2, 2))

    def test_corrupt_complete_zlib_stream_is_rejected(self):
        ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
        corrupt = b"\x89PNG\r\n\x1a\n" + ihdr + chunk(b"IDAT", b"not-zlib") + chunk(b"IEND")
        with self.assertRaises(ValueError):
            report.check_png_bytes(corrupt, (2, 2))

    def test_complete_rgb_and_rgba_screenshots_are_accepted(self):
        for color in (2, 6):
            with self.subTest(color=color):
                report.check_png_bytes(png(color=color), (2, 2))

    def test_crc_is_checked_for_every_chunk_including_ancillary(self):
        raw = png()
        for offset in (16, 44, len(raw) - 1):
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                corrupted = bytearray(raw)
                corrupted[offset] ^= 1
                report.check_png_bytes(corrupted, (2, 2))
        bad_ancillary = chunk(b"tEXt", b"note\0capture")[:-1] + b"\0"
        with self.assertRaises(ValueError):
            report.check_png_bytes(raw[:33] + bad_ancillary + raw[33:], (2, 2))

    def test_exact_dimensions_and_supported_format_are_required(self):
        for size in ((3, 2), (2, 3), (True, 2), (2561, 1440)):
            with self.subTest(size=size), self.assertRaises(ValueError):
                report.check_png_bytes(png(), size)
        for depth, color, compression, filtering, interlace in (
                (16, 2, 0, 0, 0), (8, 0, 0, 0, 0), (8, 3, 0, 0, 0),
                (8, 2, 1, 0, 0), (8, 2, 0, 1, 0), (8, 2, 0, 0, 1)):
            ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, depth, color, compression, filtering, interlace))
            with self.subTest(ihdr=ihdr), self.assertRaises(ValueError):
                report.check_png_bytes(png()[:8] + ihdr + png()[33:], (2, 2))

    def test_complete_chunk_order_and_no_trailing_bytes_are_required(self):
        raw = png()
        header = raw[:33]
        payload = zlib.compress(b"\0" * 14)
        malformed = (
            raw[:8] + chunk(b"tEXt", b"first") + raw[8:],
            header + raw[8:33] + raw[33:],
            header + chunk(b"IEND"),
            header + chunk(b"IDAT", payload),
            raw + b"extra",
            header + chunk(b"IDAT", payload[:2]) + chunk(b"tEXt", b"split") +
            chunk(b"IDAT", payload[2:]) + chunk(b"IEND"),
            header + chunk(b"ABCD") + raw[33:],
            header + chunk(b"IDAT", payload) + chunk(b"PLTE", b"\0\0\0") + chunk(b"IEND"),
        )
        for index, candidate in enumerate(malformed):
            with self.subTest(index=index), self.assertRaises(ValueError):
                report.check_png_bytes(candidate, (2, 2))
        # Consecutive IDAT chunks are valid, including a harmless empty chunk.
        report.check_png_bytes(header + chunk(b"IDAT", payload[:2]) + chunk(b"IDAT") +
                               chunk(b"IDAT", payload[2:]) + chunk(b"IEND"), (2, 2))

    def test_scanlines_and_zlib_completion_are_bounded_and_exact(self):
        for scanlines in (b"\0" * 13, b"\0" * 15, b"\0" * 1_000_000, b"\x05" + b"\0" * 13):
            with self.subTest(length=len(scanlines)), self.assertRaises(ValueError):
                report.check_png_bytes(png(scanlines=scanlines), (2, 2))
        header = png()[:33]
        compressed = zlib.compress(b"\0" * 14)
        for data in (compressed[:-1], compressed + b"trailing", compressed + compressed):
            with self.subTest(data=data), self.assertRaises(ValueError):
                report.check_png_bytes(header + chunk(b"IDAT", data) + chunk(b"IEND"), (2, 2))
        # Every standard PNG filter number is permitted; reconstruction is not needed.
        for filter_type in range(5):
            report.check_png_bytes(png(scanlines=bytes([filter_type]) + b"\0" * 6 + b"\0" * 7), (2, 2))

    def test_encoded_png_has_a_hard_16_mib_bound(self):
        with self.assertRaises(ValueError):
            report.check_png_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * report.PNG_MAX_BYTES, (2, 2))

    def test_load_run_requires_a_complete_production_resolution_screenshot(self):
        with tempfile.TemporaryDirectory(prefix="aqualumen-png-test-") as temporary:
            directory = Path(temporary)
            run = {"run_id": "png-regression", "expected_resolution": [2560, 1440],
                   "world_generator": "minecraft:noise/overworld", "shader_active": True,
                   "shader_fallback": False, "pack_sha256": "test", "expected_pack_sha256": "test",
                   "world_id": "test-world", "scenarios": ["ocean-day"], "sample_seconds": 5}
            row = dict(report.metrics([1.0] * 10), resolution=[2560, 1440],
                       framebuffer_resolution=[2560, 1440], pack_sha256="test", world_id="test-world",
                       shader_active=True, shader_fallback=False, sample_seconds_actual=5,
                       player_dimension="minecraft:overworld", camera_lock=True,
                       camera_follows_local_player=True, actual_camera_rotation=[0, 0],
                       expected_camera_rotation=[0, 0], workload="warmed-view")
            (directory / "run.json").write_text(json.dumps(run))
            (directory / "complete.json").write_text(json.dumps({"run_id": run["run_id"], "status": "complete"}))
            (directory / "ocean-day.json").write_text(json.dumps(row))
            (directory / "ocean-day.csv").write_text("ms\n" + "1.0\n" * 10)
            with self.assertRaisesRegex(ValueError, "Invalid screenshot ocean-day.png"):
                report.load_run(directory)
            valid = png(2560, 1440)
            (directory / "ocean-day.png").write_bytes(valid)
            loaded_run, loaded_rows = report.load_run(directory)
            self.assertEqual(loaded_run["run_id"], run["run_id"])
            self.assertEqual(len(loaded_rows), 1)
            (directory / "ocean-day.png").write_bytes(valid[:-1])
            with self.assertRaisesRegex(ValueError, "Invalid screenshot ocean-day.png"):
                report.load_run(directory)


if __name__ == "__main__":
    unittest.main()
