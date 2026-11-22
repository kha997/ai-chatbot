import unittest

from availability import combine_windows


class AvailabilityTests(unittest.TestCase):
    def test_touching_windows_stay_distinct(self):
        self.assertEqual(combine_windows([(5, 8), (1, 5), (8, 9)]), [(1, 5), (5, 8), (8, 9)])

    def test_overlapping_and_nested_windows_merge(self):
        self.assertEqual(combine_windows([(3, 8), (10, 12), (4, 5), (1, 4)]), [(1, 8), (10, 12)])

    def test_empty_windows(self):
        self.assertEqual(combine_windows([]), [])
