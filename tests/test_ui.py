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

    def test_idle_timer_uses_configured_minutes(self):
        fake = SimpleNamespace(
            settings=SimpleNamespace(value=Mock(return_value=5)),
            idle_timer=Mock(),
            corrector=Mock(),
        )
        TypoZapApp.schedule_engine_sleep(fake)
        fake.idle_timer.stop.assert_called_once()
        fake.idle_timer.start.assert_called_once_with(5 * 60 * 1000)

    def test_engine_sleep_releases_corrector(self):
        fake = SimpleNamespace(
            busy=False,
            explanation_worker=None,
            corrector=Mock(),
            engine=Mock(),
            explain_action=Mock(),
            logger=Mock(),
        )
        TypoZapApp.put_engine_to_sleep(fake)
        fake.engine.stop.assert_called_once()
        self.assertIsNone(fake.corrector)
        fake.explain_action.setEnabled.assert_called_once_with(False)


if __name__ == "__main__":
    unittest.main()
