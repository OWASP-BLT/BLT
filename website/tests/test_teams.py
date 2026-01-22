from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Team


class TeamMemberLeaderboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.team = Team.objects.create(name="Test Team")
        self.user.userprofile.team = self.team
        self.user.userprofile.leaderboard_score = 100
        self.user.userprofile.save()

    def test_leaderboard_requires_login_and_orders_correctly(self):
        """Test view requires auth and orders by score/streak"""
        # Unauthenticated access
        response = self.client.get(reverse("team_member_leaderboard"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

        # Create team members with different scores
        user2 = User.objects.create_user(username="user2", password="test")
        user2.userprofile.team = self.team
        user2.userprofile.leaderboard_score = 150
        user2.userprofile.save()

        # Authenticated access
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("team_member_leaderboard"))

        self.assertEqual(response.status_code, 200)
        members = list(response.context["members"])
        # Higher score should be first
        self.assertEqual(members[0].user.username, "user2")
