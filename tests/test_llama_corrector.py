import unittest
from unittest.mock import Mock, patch

from typozap.correctors import LocalEngineCorrector


class LocalEngineCorrectorTests(unittest.TestCase):
    @patch("typozap.correctors.requests.post")
    def test_uses_chat_template_endpoint(self, post):
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": "Les enfants jouent."}}]
        }
        response.raise_for_status.return_value = None
        post.return_value = response

        result = LocalEngineCorrector("http://127.0.0.1:1234").correct_text("Les enfant joue.")

        self.assertEqual(result, "Les enfants jouent.")
        self.assertTrue(post.call_args.args[0].endswith("/v1/chat/completions"))
        self.assertEqual(post.call_args.kwargs["json"]["temperature"], 0)


if __name__ == "__main__":
    unittest.main()
