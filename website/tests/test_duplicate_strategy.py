from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from website.duplicate_checker import (
    DuplicateDetectionStrategy,
    SequenceMatcherStrategy,
    VectorSearchStrategy,
    check_for_duplicates,
    find_similar_bugs,
    format_similar_bug,
    get_duplicate_strategy,
)
from website.models import Issue


class DuplicateStrategyTest(TestCase):
    def test_strategy_is_abc(self):
        """Ensure DuplicateDetectionStrategy cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            DuplicateDetectionStrategy()

    def test_sequence_matcher_strategy_normalization(self):
        """Test text normalization in SequenceMatcherStrategy."""
        strategy = SequenceMatcherStrategy()
        self.assertEqual(strategy.normalize_text("  HeLLo World!  "), "hello world")
        self.assertEqual(strategy.normalize_text(None), "")

    def test_sequence_matcher_strategy_domain_extraction(self):
        """Test domain extraction logic."""
        strategy = SequenceMatcherStrategy()
        self.assertEqual(strategy.extract_domain_from_url("https://www.google.com/search"), "google.com")
        self.assertEqual(strategy.extract_domain_from_url("//example.org/path"), "example.org")
        self.assertEqual(strategy.extract_domain_from_url("example.net"), "example.net")

    def test_sequence_matcher_similarity(self):
        """Test similarity calculation."""
        strategy = SequenceMatcherStrategy()
        score = strategy.calculate_similarity("bug report", "bug report")
        self.assertEqual(score, 1.0)

        score_diff = strategy.calculate_similarity("bug report", "feature request")
        self.assertTrue(score_diff < 0.5)

    def test_vector_search_not_implemented(self):
        """Test that VectorSearchStrategy raises NotImplementedError."""
        strategy = VectorSearchStrategy()
        with self.assertRaises(NotImplementedError):
            strategy.find_similar("http://example.com", "test")

    def test_get_duplicate_strategy_default(self):
        """Test factory returns SequenceMatcherStrategy by default."""
        strategy = get_duplicate_strategy()
        self.assertIsInstance(strategy, SequenceMatcherStrategy)

    @override_settings(DUPLICATE_DETECTION_STRATEGY="vector_search")
    def test_get_duplicate_strategy_configured(self):
        """Test factory returns VectorSearchStrategy when configured."""
        strategy = get_duplicate_strategy()
        self.assertIsInstance(strategy, VectorSearchStrategy)

    @patch("website.duplicate_checker.SequenceMatcherStrategy.find_similar")
    def test_facade_integration(self, mock_find_similar):
        """Test that facades correctly delegate to the active strategy."""
        mock_find_similar.return_value = [
            {
                "issue": MagicMock(spec=Issue),
                "similarity": 0.85,
                "description_similarity": 0.85,
                "url_similarity": 0.0,
                "keyword_matches": 0,
            }
        ]

        # Test find_similar_bugs facade
        results = find_similar_bugs("http://test.com", "desc")
        self.assertEqual(len(results), 1)
        mock_find_similar.assert_called_once()

        # Test check_for_duplicates facade
        result = check_for_duplicates("http://test.com", "desc")
        self.assertTrue(result["is_duplicate"])

    def test_format_similar_bug(self):
        """Test the boolean and formatting logic of format_similar_bug."""
        mock_issue = MagicMock(spec=Issue)
        mock_issue.id = 123
        mock_issue.url = "http://example.com/bug"
        mock_issue.description = "A very long description " * 10
        mock_issue.status = "open"
        mock_issue.created = "2023-01-01"
        mock_issue.user.username = "tester"
        mock_issue.upvoted.count.return_value = 5

        bug_info = {
            "issue": mock_issue,
            "similarity": 0.95,
            "description_similarity": 0.9,
            "url_similarity": 1.0,
            "keyword_matches": 3,
        }

        formatted = format_similar_bug(bug_info, truncate_description=20)

        self.assertEqual(formatted["id"], 123)
        self.assertEqual(formatted["similarity_percent"], 95)
        self.assertTrue(len(formatted["description"]) <= 23)  # 20 chars + "..."
        self.assertTrue(formatted["description"].endswith("..."))
