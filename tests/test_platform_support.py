import unittest
from unittest.mock import patch

from typozap import platform


class PlatformSupportTests(unittest.TestCase):
    def test_macos_uses_command(self):
        self.assertEqual(platform.copy_shortcut("darwin"), ("command", "c"))
        self.assertEqual(platform.paste_shortcut("darwin"), ("command", "v"))
        self.assertEqual(platform.hotkey_spec("darwin"), "<ctrl>+<alt>+c")
        self.assertEqual(platform.hotkey_label("darwin"), "⌃⌥C")
        self.assertEqual(platform.default_hotkey_sequence("darwin"), "Ctrl+Alt+C")

    def test_windows_uses_control(self):
        self.assertEqual(platform.copy_shortcut("windows"), ("ctrl", "c"))
        self.assertEqual(platform.paste_shortcut("windows"), ("ctrl", "v"))
        self.assertEqual(platform.hotkey_spec("windows"), "<ctrl>+<shift>+<f8>")
        self.assertEqual(platform.hotkey_label("windows"), "Ctrl+Shift+F8")

    def test_user_shortcut_is_converted_for_pynput(self):
        self.assertEqual(
            platform.hotkey_spec_from_label("Ctrl+Alt+F9"),
            "<ctrl>+<alt>+<f9>",
        )

    def test_user_shortcut_requires_modifier(self):
        with self.assertRaises(ValueError):
            platform.hotkey_spec_from_label("F9")

    def test_reserved_ctrl_space_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Teams"):
            platform.hotkey_spec_from_label("Ctrl+Space")

    def test_hotkey_matcher_triggers_once_until_release(self):
        calls = []
        matcher = platform.HotkeyMatcher(["ctrl", "alt", "f9"], lambda: calls.append(True))
        matcher.press("ctrl")
        matcher.press("alt")
        matcher.press("f9")
        matcher.press("f9")
        self.assertEqual(calls, [])
        matcher.release("f9")
        matcher.release("alt")
        self.assertEqual(calls, [])
        matcher.release("ctrl")
        self.assertEqual(calls, [True])
        matcher.press("ctrl")
        matcher.press("alt")
        matcher.press("f9")
        matcher.release("ctrl")
        matcher.release("alt")
        matcher.release("f9")
        self.assertEqual(calls, [True, True])

    @patch("typozap.platform.platform.system", return_value="Darwin")
    def test_runtime_detection_is_normalized(self, _):
        self.assertEqual(platform.system_name(), "darwin")


if __name__ == "__main__":
    unittest.main()
