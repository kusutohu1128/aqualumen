import unittest

from profile_data import account, collect_window, overhead, percentile, calibration, read_rows
from io import StringIO


class ProfileTests(unittest.TestCase):
    def test_nested_repeated_and_residual(self):
        frame = account([("frame", 0, 100), ("shadow", 5, 75), ("solid", 8, 12),
                         ("solid", 20, 30), ("final", 80, 95)])
        self.assertEqual(frame["exclusive"], {"shadow": 56, "solid": 14, "final": 15})
        self.assertEqual(frame["residual"], 15)
        self.assertEqual(frame["calls"]["solid"], 2)
        self.assertEqual(frame["inclusive"]["shadow"], 70)

    def test_invalid_frames(self):
        for rows in [[("frame", 0, 10), ("a", 1, 5), ("b", 4, 7)],
                     [("frame", 0, 10), ("a", 4, 11)], [("a", 1, 3)],
                     [("frame", 5, 3)], [("frame", 1, 5), ("frame", 1, 2)]]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                account(rows)

    def test_delayed_and_missing(self):
        csv = "epoch,frame,range,start_ns,end_ns\n1,8,frame,0,5\n1,7,frame,7,9\n2,6,frame,10,11\n"
        frames = read_rows(StringIO(csv))
        self.assertEqual(len(collect_window(frames, [7, 8])), 2)
        for ids in ([6, 7], [8, 9], [8, 7], [7, 7]):
            with self.assertRaises(ValueError):
                collect_window(frames, ids)

    def test_explicit_parent_and_zero_calls(self):
        rows = [("frame", 0, 10, -1, 0), ("flush", 0, 5, 0, 0), ("quad", 0, 5, 1, 1)]
        result = account(rows)
        self.assertEqual(result["draws"], {"frame": 0, "flush": 0, "quad": 1})
        with self.assertRaises(ValueError):
            account(rows[:2] + [("quad", 2, 4, 0, 1)])

    def test_ambiguous_cpu_batch(self):
        from summarize import window_ids
        lines=["[Server] AQLAVA_READY_test_END", "test.pngとして保存しました"]
        for i in range(4):
            lines.extend((f"AQ_RENDER_FRAME_END {i} {2*i+2}",f"AQ_RENDER_INTERVALS_US {i} 100 200"))
        lines.append("[Server] AQLAVA_STILL_test_END")
        self.assertEqual(window_ids("\n".join(lines),"test",[100,200]),[7,8])
        lines.insert(-1, "AQ_RENDER_FRAME_END 3 10")
        with self.assertRaises(ValueError):
            window_ids("\n".join(lines),"test",[100,200])

    def test_campaign_blocks_unvalidated_pack(self):
        import tempfile
        from pathlib import Path
        from run import check_sequence
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            check_sequence("gp-cal-4x-c",root)
            with self.assertRaises(ValueError):
                check_sequence("gp-cal-4x-c-retry1",root)
            with self.assertRaises(ValueError):
                check_sequence("gp-p8-a",root)
            failed=root/"gp-cal-4x-c"
            failed.mkdir()
            (failed/"summary.json").write_text('{"validated":false}')
            with self.assertRaises(ValueError):
                check_sequence("gp-overhead-off-a",root)
            d=root/"gp-p7-a"
            d.mkdir()
            (d/"summary.json").write_text('{"label":"gp-p7-a"}')
            with self.assertRaises(ValueError):
                check_sequence("gp-p8-a",root)

    def test_empty_slot_receipt(self):
        stream=StringIO("epoch,frame,range,start_ns,end_ns,parent,draws,empty_slots\n"
                        "2,9,frame,10,100,-1,0,\n2,9,stage/shadowcomp,11,90,0,0,8-99\n")
        rows=read_rows(stream)[2,9]
        self.assertEqual(rows[-1][-1],"8-99")
        self.assertEqual(account(rows)["inclusive"]["stage/shadowcomp"],79)

    def test_paired_range_differences(self):
        from comparisons import compared
        def values(m):
            return dict(medianMs=m,p95Ms=2*m)
        result=compared([values(8),values(11)],[values(10),values(10)])
        self.assertEqual(result["medianMs"],dict(a=2,b=-1,mean=.5))
        self.assertEqual(result["p95Ms"]["mean"],1)
        self.assertIsNone(compared([None,None],[values(1),values(1)])["medianMs"])

    def test_birch_stage_order_and_cleanup(self):
        import importlib.util
        import birch_scene as b
        spec=importlib.util.spec_from_file_location("original_rooms",b.R.parent/"2026-11-21-animal-light/scene.py")
        rooms=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rooms)
        scene=b.BirchRooms(rooms)
        scene.configure(680)
        files=scene.datapack(b.STAGES)
        prefix="data/animal/function/"
        self.assertIn("animal:s2 680t",files[prefix+"s1.mcfunction"])
        self.assertIn("if block 207 64 359 minecraft:air run setblock",files[prefix+"s3.mcfunction"])
        receipt=files[prefix+"e3.mcfunction"]
        self.assertLess(receipt.index("setblock"),receipt.index("AQ_BIRCH_RESTORED"))
        self.assertLess(receipt.index("AQ_BIRCH_RESTORED"),receipt.index("AQLAVA_STILL"))
        self.assertEqual(receipt.count("unless loaded"),16)
        self.assertEqual(receipt.count("unless block"),55)

    def test_rank_and_limits(self):
        self.assertEqual(percentile([5, 2, 9, 1], .5), 2)
        self.assertEqual(percentile([5, 2, 9, 1], .95), 9)
        self.assertTrue(overhead([100]*100, [105]*100)["pass"])
        self.assertFalse(overhead([100]*100, [106]*100)["pass"])
        self.assertTrue(overhead([100]*100,[100]*94+[108]*6)["pass"])
        self.assertFalse(overhead([100]*100, [100]*94+[109]*6)["pass"])
        self.assertTrue(calibration(4., 1., [.2, 3.], [.29, 3.29], 1)["pass"])
        for cost, check, roi in [(2.9, .2, 0), (5.1, .2, 0), (4., .31, 0), (4., .2, 2)]:
            self.assertFalse(calibration(cost, 1., [check], [.2], roi)["pass"])
