import unittest
from pathlib import Path
from water_normal_pause_event import verify_pause_event

class NormalPauseEventTest(unittest.TestCase):
    def test_historical_pause_cannot_qualify_later_gameplay_image(self):
        root=Path(__file__).resolve().parents[1]
        log=(root/"reports/2026-10-06-water-receiver-faces/normal-final-runtime.log").read_text()
        with self.assertRaises(ValueError):
            verify_pause_event(log,"2026-10-06_15.33.12.png","2026-10-06_15.34.03.png")

    def test_ordered_new_pause_is_necessary_not_image_proof(self):
        log=("スクリーンショットをruntime.pngとして保存しました\n"
             "Saving and pausing game...\n"
             "スクリーンショットをpause.pngとして保存しました\n")
        result=verify_pause_event(log,"runtime.png","pause.png")
        self.assertEqual(result["freshPauseLogLine"],2)
        self.assertTrue(result["imageMenuMustBeInspectedSeparately"])

if __name__=="__main__":unittest.main()
