from unittest.mock import MagicMock, patch

from django.test import TestCase

from website.views.slack_handlers import (
    _handle_contribute_message,
    _handle_team_join,
    extract_text_from_blocks,
    handle_message,
)


class SlackFunctionTests(TestCase):
    def setUp(self):
        self.mock_client = MagicMock()

    def test_extract_text_from_blocks(self):
        """Test extracting text from Slack block format"""
        # Test rich text blocks
        blocks = [
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": [{"type": "text", "text": "I want to contribute"}],
                    }
                ],
            }
        ]

        self.assertEqual(extract_text_from_blocks(blocks), "I want to contribute")

        # Test empty blocks
        self.assertEqual(extract_text_from_blocks([]), "")

        # Test invalid blocks
        self.assertEqual(extract_text_from_blocks(None), "")

    @patch("website.views.slack_handlers.client")
    def test_handle_contribute_message(self, mock_client):
        """Test contribute message handler"""
        message = {
            "user": "U123",
            "channel": "C123",
            "text": "How do I contribute?",
            "subtype": None,
        }

        _handle_contribute_message(message)

        mock_client.chat_postMessage.assert_called_once()

        # Test message without contribute keyword
        message["text"] = "Hello world"
        mock_client.chat_postMessage.reset_mock()
        _handle_contribute_message(message)
        mock_client.chat_postMessage.assert_not_called()

    @patch("website.views.slack_handlers.client")
    def test_handle_team_join(self, mock_client):
        """Test team join handler"""
        mock_client.conversations_open.return_value = {"ok": True, "channel": {"id": "D123"}}

        _handle_team_join("U123")

        # Should send welcome message in joins channel
        mock_client.chat_postMessage.assert_called()

        # Should try to open DM
        mock_client.conversations_open.assert_called_once_with(users=["U123"])

    @patch("website.views.slack_handlers.client")
    def test_handle_message(self, mock_client):
        """Test main message handler"""
        # Mock bot user ID
        mock_client.auth_test.return_value = {"user_id": "BOT123"}

        # Test normal user message
        payload = {"user": "U123", "text": "contribute", "channel": "C123"}

        handle_message(payload)
        mock_client.chat_postMessage.assert_called()

        # Test bot message (should be ignored)
        payload["user"] = "BOT123"
        mock_client.chat_postMessage.reset_mock()
        handle_message(payload)
        mock_client.chat_postMessage.assert_not_called()
