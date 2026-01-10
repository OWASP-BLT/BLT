from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Issue, Points


class BugsListTest(TestCase):
    def setUp(self):
        # Create test users
        self.client = Client()

        # Create a verified user
        self.verified_user = User.objects.create_user(
            username="verified_user", email="verified@example.com", password="testpass123"
        )
        # UserProfile is created automatically by signal
        EmailAddress.objects.create(user=self.verified_user, email="verified@example.com", verified=True, primary=True)

        # Create an unverified user
        self.unverified_user = User.objects.create_user(
            username="unverified_user", email="unverified@example.com", password="testpass123"
        )
        # UserProfile is created automatically by signal
        EmailAddress.objects.create(
            user=self.unverified_user, email="unverified@example.com", verified=False, primary=True
        )

        # Create some test issues
        self.visible_issue = Issue.objects.create(
            url="http://example.com/visible", description="Visible Test Issue", user=self.verified_user, is_hidden=False
        )

        self.hidden_issue = Issue.objects.create(
            url="http://example.com/hidden", description="Hidden Test Issue", user=self.verified_user, is_hidden=True
        )

        # Create issue from another user that's hidden
        self.other_hidden_issue = Issue.objects.create(
            url="http://example.com/other_hidden",
            description="Other Hidden Test Issue",
            user=self.unverified_user,
            is_hidden=True,
        )

        # Add some points for leaderboard testing
        Points.objects.create(user=self.verified_user, score=50)
        Points.objects.create(user=self.unverified_user, score=30)

    def test_bugs_list_anonymous(self):
        """Test bugs_list page for anonymous users"""
        url = reverse("issues")
        response = self.client.get(url)

        # Check response basics
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bugs_list.html")

        # Check context data
        self.assertIn("bugs", response.context)
        self.assertIn("bugs_screenshots", response.context)
        self.assertIn("leaderboard", response.context)

        # Verify only visible issues are shown
        bugs = list(response.context["bugs"])
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0].id, self.visible_issue.id)

        # Verify hidden issues are not shown
        for bug in bugs:
            self.assertNotEqual(bug.id, self.hidden_issue.id)
            self.assertNotEqual(bug.id, self.other_hidden_issue.id)

    def test_bugs_list_verified_user(self):
        """Test bugs_list page for verified users"""
        self.client.login(username="verified_user", password="testpass123")
        url = reverse("issues")
        response = self.client.get(url)

        # Check response basics
        self.assertEqual(response.status_code, 200)

        # Verify user can see their own hidden issues
        bugs = list(response.context["bugs"])
        visible_ids = [bug.id for bug in bugs]
        self.assertIn(self.visible_issue.id, visible_ids)
        self.assertIn(self.hidden_issue.id, visible_ids)

        # Verify user cannot see other users' hidden issues
        self.assertNotIn(self.other_hidden_issue.id, visible_ids)

        # Verify no error message for verified users
        messages = list(response.context["messages"]) if "messages" in response.context else []
        self.assertEqual(len(messages), 0)

    def test_bugs_list_unverified_user(self):
        """Test bugs_list page for unverified users"""
        self.client.login(username="unverified_user", password="testpass123")
        url = reverse("issues")
        response = self.client.get(url)

        # Check response basics
        self.assertEqual(response.status_code, 200)

        # Verify unverified user gets verification message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn("Please verify your email address", str(messages[0]))

        # Verify user can see their own hidden issues
        bugs = list(response.context["bugs"])
        visible_ids = [bug.id for bug in bugs]
        self.assertIn(self.visible_issue.id, visible_ids)
        self.assertIn(self.other_hidden_issue.id, visible_ids)

        # Verify user cannot see other users' hidden issues
        self.assertNotIn(self.hidden_issue.id, visible_ids)

    def test_bugs_list_pagination(self):
        """Test pagination on bugs_list page"""
        # Create 20 more issues to test pagination
        for i in range(20):
            Issue.objects.create(
                url=f"http://example.com/issue{i}",
                description=f"Test Issue {i}",
                user=self.verified_user,
                is_hidden=False,
            )

        url = reverse("issues")
        response = self.client.get(url)

        # Check that pagination is working
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["bugs"]), 15)  # Default page size is 15

        # Check second page
        response = self.client.get(f"{url}?page=2")
        self.assertEqual(response.status_code, 200)
        # We should have 21 issues total (20 new + 1 visible from setup)
        # So page 2 should have 21 - 15 = 6 issues
        self.assertEqual(len(response.context["bugs"]), 6)
