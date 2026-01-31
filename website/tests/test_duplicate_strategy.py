from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from website.duplicate_checker import (
    DuplicateDetectionStrategy,
    SequenceMatcherStrategy,
    VectorSearchStrategy,
    check_for_duplicates,
    find_similar_bugs,
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
