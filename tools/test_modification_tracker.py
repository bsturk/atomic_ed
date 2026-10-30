"""Overlapping patches retain untouched bytes and the original file baseline."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.modification_tracker import ModificationTracker, ModificationType


class ModificationTrackerTests(unittest.TestCase):
    def test_contained_patch_preserves_surrounding_changes_and_baseline(self):
        tracker = ModificationTracker()
        tracker.add_modification(100, b'abcd', b'WXYZ', ModificationType.UNIT_STATS)
        tracker.add_modification(102, b'Y', b'!', ModificationType.UNIT_STATS)
        self.assertEqual(tracker.get_patches(), [(100, b'WX!Z')])
        self.assertEqual(tracker.revert_all(), [(100, b'abcd')])

    def test_partial_overlap_extends_in_either_direction(self):
        for offset, original, changed, expected_original, expected in (
                (98, b'12WX', b'1234', b'12abcd', b'1234YZ'),
                (102, b'YZ56', b'3456', b'abcd56', b'WX3456')):
            with self.subTest(offset=offset):
                tracker = ModificationTracker()
                tracker.add_modification(100, b'abcd', b'WXYZ', ModificationType.UNIT_STATS)
                tracker.add_modification(offset, original, changed, ModificationType.UNIT_STATS)
                start = min(100, offset)
                self.assertEqual(tracker.get_patches(), [(start, expected)])
                self.assertEqual(tracker.revert_all(), [(start, expected_original)])

    def test_bridge_preserves_both_baselines_and_can_revert_to_original(self):
        tracker = ModificationTracker()
        tracker.add_modification(100, b'ab', b'WX', ModificationType.UNIT_STATS)
        tracker.add_modification(104, b'ef', b'YZ', ModificationType.UNIT_STATS)
        tracker.add_modification(101, b'XcdY', b'1234', ModificationType.UNIT_STATS)
        self.assertEqual(tracker.get_patches(), [(100, b'W1234Z')])
        self.assertEqual(tracker.revert_all(), [(100, b'abcdef')])
        tracker.add_modification(100, b'W1234Z', b'abcdef', ModificationType.UNIT_STATS)
        self.assertEqual(tracker.get_patches(), [])
        self.assertEqual(tracker.revert_all(), [(100, b'abcdef')])


if __name__ == '__main__':
    unittest.main()
