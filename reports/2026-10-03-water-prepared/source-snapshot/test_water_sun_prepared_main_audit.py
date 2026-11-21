"""Public CPU saved-map tests; no GL and no synthetic native acceptance."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import struct
import hashlib

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT/"tools/water_sun_prepared_main_audit.py"
sys.path.insert(0, str(ROOT / 'tools'))
import water_sun_prepared_main_audit as main_audit


def saved_nodes(root, size=1):
    """One-pixel CPU fixture, explicitly not a native packet."""
    records = []
    for node in range(48):
        files = []
        for mode in ('old', 'prepared'):
            for kind, slot, values in [('target', 5, (0., 1., 0., node+1.)),
                                       ('view', 6, (0., -1., 0., 1.333)),
                                       ('class', 7, (2., 1., float(node), 1.))]:
                raw = struct.pack('<4f', *values)*(size*size)
                name = f'node{node}-{mode}-{kind}.rgba32f'
                (root / name).write_bytes(raw)
                files.append(dict(mode=mode, kind=kind, slot=slot, file=name,
                                  bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        records.append(dict(node=node, generated_pixels=size*size, class_called_pixels=size*size,
                            saved_maps=dict(node=node, duplicate_maps_omitted=False, maps=files)))
    return records


class MainAuditTests(unittest.TestCase):
    def test_public_all48_reader_replays_both_saved_modes(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-main-synthetic-') as tmp:
            root = Path(tmp)
            result = main_audit.verify_nodes(root, saved_nodes(root), [48*64+48*262144],
                                            size=1, selected_pixels=[(0, 0)])
            self.assertEqual(result['fullNodePixelPairsPerMode'], 48)
            self.assertEqual(result['selectedArithmeticRecords'], 96)
            self.assertEqual(result['fullLedgerPixels'], 1)
            self.assertFalse(result['nativeGLExecuted'])

    def test_both_modes_corrupted_class_fails_independent_selected_arithmetic(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-main-synthetic-') as tmp:
            root = Path(tmp); records = saved_nodes(root)
            for entry in records[17]['saved_maps']['maps']:
                if entry['kind'] == 'class':
                    raw = struct.pack('<4f',1.,1.,17.,1.)
                    (root/entry['file']).write_bytes(raw)
                    entry['sha256'] = hashlib.sha256(raw).hexdigest()
            with self.assertRaisesRegex(ValueError,'arithmetic class'):
                main_audit.verify_nodes(root,records,[1+47*64+48*262144],size=1,selected_pixels=[(0,0)])

    def test_signed_zero_difference_in_prepared_map_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-main-synthetic-') as tmp:
            root = Path(tmp); records = saved_nodes(root)
            entry = records[31]['saved_maps']['maps'][3]
            raw = struct.pack('<4f',-0.,1.,0.,32.)
            (root/entry['file']).write_bytes(raw); entry['sha256'] = hashlib.sha256(raw).hexdigest()
            with self.assertRaisesRegex(ValueError,'raw bits differ'):
                main_audit.verify_nodes(root,records,[48*64+48*262144],size=1,selected_pixels=[(0,0)])

    def test_full_ledger_is_verified_outside_selected_pixel_subset(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-main-synthetic-') as tmp:
            root = Path(tmp); records = saved_nodes(root, size=2)
            with self.assertRaisesRegex(ValueError,'actual class/count ledger'):
                main_audit.verify_nodes(root,records,[48*64+48*262144]*3+[47*64+47*262144],
                                        size=2,selected_pixels=[(0,0)])

    def test_missing_prepared_map_or_truncated_bytes_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='aqualumen-main-synthetic-') as tmp:
            root = Path(tmp); records = saved_nodes(root)
            records[0]['saved_maps']['maps'].pop()
            with self.assertRaisesRegex(ValueError,'six node maps'):
                main_audit.verify_nodes(root,records,[48*64+48*262144],size=1,selected_pixels=[(0,0)])
            records = saved_nodes(root)
            (root/records[2]['saved_maps']['maps'][0]['file']).write_bytes(b'\0'*12)
            with self.assertRaisesRegex(ValueError,'hash/size'):
                main_audit.verify_nodes(root,records,[48*64+48*262144],size=1,selected_pixels=[(0,0)])

    def test_source_erasure_requires_one_exact_tag_pair(self):
        self.assertEqual(main_audit.erase('aBEGINbodyENDz','BEGIN','END'),'az')
        for value in ('aBEGINxBEGINyENDz','aENDxBEGINz','aBEGINz'):
            with self.assertRaises(ValueError): main_audit.erase(value,'BEGIN','END')

    def test_missing_completed_main_packet_is_inconclusive(self):
        with tempfile.TemporaryDirectory(prefix="aqualumen-main-audit-") as tmp:
            run = subprocess.run([sys.executable, "-B", str(TOOL), str(Path(tmp)/"absent")],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            result = json.loads(run.stdout)
            self.assertEqual(result["status"], "INCONCLUSIVE")
            self.assertFalse(result["accepted"])
            self.assertFalse(result["auditorGLExecuted"])


if __name__ == "__main__":
    unittest.main()
