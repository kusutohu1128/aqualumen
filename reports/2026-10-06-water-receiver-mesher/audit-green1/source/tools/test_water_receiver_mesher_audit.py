"""Public saved-capture audit behavior; copied external files, no internal mocks."""
import unittest
from water_receiver_mesher_audit import audit


class ActualMesherAuditTest(unittest.TestCase):
    def test_actual_requested_mesh_has_independently_matching_owned_encoding(self):
        actual = audit()
        self.assertEqual(actual["actualOwnedFaces"], 14)
        self.assertEqual(actual["actualVertices"], 56)
        self.assertTrue(actual["actualMinecraftMesherEncoderValidated"])
        self.assertFalse(actual["shadedSourceRadiance"])


if __name__ == "__main__":
    unittest.main()
