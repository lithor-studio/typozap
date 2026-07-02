import unittest
from unittest.mock import Mock, patch

from typozap.correctors import CorrectionError, MAX_CHUNK_CHARS, MinistralCorrector, build_prompt, split_text


class MinistralCorrectorTests(unittest.TestCase):
    def setUp(self):
        self.corrector = MinistralCorrector("http://127.0.0.1:1234")

    def response(self, content, finish_reason="stop"):
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": content}, "finish_reason": finish_reason}]
        }
        response.raise_for_status.return_value = None
        return response

    def test_empty_text_does_not_call_engine(self):
        with patch("typozap.correctors.requests.post") as post:
            self.assertEqual(self.corrector.correct_text(""), "")
            post.assert_not_called()

    @patch("typozap.correctors.requests.post")
    def test_uses_fixed_local_endpoint_and_options(self, post):
        post.return_value = self.response("  Les enfants jouent.  ")
        result = self.corrector.correct_text("Les enfant joue.")
        self.assertEqual(result, "Les enfants jouent.")
        self.assertTrue(post.call_args.args[0].endswith("/v1/chat/completions"))
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["temperature"], 0)
        self.assertIn("Les enfant joue.", payload["messages"][0]["content"])

    def test_prompt_uses_requested_style(self):
        self.assertIn("registre formel", build_prompt("bonjour", "formel"))

    def test_long_text_is_split_without_data_loss(self):
        text = ("Une phrase complète. " * 700).strip()
        chunks = split_text(text)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= MAX_CHUNK_CHARS for chunk in chunks))
        self.assertEqual("".join(chunks), text)

    def test_prompt_includes_local_preferences(self):
        prompt = build_prompt("Bonjour", options={
            "strict": True, "dictionary": ["TypoZap"],
            "tone": "chaleureux", "style_guide": "Toujours vouvoyer",
        })
        self.assertIn("reformulation est interdite", prompt)
        self.assertIn("TypoZap", prompt)
        self.assertIn("Toujours vouvoyer", prompt)
        self.assertNotIn("chaleureux", prompt)

    @patch("typozap.correctors.requests.post")
    def test_rejects_truncated_response(self, post):
        post.return_value = self.response("Texte partiel", "length")
        with self.assertRaises(CorrectionError):
            self.corrector.correct_text("Un texte suffisamment long pour être corrigé.")

    @patch("typozap.correctors.requests.post")
    def test_rejects_suspiciously_short_response(self, post):
        post.return_value = self.response("Trop court.")
        with self.assertRaises(CorrectionError):
            self.corrector.correct_text("Une phrase assez longue. " * 20)

    @patch("typozap.correctors.requests.post")
    def test_preserves_straight_apostrophe_style(self, post):
        post.return_value = self.response("C’est l’heure.")
        self.assertEqual(self.corrector.correct_text("C'est l'heure."), "C'est l'heure.")

    @patch("typozap.correctors.requests.post")
    def test_preserves_surrounding_whitespace(self, post):
        post.return_value = self.response("Phrase corrigée.")
        self.assertEqual(
            self.corrector.correct_text("\n  Phrase corrigee.\n\n"),
            "\n  Phrase corrigée.\n\n",
        )


if __name__ == "__main__":
    unittest.main()
