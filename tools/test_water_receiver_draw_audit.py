"""Public external-evidence reader tests; no own-module mocks."""
import unittest
import json
import shutil
import tempfile
from pathlib import Path
from water_receiver_draw_audit import OUT, audit

class ActualDrawTest(unittest.TestCase):
    def test_actual_iris_matrix_uv_and_ao_decode_match_gpu(self):
        actual = audit()
        self.assertEqual(actual['actualGPUOutputFloatsMatched'], 448)
        self.assertTrue(actual['actualDrawInputsValidated'])
        self.assertFalse(actual['originalTerrainFragmentInvocation'])
        self.assertFalse(actual['shadedWorldSourceUploaded'])

    def rejected_copy(self, change):
        with tempfile.TemporaryDirectory(prefix='aqualumen-external-draw-reader-') as directory:
            packet = Path(directory) / 'packet'
            shutil.copytree(OUT, packet)
            path = packet / 'actual-draw-readback.json'
            data = json.loads(path.read_text())
            change(data)
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError): audit(packet)

    def test_generic_sodium_double_light_normalization_rejected(self):
        self.rejected_copy(lambda d: d['lightmapMatrixColumnMajor'].__setitem__(0,
                            d['lightmapMatrixColumnMajor'][0]/256))

    def test_guessed_full_ao_cannot_replace_actual_gpu_output(self):
        self.rejected_copy(lambda d: d['gpuDecode']['uvLightmapColor'][0].__setitem__(7, 1.0))

    def test_wrong_bound_vertex_stride_rejected(self):
        self.rejected_copy(lambda d: d['attributes']['a_TexCoord'].__setitem__('stride', 20))

    def test_changed_actual_shader_source_rejected(self):
        self.rejected_copy(lambda d: d.__setitem__('linkedVertexSource', d['linkedVertexSource']+'\n// altered'))

    def test_unrestored_original_program_rejected(self):
        self.rejected_copy(lambda d: d['gpuDecode']['after'].__setitem__('program', 0))

    def test_owned_vs_probe_cannot_claim_original_fragment_invocation(self):
        self.rejected_copy(lambda d: d['gpuDecode'].__setitem__('originalTerrainFragmentInvocation', True))

if __name__ == '__main__': unittest.main()
