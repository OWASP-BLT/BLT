from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from website.spam_checker import (
    calculate_spam_score,
    check_spam_keywords,
    count_urls,
    is_new_account,
    is_repetitive_content,
)


class TestCountUrls(TestCase):
    def test_no_urls(self):
        self.assertEqual(count_urls("This is a normal description"), 0)

    def test_single_url(self):
        self.assertEqual(count_urls("Check https://example.com for details"), 1)

    def test_multiple_urls(self):
        text = "Visit https://a.com and https://b.com and http://c.com"
        self.assertEqual(count_urls(text), 3)

    def test_empty_text(self):
        self.assertEqual(count_urls(""), 0)
        self.assertEqual(count_urls(None), 0)

    def test_www_urls(self):
        self.assertEqual(count_urls("Go to www.example.com"), 1)


class TestCheckSpamKeywords(TestCase):
    def test_no_spam(self):
        self.assertEqual(check_spam_keywords("Found a bug on the login page"), 0)

    def test_buy_now_pattern(self):
        self.assertGreater(check_spam_keywords("Buy now and save big!"), 0)

    def test_crypto_spam(self):
        self.assertGreater(check_spam_keywords("Bitcoin doubler - send BTC now"), 0)

    def test_empty_text(self):
        self.assertEqual(check_spam_keywords(""), 0)
        self.assertEqual(check_spam_keywords(None), 0)

    def test_case_insensitive(self):
        self.assertGreater(check_spam_keywords("FREE MONEY for everyone"), 0)


class TestIsNewAccount(TestCase):
    def test_anonymous_user(self):
        user = MagicMock()
        user.is_authenticated = False
        self.assertTrue(is_new_account(user))

    def test_none_user(self):
        self.assertTrue(is_new_account(None))

    def test_new_account(self):
        user = MagicMock()
        user.is_authenticated = True
        user.date_joined = timezone.now() - timedelta(days=2)
        self.assertTrue(is_new_account(user))

    def test_old_account(self):
        user = MagicMock()
        user.is_authenticated = True
        user.date_joined = timezone.now() - timedelta(days=30)
        self.assertFalse(is_new_account(user))


class TestIsRepetitiveContent(TestCase):
    def test_normal_text(self):
        self.assertFalse(
            is_repetitive_content(
                "The login page has a cross-site scripting vulnerability "
                "when entering special characters in the username field"
            )
        )

    def test_repetitive_text(self):
        self.assertTrue(is_repetitive_content("spam " * 30))

    def test_short_text(self):
        self.assertFalse(is_repetitive_content("short"))

    def test_empty_text(self):
        self.assertFalse(is_repetitive_content(""))
        self.assertFalse(is_repetitive_content(None))


class TestCalculateSpamScore(TestCase):
    def _make_user(self, days_old=30, authenticated=True):
        user = MagicMock()
        user.is_authenticated = authenticated
        user.date_joined = timezone.now() - timedelta(days=days_old)
        return user

    @patch("website.spam_checker.check_rapid_submissions", return_value=False)
    def test_legitimate_report(self, mock_rapid):
        user = self._make_user(days_old=30)
        result = calculate_spam_score(
            description="Found XSS vulnerability on the login page",
            markdown_description="## Steps\n1. Enter `<script>` in username field",
            user=user,
            reporter_ip="192.168.1.1",
        )
        self.assertFalse(result["is_spam"])
        self.assertLess(result["score"], 3)

    @patch("website.spam_checker.check_rapid_submissions", return_value=False)
    def test_spammy_report(self, mock_rapid):
        user = self._make_user(days_old=1)
        result = calculate_spam_score(
            description="BUY NOW",
            markdown_description="Click here https://a.com https://b.com https://c.com https://d.com",
            user=user,
            reporter_ip="10.0.0.1",
        )
        self.assertTrue(result["is_spam"])
        self.assertGreater(len(result["reasons"]), 0)

    @patch("website.spam_checker.check_rapid_submissions", return_value=True)
    def test_rapid_submissions_flagged(self, mock_rapid):
        user = self._make_user(days_old=1)
        result = calculate_spam_score(
            description="Another submission",
            markdown_description="",
            user=user,
            reporter_ip="10.0.0.1",
        )
        self.assertIn("Rapid successive submissions detected", result["reasons"])

    @patch("website.spam_checker.check_rapid_submissions", return_value=False)
    def test_returns_dict_with_required_keys(self, mock_rapid):
        user = self._make_user()
        result = calculate_spam_score("test", "", user, "1.2.3.4")
        self.assertIn("score", result)
        self.assertIn("is_spam", result)
        self.assertIn("reasons", result)
        self.assertIsInstance(result["score"], int)
        self.assertIsInstance(result["is_spam"], bool)
        self.assertIsInstance(result["reasons"], list)
