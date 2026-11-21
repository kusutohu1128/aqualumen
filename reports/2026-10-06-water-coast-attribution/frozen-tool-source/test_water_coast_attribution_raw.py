"""Actual early-frame readback is a nonvacuous mask-negative, not a success."""
import json
import unittest
from water_coast_attribution_pack import OUT
from water_coast_attribution_raw import validate


class RawQualificationTest(unittest.TestCase):
    def test_available_zero_frame_is_not_water_attribution(self):
        value=json.loads((OUT/'early-frame1-zero-raw.json').read_text())
        source=next(s for s in value['samplers'] if s['name']=='colortex9')
        points=[(s['x'],s['y']) for s in source['samples']]
        self.assertTrue(value['available'])
        with self.assertRaisesRegex(AssertionError,'actual water producer mask'):
            validate(value,points)


if __name__=='__main__':
    unittest.main()
