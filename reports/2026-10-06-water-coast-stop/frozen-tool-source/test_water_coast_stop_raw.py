import json
import unittest
from water_coast_stop_raw import PREVIOUS,require_known_water


class CoastStopRawTest(unittest.TestCase):
    def test_available_initialization_zeros_are_not_water(self):
        value=json.loads((PREVIOUS/'early-frame1-zero-raw.json').read_text())
        samples=next(s for s in value['samplers'] if s['name']=='colortex9')['samples']
        with self.assertRaisesRegex(AssertionError,'water producer mask'):require_known_water(samples)

    def test_actual_prior_positive_known_water_is_admissible(self):
        value=json.loads((PREVIOUS/'selected-raw-v2.json').read_text())
        samples=next(s for s in value['samplers'] if s['name']=='colortex9')['samples']
        require_known_water(samples)


if __name__=='__main__':unittest.main()
