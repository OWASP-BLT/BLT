from django.contrib.auth.models import User
from django.db.models import Sum
from django.test import TestCase

from website.models import Points


class BaconIntegrityTest(TestCase):
    """Integrity tests for the Points (BACON) reward system."""

    def setUp(self):
        """Set up a test user for point awarding."""
        self.user = User.objects.create_user(username="bacon_hunter", password="password123")

    def test_points_creation_and_summation(self):
        """Verify points are awarded and total score is accurate using ORM aggregation."""
        # 1. Award points for different actions
        Points.objects.create(user=self.user, score=50, reason="Bug Report")
        Points.objects.create(user=self.user, score=25, reason="Daily Login")

        # 2. Verify accumulation via DB-level aggregation (The Production Path)
        result = Points.objects.filter(user=self.user).aggregate(total=Sum("score"))
        total_score = result["total"] or 0

        self.assertEqual(total_score, 75)

    def test_reason_field_integrity(self):
        """Ensure the reason for points is persisted and retrieved correctly (DB round-trip)."""
        reason_str = "Completed profile setup"
        point_entry = Points.objects.create(user=self.user, score=10, reason=reason_str)

        # Force a re-fetch from the database to verify persistence
        point_entry.refresh_from_db()

        self.assertEqual(point_entry.reason, reason_str)
