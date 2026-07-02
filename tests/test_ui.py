import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from typozap.app import CorrectionDialog, TypoZapApp


class CorrectionDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_individual_change_can_be_refused(self):
        dialog = CorrectionDialog("Les enfant jouent.", "Les enfants jouent.")
        self.assertEqual(dialog.result_text(), "Les enfants jouent.")
        dialog.change_items[0][0].setCheckState(Qt.Unchecked)
        self.assertEqual(dialog.result_text(), "Les enfant jouent.")

    def test_hotkey_restart_is_bound_to_new_listener(self):
        first, second = Mock(), Mock()
        first.canonical.side_effect = lambda key: key
        second.canonical.side_effect = lambda key: key
        bridge = SimpleNamespace(activated=SimpleNamespace(emit=Mock()))
        fake = SimpleNamespace(
            hotkey_listener=first,
            hotkey="Ctrl+Shift+F8",
            hotkey_bridge=bridge,
            logger=Mock(),
            show_notification=Mock(),
        )
        fake.emit_hotkey = bridge.activated.emit
        fake_keyboard = SimpleNamespace(
            HotKey=SimpleNamespace(parse=Mock(return_value=["x"])),
            Listener=Mock(return_value=second),
        )
        fake_pynput = SimpleNamespace(keyboard=fake_keyboard)
        with patch.dict(sys.modules, {"pynput": fake_pynput, "pynput.keyboard": fake_keyboard}):
            self.assertTrue(TypoZapApp.setup_hotkey(fake))
            first.stop.assert_called_once()
            first.join.assert_called_once_with(1)
            fake_keyboard.Listener.call_args.kwargs["on_press"]("x")
            second.canonical.assert_called_with("x")
            fake.hotkey_bridge.activated.emit.assert_not_called()
            fake_keyboard.Listener.call_args.kwargs["on_release"]("x")
            fake.hotkey_bridge.activated.emit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
