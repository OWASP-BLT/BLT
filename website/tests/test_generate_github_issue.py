import os
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from website.views.issue import generate_github_issue


class GenerateGithubIssueTests(SimpleTestCase):
    @patch("website.views.issue.OpenAI")
    def test_generate_github_issue_success(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"title": "Bug", "description": "Details", "labels": ["bug"]}'
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value.with_options.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            result = generate_github_issue("Something is wrong")

        self.assertEqual(result["title"], "Bug")
        self.assertEqual(result["description"], "Details")
        self.assertEqual(result["labels"], ["bug"])
        mock_openai.assert_called_once_with(api_key="sk-test")
        mock_client.chat.completions.create.assert_called_once()

    @patch("website.views.issue.OpenAI")
    def test_generate_github_issue_handles_invalid_json(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "not-json"
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value.with_options.return_value = mock_client

        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            result = generate_github_issue("Bad format")

        self.assertIn("error", result)

    def test_generate_github_issue_missing_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            result = generate_github_issue("No key configured")

        self.assertIn("error", result)

