from django.contrib.auth.models import User
from django.test import TestCase

from website.utils import check_for_spam


class SpamCheckTests(TestCase):
    """Tests for spam detection functionality"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_normal_text_not_spam(self):
        """Test that normal text is not flagged as spam"""
        text = "This is a legitimate bug report about a security vulnerability"
        is_spam, reason = check_for_spam(text)
        self.assertFalse(is_spam)
        self.assertIsNone(reason)

    def test_spam_keywords_detected(self):
        """Test that spam keywords are detected"""
        spam_texts = [
            "Buy viagra online now!",
            "Get rich quick with crypto investment",
            "Congratulations you won a lottery!",
            "Work from home and make money fast",
        ]
        for text in spam_texts:
            is_spam, reason = check_for_spam(text)
            self.assertTrue(is_spam, f"Failed to detect spam in: {text}")
            self.assertIn("spam keyword", reason.lower())

    def test_excessive_urls_detected(self):
        """Test that excessive URLs are flagged"""
        text = "Check out https://url1.com https://url2.com https://url3.com https://url4.com https://url5.com https://url6.com"
        is_spam, reason = check_for_spam(text)
        self.assertTrue(is_spam)
        self.assertIn("excessive URLs", reason)

    def test_excessive_capitalization_detected(self):
        """Test that excessive capitalization is flagged"""
        text = "THIS IS ALL CAPS AND VERY SUSPICIOUS TEXT"
        is_spam, reason = check_for_spam(text)
        self.assertTrue(is_spam)
        self.assertIn("capitalization", reason)

    def test_repeated_characters_detected(self):
        """Test that excessive repeated characters are flagged"""
        text = "This is amazing!!!!!!!!"
        is_spam, reason = check_for_spam(text)
        self.assertTrue(is_spam)
        self.assertIn("repeated characters", reason)

    def test_high_url_to_text_ratio_detected(self):
        """Test that high URL-to-text ratio is flagged"""
        text = "Check https://spam1.com https://spam2.com https://spam3.com"
        is_spam, reason = check_for_spam(text)
        self.assertTrue(is_spam)
        self.assertIn("URL-to-text ratio", reason)

    def test_short_content_with_urls_detected(self):
        """Test that very short content with URLs is flagged"""
        text = "https://spam.com"
        is_spam, reason = check_for_spam(text)
        self.assertTrue(is_spam)
        # Either reason is valid for spam detection
        self.assertTrue("URL" in reason or "short content" in reason)

    def test_empty_text_not_spam(self):
        """Test that empty text is not flagged"""
        is_spam, reason = check_for_spam("")
        self.assertFalse(is_spam)
        self.assertIsNone(reason)

    def test_none_text_not_spam(self):
        """Test that None text is not flagged"""
        is_spam, reason = check_for_spam(None)
        self.assertFalse(is_spam)
        self.assertIsNone(reason)

    def test_legitimate_issue_with_urls(self):
        """Test that legitimate bug reports with reasonable URLs are not flagged"""
        text = """
        I found a security vulnerability at https://example.com/login
        Steps to reproduce: 
        1. Visit the login page
        2. Enter special characters
        The issue is documented at https://github.com/repo/issues/123
        """
        is_spam, reason = check_for_spam(text)
        if is_spam:
            self.fail(f"Legitimate issue was incorrectly flagged as spam. Reason: {reason}")
        self.assertFalse(is_spam)

    def test_case_insensitive_keyword_detection(self):
        """Test that spam keywords are detected regardless of case"""
        text = "BUY VIAGRA NOW"
        is_spam, reason = check_for_spam(text)
        self.assertTrue(is_spam)
        self.assertIn("spam keyword", reason.lower())
