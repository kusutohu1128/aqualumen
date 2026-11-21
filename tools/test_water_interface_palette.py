import unittest

from water_interface_palette import classify, classify_raw


class InterfacePaletteTest(unittest.TestCase):
    def test_raw_codes_are_distinct_and_displayed_colors_are_not_raw_evidence(self):
        for color, expected in (
                ((0, 128, 0), 'transmission'), ((0, 0, 128), 'tir'),
                ((255, 89, 0), 'transmission_wrong_side'),
                ((255, 0, 0), 'reflection_wrong_side'),
                ((255, 255, 0), 'admitted_downward_transmission'),
                ((0, 0, 0), 'unobserved'), ((10, 152, 10), 'unclassified')):
            with self.subTest(color=color):
                self.assertEqual(classify_raw(color), expected)

    def test_source_palette_and_observed_composited_colors(self):
        for color, expected in (
                ((0, 128, 0), 'transmission'), ((10, 152, 10), 'transmission'),
                ((0, 0, 128), 'tir'), ((20, 25, 147), 'tir'),
                ((255, 89, 0), 'transmission_wrong_side'),
                ((160, 140, 10), 'transmission_wrong_side'),
                ((255, 0, 0), 'reflection_wrong_side'),
                ((0, 0, 0), 'unclassified'), ((100, 100, 100), 'unclassified')):
            with self.subTest(color=color):
                self.assertEqual(classify(color), expected)


if __name__ == '__main__':
    unittest.main()
