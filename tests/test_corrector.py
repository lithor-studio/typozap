import unittest
from unittest.mock import Mock, patch

from corrector import CorrectionError, OllamaCorrector


class OllamaCorrectorTests(unittest.TestCase):
    def setUp(self):
        self.corrector = OllamaCorrector(model="test-model")

    def test_empty_text_does_not_call_ollama(self):
        with patch("corrector.requests.post") as post:
            self.assertEqual(self.corrector.correct_text(""), "")
            post.assert_not_called()

    @patch("corrector.requests.post")
    def test_returns_trimmed_correction_and_deterministic_options(self, post):
        response = Mock()
        response.json.return_value = {"response": "  Les enfants jouent.  "}
        response.raise_for_status.return_value = None
        post.return_value = response

        result = self.corrector.correct_text("Les enfant joue.")

        self.assertEqual(result, "Les enfants jouent.")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["options"]["temperature"], 0)
        self.assertIn("Les enfant joue.", payload["prompt"])

    @patch("corrector.requests.post")
    def test_network_error_is_not_returned_as_corrected_text(self, post):
        from requests import ConnectionError

        post.side_effect = ConnectionError("service arrêté")
        with self.assertRaises(CorrectionError):
            self.corrector.correct_text("Une phrase.")

    @patch("corrector.requests.post")
    def test_empty_model_response_is_an_error(self, post):
        response = Mock()
        response.json.return_value = {"response": ""}
        response.raise_for_status.return_value = None
        post.return_value = response

        with self.assertRaises(CorrectionError):
            self.corrector.correct_text("Une phrase.")

    @patch("corrector.requests.post")
    def test_preserves_straight_apostrophe_style(self, post):
        response = Mock()
        response.json.return_value = {"response": "C’est l’heure."}
        response.raise_for_status.return_value = None
        post.return_value = response

        self.assertEqual(self.corrector.correct_text("C'est l'heure."), "C'est l'heure.")


if __name__ == "__main__":
    unittest.main()
