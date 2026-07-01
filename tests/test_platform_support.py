import unittest
from unittest.mock import patch

from typozap import platform


class PlatformSupportTests(unittest.TestCase):
    def test_macos_uses_command(self):
        self.assertEqual(platform.copy_shortcut("darwin"), ("command", "c"))
        self.assertEqual(platform.paste_shortcut("darwin"), ("command", "v"))
        self.assertEqual(platform.hotkey_spec("darwin"), "<ctrl>+<alt>+c")
        self.assertEqual(platform.hotkey_label("darwin"), "⌃⌥C")

    def test_windows_uses_control(self):
        self.assertEqual(platform.copy_shortcut("windows"), ("ctrl", "c"))
        self.assertEqual(platform.paste_shortcut("windows"), ("ctrl", "v"))
        self.assertEqual(platform.hotkey_spec("windows"), "<ctrl>+<shift>+c")

    @patch("typozap.platform.platform.system", return_value="Darwin")
    def test_runtime_detection_is_normalized(self, _):
        self.assertEqual(platform.system_name(), "darwin")


if __name__ == "__main__":
    unittest.main()
