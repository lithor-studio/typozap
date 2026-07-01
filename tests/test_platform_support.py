import unittest
from unittest.mock import patch

import platform_support


class PlatformSupportTests(unittest.TestCase):
    def test_macos_uses_command(self):
        self.assertEqual(platform_support.copy_shortcut("darwin"), ("command", "c"))
        self.assertEqual(platform_support.paste_shortcut("darwin"), ("command", "v"))
        self.assertEqual(platform_support.hotkey_spec("darwin"), "<ctrl>+<alt>+c")
        self.assertEqual(platform_support.hotkey_label("darwin"), "⌃⌥C")

    def test_windows_uses_control(self):
        self.assertEqual(platform_support.copy_shortcut("windows"), ("ctrl", "c"))
        self.assertEqual(platform_support.paste_shortcut("windows"), ("ctrl", "v"))
        self.assertEqual(platform_support.hotkey_spec("windows"), "<ctrl>+<shift>+c")

    @patch("platform_support.platform.system", return_value="Darwin")
    def test_runtime_detection_is_normalized(self, _):
        self.assertEqual(platform_support.system_name(), "darwin")


if __name__ == "__main__":
    unittest.main()
