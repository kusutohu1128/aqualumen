"""Public saved-capture audit behavior; copied external files, no internal mocks."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from water_receiver_mesher_audit import OUT, audit


class ActualMesherAuditTest(unittest.TestCase):
    def test_actual_requested_mesh_has_independently_matching_owned_encoding(self):
        actual = audit()
        self.assertEqual(actual["actualOwnedFaces"], 14)
        self.assertEqual(actual["actualVertices"], 56)
        self.assertTrue(actual["actualMinecraftMesherEncoderValidated"])
        self.assertFalse(actual["shadedSourceRadiance"])

    def rejected_copy(self, change):
        with tempfile.TemporaryDirectory(prefix="aqualumen-external-mesher-reader-") as directory:
            copy = Path(directory) / "packet"
            shutil.copytree(OUT, copy)
            file = copy / "actual-mesher-readback.json"
            data = json.loads(file.read_text())
            change(data)
            file.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                audit(copy)

    def test_written_position_bit_cannot_pass_as_the_owned_vertex(self):
        self.rejected_copy(lambda d: d["actualMesherEncodes"][0]["encodedFirst20ByteWords"][0].__setitem__(0,
            d["actualMesherEncodes"][0]["encodedFirst20ByteWords"][0][0] ^ 1))

    def test_ao_output_cannot_be_substituted_with_guessed_full_alpha(self):
        self.rejected_copy(lambda d: d["actualMesherEncodes"][0]["encodedFirst20ByteWords"][0].__setitem__(2, 0xffffffff))

    def test_duplicate_owner_does_not_establish_complete_requested_faces(self):
        self.rejected_copy(lambda d: d["actualMesherEncodes"].__setitem__(-1, d["actualMesherEncodes"][0]))

    def test_render_thread_label_does_not_establish_actual_worker_capture(self):
        self.rejected_copy(lambda d: d["actualMesherEncodes"][0].__setitem__("threadName", "Render thread"))


if __name__ == "__main__":
    unittest.main()
