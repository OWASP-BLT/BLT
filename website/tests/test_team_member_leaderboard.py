from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from website.models import Organization


class TeamMemberLeaderboardViewTest(TestCase):
    """Tests for the Django web leaderboard page"""

    def setUp(self):
        self.client = Client()

        # Create team
        self.team = Organization.objects.create(name="TestOrg")

        # Users
        self.user1 = User.objects.create_user("u1", "u1@example.com", "pass")
        self.user2 = User.objects.create_user("u2", "u2@example.com", "pass")
        self.user3 = User.objects.create_user("u3", "u3@example.com", "pass")

        # Attach team
        self.user1.userprofile.team = self.team
        self.user2.userprofile.team = self.team
        self.user3.userprofile.team = self.team

        # Add scores
        self.user1.userprofile.leaderboard_score = Decimal("95.00")
        self.user2.userprofile.leaderboard_score = Decimal("80.00")
        self.user3.userprofile.leaderboard_score = Decimal("65.00")

        self.user1.userprofile.save()
        self.user2.userprofile.save()
        self.user3.userprofile.save()

    def test_leaderboard_requires_login(self):
        url = reverse("team_member_leaderboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_leaderboard_renders_correctly(self):
        self.client.login(username="u1", password="pass")
        url = reverse("team_member_leaderboard")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Ranked order → u1, u2, u3
        ranked = response.context["ranked_members"]

        self.assertEqual(ranked[0]["profile"], self.user1.userprofile)
        self.assertEqual(ranked[1]["profile"], self.user2.userprofile)
        self.assertEqual(ranked[2]["profile"], self.user3.userprofile)

    def test_user_with_no_team_sees_empty_list(self):
        user = User.objects.create_user("lonely", "l@example.com", "pass")
        self.client.login(username="lonely", password="pass")

        url = reverse("team_member_leaderboard")
        response = self.client.get(url)

        self.assertEqual(len(response.context["members"]), 0)


class TeamMemberLeaderboardAPITest(TestCase):
    """Tests for the DRF JSON leaderboard API"""

    def setUp(self):
        self.client = APIClient()

        # Create team
        self.team = Organization.objects.create(name="TestAPIOrg")

        # Users
        self.user = User.objects.create_user("apiuser", "api@example.com", "pass")
        self.user.userprofile.team = self.team
        self.user.userprofile.save()

        self.m1 = User.objects.create_user("m1", "m1@example.com", "pass")
        self.m2 = User.objects.create_user("m2", "m2@example.com", "pass")

        self.m1.userprofile.team = self.team
        self.m2.userprofile.team = self.team

        self.m1.userprofile.leaderboard_score = Decimal("90.00")
        self.m2.userprofile.leaderboard_score = Decimal("70.00")

        self.m1.userprofile.save()
        self.m2.userprofile.save()

    def test_api_requires_auth(self):
        url = reverse("api_team_leaderboard")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 401)

    def test_api_returns_ranked_data(self):
        self.client.login(username="apiuser", password="pass")

        url = reverse("api_team_leaderboard")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Validate new structured response
        self.assertIn("results", data)
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["results"]), 3)

        results = data["results"]

        # Verify ordering by score: m1 (90), m2 (70), apiuser (default)
        self.assertEqual(results[0]["username"], "m1")
        self.assertEqual(results[1]["username"], "m2")
        self.assertEqual(results[2]["username"], "apiuser")

    def test_api_no_team(self):
        lonely = User.objects.create_user("lonely", "l@example.com", "pass")
        self.client.login(username="lonely", password="pass")

        url = reverse("api_team_leaderboard")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "User has no team")
