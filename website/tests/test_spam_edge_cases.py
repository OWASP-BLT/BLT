from django.test import TestCase
from website.spam_checker import calculate_spam_score

class SpamCheckerEdgeCaseTest(TestCase):

    def test_repetitive_emojis_not_detected(self):
        # 100 emojis with no spaces
        description = "😂" * 100
        markdown_description = ""

        # Run it through the scanner
        result = calculate_spam_score(
            description=description,
            markdown_description=markdown_description,
            user=None,
            reporter_ip="127.0.0.1",
        )

        # Documenting the weakness: Currently, the system DOES NOT flag this as spam.
        # We assert False so the test passes, but it highlights the logic gap.
        self.assertFalse(
            result["is_spam"],
            "LIMITATION: Repetitive emojis without spaces bypass the spam filter."
        )