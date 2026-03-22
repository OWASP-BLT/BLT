from django.test import TestCase
from website.spam_checker import normalize_homoglyphs, check_spam_keywords


class TestHomoglyphNormalization(TestCase):
    def test_homoglyph_and_punctuation_bypass(self):
        # Testing "Fr€€ M0n€y!" pattern
        text = "Fr€€ M0n€y!"
        normalized = normalize_homoglyphs(text)
        self.assertEqual(normalized, "free money")

    def test_keyword_detection_after_normalization(self):
        # Testing if the spam checker actually catches it now
        text = "B0TC0IN investment"
        normalized = normalize_homoglyphs(text)
        score = check_spam_keywords(normalized)
        self.assertGreater(score, 0, "Should catch normalized 'bitcoin' keyword")
