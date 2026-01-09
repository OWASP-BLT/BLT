"""
Tests for trademark models and integration.
"""

from django.test import TestCase

from website.models import Organization, TrademarkMatch


class TrademarkMatchModelTestCase(TestCase):
    """Test cases for TrademarkMatch model."""

    def setUp(self):
        """Set up test fixtures."""
        self.org = Organization.objects.create(name="Test Organization", slug="test-org")

    def test_trademark_match_creation(self):
        """Test creating a TrademarkMatch."""
        match = TrademarkMatch.objects.create(
            organization=self.org,
            checked_name="Test Organization",
            matched_trademark_name="Test Mark Inc.",
            similarity_score=92.5,
            risk_level="high",
        )

        self.assertEqual(match.organization, self.org)
        self.assertEqual(match.similarity_score, 92.5)
        self.assertEqual(match.risk_level, "high")
        self.assertFalse(match.is_reviewed)
        self.assertEqual(match.status, "pending")

    def test_trademark_match_is_high_risk(self):
        """Test is_high_risk property."""
        high_risk = TrademarkMatch.objects.create(
            organization=self.org,
            checked_name="Test",
            matched_trademark_name="Mark",
            similarity_score=95.0,
            risk_level="high",
        )

        low_risk = TrademarkMatch.objects.create(
            organization=self.org,
            checked_name="Test",
            matched_trademark_name="Mark2",
            similarity_score=75.0,
            risk_level="low",
        )

        self.assertTrue(high_risk.is_high_risk)
        self.assertFalse(low_risk.is_high_risk)

    def test_trademark_match_str(self):
        """Test string representation."""
        match = TrademarkMatch.objects.create(
            organization=self.org,
            checked_name="Test",
            matched_trademark_name="Test Mark",
            similarity_score=90.0,
            risk_level="high",
        )

        self.assertIn("Test Organization", str(match))
        self.assertIn("Test Mark", str(match))

    def test_trademark_match_ordering(self):
        """Test that matches are ordered by score descending."""
        m1 = TrademarkMatch.objects.create(
            organization=self.org,
            checked_name="Test",
            matched_trademark_name="Mark1",
            similarity_score=80.0,
            risk_level="medium",
        )
        m2 = TrademarkMatch.objects.create(
            organization=self.org,
            checked_name="Test",
            matched_trademark_name="Mark2",
            similarity_score=95.0,
            risk_level="high",
        )

        matches = list(TrademarkMatch.objects.filter(organization=self.org))
        self.assertEqual(matches[0].similarity_score, 95.0)
        self.assertEqual(matches[1].similarity_score, 80.0)
