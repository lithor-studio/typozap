"""Tests réels du modèle embarqué, activés avec TYPOZAP_TEST_MODEL=1."""

import os
import unittest

from typozap.engine import EngineManager


@unittest.skipUnless(os.getenv("TYPOZAP_TEST_MODEL") == "1", "test du modèle embarqué optionnel")
class FrenchModelAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = EngineManager()
        cls.corrector = cls.engine.start()
        if cls.corrector is None:
            raise unittest.SkipTest("runtime ou modèle Ministral absent")

    @classmethod
    def tearDownClass(cls):
        cls.engine.stop()

    def assertCorrection(self, source, expected):
        self.assertEqual(self.corrector.correct_text(source), expected)

    def test_core_french_corpus(self):
        cases = [
            ("Les enfant joue dans le jardin.", "Les enfants jouent dans le jardin."),
            ("Elle est arrivee tres tot.", "Elle est arrivée très tôt."),
            ("Sa va beaucoup mieux aujourd'hui.", "Ça va beaucoup mieux aujourd'hui."),
            ("Elles se sont parlé pendant une heure.", "Elles se sont parlé pendant une heure."),
            ("Peut tu m'envoyer le dossier ?", "Peux-tu m'envoyer le dossier ?"),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertCorrection(source, expected)


if __name__ == "__main__":
    unittest.main()
