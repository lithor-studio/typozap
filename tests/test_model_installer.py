import tempfile
import unittest
from pathlib import Path

from typozap.model_installer import sha256_file


class ModelInstallerTests(unittest.TestCase):
    def test_sha256_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "model.gguf"
            path.write_bytes(b"TypoZap")
            self.assertEqual(
                sha256_file(path),
                "55e1b516be72b87f571aa6500c7d03aba468fa9ec778b530ab0f224c1632535b",
            )


if __name__ == "__main__":
    unittest.main()
