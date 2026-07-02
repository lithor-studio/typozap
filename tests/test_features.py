import unittest
import sys
import tempfile
from pathlib import Path

from typozap.features import SecureHistory, style_for_window


class FeatureTests(unittest.TestCase):
    def test_profile_matches_window_case_insensitively(self):
        self.assertEqual(
            style_for_window("Discussion | Microsoft Teams", {"teams": "informel"}, "standard"),
            "informel",
        )

    def test_profile_falls_back_to_default(self):
        self.assertEqual(style_for_window("Bloc-notes", {"teams": "informel"}, "formel"), "formel")

    @unittest.skipUnless(sys.platform == "win32", "DPAPI Windows uniquement")
    def test_secure_history_is_encrypted_and_readable(self):
        with tempfile.TemporaryDirectory() as folder:
            history = SecureHistory()
            history.path = Path(folder) / "history.dat"
            history.add("phrase fausse", "phrase correcte", "standard")
            self.assertNotIn(b"phrase fausse", history.path.read_bytes())
            self.assertEqual(history.load()[0]["corrected"], "phrase correcte")


if __name__ == "__main__":
    unittest.main()
