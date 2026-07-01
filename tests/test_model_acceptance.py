"""Tests réels du modèle. Exécution : TYPOZAP_TEST_MODEL=1 python -m unittest tests.test_model_acceptance"""

import os
import unittest

from corrector import OllamaCorrector


@unittest.skipUnless(os.getenv("TYPOZAP_TEST_MODEL") == "1", "test Ollama optionnel")
class FrenchModelAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corrector = OllamaCorrector()
        if not cls.corrector.check_ollama():
            raise unittest.SkipTest("Ollama n'est pas démarré")

    def assertCorrection(self, source, expected):
        self.assertEqual(self.corrector.correct_text(source), expected)

    def test_plural_and_verb_agreement(self):
        self.assertCorrection("Les enfant joue dans le jardin.", "Les enfants jouent dans le jardin.")

    def test_accents_and_agreement(self):
        self.assertCorrection("Elle est arrivee tres tot.", "Elle est arrivée très tôt.")

    def test_common_homophones(self):
        self.assertCorrection("Ils ce sont rendu a la gare.", "Ils se sont rendus à la gare.")

    def test_correct_sentence_is_preserved(self):
        sentence = "Nous sommes arrivés à l'heure."
        self.assertCorrection(sentence, sentence)

    def test_extended_french_corpus(self):
        cases = [
            ("J'ai acheter du pain ce matin.", "J'ai acheté du pain ce matin."),
            ("Ces fleurs sont très belle.", "Ces fleurs sont très belles."),
            ("Nous avons manger ensemble.", "Nous avons mangé ensemble."),
            ("Il a prit le dernier train.", "Il a pris le dernier train."),
            ("Les chevals courent dans le champ.", "Les chevaux courent dans le champ."),
            ("Sa va beaucoup mieux aujourd'hui.", "Ça va beaucoup mieux aujourd'hui."),
            ("Je les ai vu hier soir.", "Je les ai vus hier soir."),
            ("Elles se sont parlé pendant une heure.", "Elles se sont parlé pendant une heure."),
            ("Il faut que tu viennes demain.", "Il faut que tu viennes demain."),
            ("Le rendez-vous est fixé à quatorze heures.", "Le rendez-vous est fixé à quatorze heures."),
            ("Peut tu m'envoyer le dossier ?", "Peux-tu m'envoyer le dossier ?"),
            ("Ils ont résolu le problème eux même.", "Ils ont résolu le problème eux-mêmes."),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertCorrection(source, expected)


if __name__ == "__main__":
    unittest.main()
