import unittest
from water_residual_angular_peaks import components


class AngularPeaksTests(unittest.TestCase):
    def test_two_separated_bright_regions_report_their_actual_peaks(self):
        values = {(128, 128): 1., (129, 128): .3,
                  (140, 128): .6, (128, 129): .1}
        result = components(values)
        self.assertEqual([item['peak_pixel'] for item in result],
                         [[128, 128], [140, 128]])
        self.assertEqual([item['pixels'] for item in result], [2, 1])


if __name__ == '__main__':
    unittest.main()
