import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import QApplication

from typozap.selection_effect import AuroraOverlay, _windows_selection_rectangles


class SelectionEffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_windows_selection_rectangles_are_filtered(self):
        valid = SimpleNamespace(left=10, top=20, right=210, bottom=44)
        empty = SimpleNamespace(left=10, top=20, right=10, bottom=44)
        text_range = SimpleNamespace(GetBoundingRectangles=lambda: [valid, empty])
        pattern = SimpleNamespace(GetSelection=lambda: [text_range])
        control = SimpleNamespace(GetPattern=lambda pattern_id: pattern)
        automation = SimpleNamespace(
            GetFocusedControl=lambda: control,
            PatternId=SimpleNamespace(TextPattern=10014),
        )
        with patch.dict(sys.modules, {"uiautomation": automation}):
            self.assertEqual(_windows_selection_rectangles(), [QRect(10, 20, 200, 24)])

    def test_overlay_animates_without_taking_input(self):
        overlay = AuroraOverlay()
        overlay.start([QRect(100, 100, 240, 26)])
        self.assertTrue(overlay.isVisible())
        self.assertTrue(overlay.timer.isActive())
        self.assertEqual(len(overlay.local_rectangles), 1)
        overlay.advance()
        self.assertGreater(overlay.phase, 0)
        overlay.stop()
        self.assertFalse(overlay.timer.isActive())
        self.assertFalse(overlay.isVisible())


if __name__ == "__main__":
    unittest.main()
