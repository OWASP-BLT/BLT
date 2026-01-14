from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Badge
from website.models import Organization as Team
from website.models import TeamBadge


class TeamBadgeModelTests(TestCase):
    """Tests for TeamBadge model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpass123"
        )

        self.team = Team.objects.create(
            name="Test Team",
            description="A test team",
            created=self.user
        )

        self.badge = Badge.objects.create(
            title="Bug Hunter",
            description="Found 10 bugs",
            type="automatic",
            scope="team"
        )

    def test_team_badge_creation(self):
        team_badge = TeamBadge.objects.create(
            team=self.team,
            badge=self.badge
        )

        self.assertIsNotNone(team_badge.id)
        self.assertEqual(team_badge.team, self.team)
        self.assertEqual(team_badge.badge, self.badge)

    def test_team_badge_unique_constraint(self):
        TeamBadge.objects.create(team=self.team, badge=self.badge)

        with self.assertRaises(Exception):
            TeamBadge.objects.create(team=self.team, badge=self.badge)


class TeamBadgeAssignmentTests(TestCase):
    """Tests for assigning badges to teams"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="testpass123"
        )

        self.team = Team.objects.create(
            name="Development Team",
            description="Core development team",
            created=self.user
        )

        self.badge1 = Badge.objects.create(
            title="First Bug Found",
            description="First bug reported",
            type="automatic"
        )

        self.badge2 = Badge.objects.create(
            title="Team Leader",
            description="Team leadership badge",
            type="manual",
            scope="topuser_team"
        )

    def test_assign_multiple_badges_to_team(self):
        TeamBadge.objects.create(team=self.team, badge=self.badge1)
        TeamBadge.objects.create(team=self.team, badge=self.badge2)

        self.assertEqual(
            TeamBadge.objects.filter(team=self.team).count(), 2
        )


class TeamBadgeViewTests(TestCase):
    """Basic view test to ensure badges render"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpass123"
        )

        self.team = Team.objects.create(
            name="Test Team",
            description="Test team description",
            created=self.user
        )

        self.badge = Badge.objects.create(
            title="Test Badge",
            description="Test badge description",
            type="automatic",
            scope="team"
        )

        TeamBadge.objects.create(team=self.team, badge=self.badge)

    def test_team_badges_list_view(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("team_badges"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.badge.title)
