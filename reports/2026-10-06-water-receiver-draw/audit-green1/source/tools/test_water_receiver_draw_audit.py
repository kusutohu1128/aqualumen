"""Public external-evidence reader tests; no own-module mocks."""
import unittest
from water_receiver_draw_audit import audit

class ActualDrawTest(unittest.TestCase):
    def test_actual_iris_matrix_uv_and_ao_decode_match_gpu(self):
        actual = audit()
        self.assertEqual(actual['actualGPUOutputFloatsMatched'], 448)
        self.assertTrue(actual['actualDrawInputsValidated'])
        self.assertFalse(actual['originalTerrainFragmentInvocation'])
        self.assertFalse(actual['shadedWorldSourceUploaded'])

if __name__ == '__main__': unittest.main()
