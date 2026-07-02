import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from typozap.model_installer import download_model, sha256_file


class ModelInstallerTests(unittest.TestCase):
    def test_sha256_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "model.gguf"
            path.write_bytes(b"TypoZap")
            self.assertEqual(
                sha256_file(path),
                "55e1b516be72b87f571aa6500c7d03aba468fa9ec778b530ab0f224c1632535b",
            )

    def test_existing_valid_model_is_reused_without_network(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "model.gguf"
            path.write_bytes(b"TypoZap")
            with (
                patch("typozap.model_installer.MODEL_SIZE", 7),
                patch("typozap.model_installer.MODEL_SHA256", sha256_file(path)),
                patch("typozap.model_installer.requests.get") as get,
            ):
                self.assertEqual(download_model(path), path)
                get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
