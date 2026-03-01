from datetime import datetime

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from website.models import Domain, Issue, Points, UserProfile


class UserMonthlyActivityViewTest(TestCase):
    def setUp(self):
        """Create test users, issues, and points data."""
        self.client = Client()

        # Create test users
        self.user1 = User.objects.create_user(username="testuser1", email="test1@example.com", password="testpass123")
        self.user2 = User.objects.create_user(username="testuser2", email="test2@example.com", password="testpass123")
        self.staff_user = User.objects.create_user(
            username="staffuser", email="staff@example.com", password="testpass123", is_staff=True
        )

        # Ensure UserProfiles exist
        UserProfile.objects.get_or_create(user=self.user1)
        UserProfile.objects.get_or_create(user=self.user2)
        UserProfile.objects.get_or_create(user=self.staff_user)

        # Create a domain
        self.domain = Domain.objects.create(name="example.com", url="https://example.com")

        # Create issues for user1
        self.issue1 = Issue.objects.create(
            user=self.user1,
            url="https://example.com/issue1",
            description="Test issue 1",
            domain=self.domain,
        )
        self.issue2 = Issue.objects.create(
            user=self.user1,
            url="https://example.com/issue2",
            description="Test issue 2",
            domain=self.domain,
            is_hidden=True,  # Hidden issue
        )

        # Create points for user1 in January 2024
        self.points1 = Points.objects.create(
            user=self.user1,
            issue=self.issue1,
            domain=self.domain,
            score=20,
            created=datetime(2024, 1, 15, tzinfo=timezone.utc),
        )
        self.points2 = Points.objects.create(
            user=self.user1,
            issue=self.issue2,
            domain=self.domain,
            score=15,
            created=datetime(2024, 1, 20, tzinfo=timezone.utc),
        )

        # Create points for user1 in February 2024
        self.points3 = Points.objects.create(
            user=self.user1,
            domain=self.domain,
            score=10,
            created=datetime(2024, 2, 5, tzinfo=timezone.utc),
        )

        # Create points for user2 in January 2024
        self.points4 = Points.objects.create(
            user=self.user2,
            domain=self.domain,
            score=25,
            created=datetime(2024, 1, 10, tzinfo=timezone.utc),
        )

    def test_view_url_exists(self):
        """Test that the view URL is accessible."""
        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=1&year=2024"
        )
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        """Test that the view uses the correct template."""
        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=1&year=2024"
        )
        self.assertTemplateUsed(response, "user_monthly_activity.html")

    def test_missing_month_parameter_returns_404(self):
        """Test that missing month parameter returns 404."""
        response = self.client.get(reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?year=2024")
        self.assertEqual(response.status_code, 404)

    def test_missing_year_parameter_returns_404(self):
        """Test that missing year parameter returns 404."""
        response = self.client.get(reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=1")
        self.assertEqual(response.status_code, 404)

    def test_invalid_month_returns_404(self):
        """Test that invalid month returns 404."""
        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=13&year=2024"
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=0&year=2024"
        )
        self.assertEqual(response.status_code, 404)

    def test_invalid_month_format_returns_404(self):
        """Test that non-numeric month returns 404."""
        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=abc&year=2024"
        )
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_user_returns_404(self):
        """Test that nonexistent user returns 404."""
        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "nonexistent"}) + "?month=1&year=2024"
        )
        self.assertEqual(response.status_code, 404)

    def test_correct_points_for_user_and_month(self):
        """Test that the view returns correct points for specific user and month."""
        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=1&year=2024"
        )
        self.assertEqual(response.status_code, 200)

        # Check that points from January 2024 are included
        points_list = response.context["points_list"]
        self.assertEqual(len(points_list), 2)

        # Check that points from February are not included
        point_ids = [p.id for p in points_list]
        self.assertIn(self.points1.id, point_ids)
        self.assertIn(self.points2.id, point_ids)
        self.assertNotIn(self.points3.id, point_ids)

    def test_correct_total_score_calculation(self):
        """Test that total score is calculated correctly."""
        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=1&year=2024"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_score"], 35)  # 20 + 15

    def test_correct_issue_count(self):
        """Test that issue count is calculated correctly."""
        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=1&year=2024"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["issue_count"], 2)  # 2 distinct issues

    def test_month_name_in_context(self):
        """Test that month name is correctly set."""
        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=1&year=2024"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["month_name"], "January")

    def test_different_user_points_not_included(self):
        """Test that points from other users are not included."""
        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=1&year=2024"
        )
        self.assertEqual(response.status_code, 200)

        points_list = response.context["points_list"]
        point_ids = [p.id for p in points_list]
        self.assertNotIn(self.points4.id, point_ids)  # user2's points

    def test_hidden_issue_visibility_for_owner(self):
        """Test that issue owner can see their own hidden issues."""
        self.client.login(username="testuser1", password="testpass123")
        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=1&year=2024"
        )
        self.assertEqual(response.status_code, 200)

        # Should see both points including the one with hidden issue
        points_list = response.context["points_list"]
        self.assertEqual(len(points_list), 2)
        point_ids = [p.id for p in points_list]
        self.assertIn(self.points2.id, point_ids)  # Hidden issue point

    def test_hidden_issue_visibility_for_other_users(self):
        """Test that other users cannot see hidden issues."""
        self.client.login(username="testuser2", password="testpass123")
        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=1&year=2024"
        )
        self.assertEqual(response.status_code, 200)

        # Should only see the non-hidden issue point
        points_list = response.context["points_list"]
        self.assertEqual(len(points_list), 1)
        point_ids = [p.id for p in points_list]
        self.assertIn(self.points1.id, point_ids)
        self.assertNotIn(self.points2.id, point_ids)  # Hidden issue point excluded

    def test_hidden_issue_visibility_for_staff(self):
        """Test that staff users can see hidden issues."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=1&year=2024"
        )
        self.assertEqual(response.status_code, 200)

        # Staff should see all points including hidden ones
        points_list = response.context["points_list"]
        self.assertEqual(len(points_list), 2)
        point_ids = [p.id for p in points_list]
        self.assertIn(self.points2.id, point_ids)  # Hidden issue point

    def test_pagination(self):
        """Test that pagination works correctly."""
        # Create many points to test pagination (paginate_by = 50)
        for i in range(60):
            Points.objects.create(
                user=self.user1,
                domain=self.domain,
                score=1,
                created=datetime(2024, 3, 1, tzinfo=timezone.utc),
            )

        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=3&year=2024"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["points_list"]), 50)

        # Check second page
        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "testuser1"}) + "?month=3&year=2024&page=2"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["points_list"]), 10)

    def test_user_profile_created_if_missing(self):
        """Test that UserProfile is created if it doesn't exist."""
        # Create a user without a profile
        user_no_profile = User.objects.create_user(
            username="noprofile", email="noprofile@example.com", password="testpass123"
        )
        # Delete the profile if it was auto-created
        UserProfile.objects.filter(user=user_no_profile).delete()

        # Create a point for this user
        Points.objects.create(
            user=user_no_profile,
            domain=self.domain,
            score=10,
            created=datetime(2024, 4, 1, tzinfo=timezone.utc),
        )

        # Access the view - should not crash
        response = self.client.get(
            reverse("user_monthly_activity", kwargs={"username": "noprofile"}) + "?month=4&year=2024"
        )
        self.assertEqual(response.status_code, 200)

        # Verify UserProfile was created
        self.assertTrue(UserProfile.objects.filter(user=user_no_profile).exists())
