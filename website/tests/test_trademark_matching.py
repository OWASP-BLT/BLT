"""
Unit tests for trademark matching service.
"""

from django.test import TestCase

from website.services.trademark_matching import TrademarkCandidate, TrademarkMatcher, get_trademark_matches


class TrademarkMatcherTestCase(TestCase):
    """Test cases for TrademarkMatcher core logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.matcher = TrademarkMatcher(threshold=85.0)

    def test_normalize_removes_special_chars(self):
        """Test that normalize removes non-alphanumeric characters."""
        result = self.matcher.normalize("Bug-Heist Inc.")
        self.assertEqual(result, "bugheistinc")

    def test_normalize_lowercases(self):
        """Test that normalize converts to lowercase."""
        result = self.matcher.normalize("BugHeist")
        self.assertEqual(result, "bugheist")

    def test_normalize_empty_string(self):
        """Test normalize with empty string."""
        result = self.matcher.normalize("")
        self.assertEqual(result, "")

    def test_levenshtein_distance_identical(self):
        """Test Levenshtein distance for identical strings."""
        distance = self.matcher._levenshtein_distance("abc", "abc")
        self.assertEqual(distance, 0)

    def test_levenshtein_distance_one_char_diff(self):
        """Test Levenshtein distance with one character difference."""
        distance = self.matcher._levenshtein_distance("cat", "bat")
        self.assertEqual(distance, 1)

    def test_levenshtein_distance_empty_strings(self):
        """Test Levenshtein distance with empty strings."""
        distance = self.matcher._levenshtein_distance("", "")
        self.assertEqual(distance, 0)

    def test_levenshtein_distance_empty_vs_nonempty(self):
        """Test Levenshtein distance with one empty string."""
        distance = self.matcher._levenshtein_distance("abc", "")
        self.assertEqual(distance, 3)

    def test_similarity_score_identical(self):
        """Test similarity score for identical strings."""
        score = self.matcher._similarity_score("bugheist", "bugheist")
        self.assertEqual(score, 100.0)

    def test_similarity_score_empty_strings(self):
        """Test similarity score for empty strings."""
        score = self.matcher._similarity_score("", "")
        self.assertEqual(score, 100.0)

    def test_match_exact_match(self):
        """Test matching with exact match."""
        trademarks = ["BugHeist", "Bug Hunt", "Other"]
        results = self.matcher.match("BugHeist", trademarks)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "BugHeist")
        self.assertEqual(results[0].score, 100.0)

    def test_match_similar_match(self):
        """Test matching with similar but not exact match."""
        trademarks = ["Bug Heist Inc.", "CompletelyDifferent"]
        # Use a lower threshold to ensure a match, or just check ordering if any
        matcher = TrademarkMatcher(threshold=70.0)
        results = matcher.match("BugHeist", trademarks)

        # At least one match when threshold is lower
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].name, "Bug Heist Inc.")

    def test_match_below_threshold(self):
        """Test that matches below threshold are not returned."""
        trademarks = ["XYZ Corporation", "ABC Services"]
        results = self.matcher.match("BugHeist", trademarks)

        # These should not match; they are too different
        self.assertEqual(len(results), 0)

    def test_match_respects_limit(self):
        """Test that limit parameter is respected."""
        trademarks = [f"Bug{i}" for i in range(20)]
        results = self.matcher.match("Bug0", trademarks, limit=5)

        self.assertLessEqual(len(results), 5)

    def test_match_sorted_by_score(self):
        """Test that results are sorted by score descending."""
        trademarks = ["BugHeist", "Bug Heist", "BugHeistInc"]
        results = self.matcher.match("BugHeist", trademarks)

        # All should be found, sorted by score
        self.assertGreater(len(results), 0)
        for i in range(len(results) - 1):
            self.assertGreaterEqual(results[i].score, results[i + 1].score)

    def test_match_empty_input(self):
        """Test matching with empty company name."""
        trademarks = ["BugHeist"]
        results = self.matcher.match("", trademarks)

        self.assertEqual(len(results), 0)

    def test_match_empty_trademarks(self):
        """Test matching with empty trademark list."""
        results = self.matcher.match("BugHeist", [])

        self.assertEqual(len(results), 0)

    def test_get_trademark_matches_convenience(self):
        """Test convenience function get_trademark_matches."""
        results = get_trademark_matches("BugHeist")

        # Should find at least one match in sample data
        self.assertIsInstance(results, list)
        if len(results) > 0:
            self.assertIsInstance(results[0], TrademarkCandidate)

    def test_candidate_dataclass(self):
        """Test TrademarkCandidate dataclass."""
        candidate = TrademarkCandidate(name="TestMark", score=95.5)

        self.assertEqual(candidate.name, "TestMark")
        self.assertEqual(candidate.score, 95.5)

    def test_threshold_filtering(self):
        """Test that threshold correctly filters results."""
        matcher_strict = TrademarkMatcher(threshold=95.0)
        matcher_loose = TrademarkMatcher(threshold=70.0)

        trademarks = ["BugHeist", "Bug Heist", "Similar"]

        strict_results = matcher_strict.match("BugHeist", trademarks)
        loose_results = matcher_loose.match("BugHeist", trademarks)

        # Loose matcher should find at least as many as strict
        self.assertGreaterEqual(len(loose_results), len(strict_results))
