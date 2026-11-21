import json
from pathlib import Path
import shutil
import tempfile
import unittest
from water_receiver_triangle_audit import OUT, audit

class TriangleAuditTest(unittest.TestCase):
    def test_original_vs_pinned_diagonal_interpolation_qualifies_both_projections(self):
        result=audit()
        self.assertEqual(result['qualifiedGPUInterpolantFloatCount'],928)
        self.assertGreater(result['maximumOppositeDiagonalDifference'],.01)
        self.assertFalse(result['originalTerrainFragmentInvocation'])
    def copied_rejection(self,change):
        with tempfile.TemporaryDirectory(prefix='aqualumen-external-triangle-reader-') as folder:
            packet=Path(folder)/'packet';shutil.copytree(OUT,packet);change(packet)
            with self.assertRaises(ValueError):audit(packet)
    def test_guessed_full_ao_rejected(self):
        def change(p):
            import struct
            path=p/'native-v1/native-outputs.f32';data=bytearray(path.read_bytes());struct.pack_into('<f',data,7*4,1)
            path.write_bytes(data)
        self.copied_rejection(change)
    def test_opposite_diagonal_cannot_be_labeled_original(self):
        def change(p):
            path=p/'native-v1/native-outputs.f32';data=path.read_bytes();half=len(data)//2
            path.write_bytes(data[half:]+data[:half])
        self.copied_rejection(change)
    def test_detached_vertex_owner_rejected(self):
        def change(p):
            path=p/'input-contract.json';data=json.loads(path.read_text());data['faces'][0]['cell'][0]+=1
            path.write_text(json.dumps(data))
        self.copied_rejection(change)
    def test_changed_native_source_rejected(self):
        def change(p):
            path=p/'native-v1/source/tools/receiver-triangle-gpu.cpp';path.write_text(path.read_text()+'\n// changed')
        self.copied_rejection(change)

if __name__=='__main__':unittest.main()
