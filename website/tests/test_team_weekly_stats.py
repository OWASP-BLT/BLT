from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from website.models import Contributor, ContributorStats, OrganisationType, Organization, Repo
from website.services.team_weekly_stats import get_weekly_team_stats


class TestWeeklyTeamStats(TestCase):
    def test_invalid_date_range_raises_error(self):
        with self.assertRaises(ValidationError):
            get_weekly_team_stats(
                start_date=date(2024, 5, 10),
                end_date=date(2024, 5, 1),
            )

    def test_no_teams_returns_empty_list(self):
        result = get_weekly_team_stats(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
        )
        self.assertEqual(result, [])

    def test_team_with_no_stats_returns_zeros(self):
        team = Organization.objects.create(
            name="Test Team",
            type=OrganisationType.TEAM.value,
            url="https://example.com/test-team",
        )

        result = get_weekly_team_stats(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
        )

        self.assertEqual(len(result), 1)
        team_result = result[0]

        self.assertEqual(team_result["team_id"], team.id)
        self.assertEqual(team_result["team_name"], "Test Team")
        self.assertEqual(
            team_result["stats"],
            {
                "commits": 0,
                "issues_opened": 0,
                "issues_closed": 0,
                "pull_requests": 0,
                "comments": 0,
            },
        )

    def test_single_team_with_stats(self):
        team = Organization.objects.create(
            name="Team A",
            type=OrganisationType.TEAM.value,
            url="https://example.com/test-team",
        )

        repo = Repo.objects.create(
            name="test-repo",
            organization=team,
            repo_url="https://github.com/example/test-repo",
        )

        contributor = Contributor.objects.create(
            name="Test User",
            github_id=12345,
            github_url="https://github.com/test-user",
            avatar_url="https://avatars.githubusercontent.com/u/12345",
            contributor_type="INDIVIDUAL",
            contributions=0,
        )

        ContributorStats.objects.create(
            repo=repo,
            contributor=contributor,
            granularity="day",
            date=date(2025, 1, 3),
            commits=5,
            issues_opened=2,
            issues_closed=1,
            pull_requests=1,
            comments=3,
        )
        result = get_weekly_team_stats(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
        )

        self.assertEqual(len(result), 1)

        team_result = result[0]

        self.assertEqual(team_result["team_id"], team.id)
        self.assertEqual(team_result["team_name"], "Team A")
        self.assertEqual(team_result["start_date"], date(2025, 1, 1))
        self.assertEqual(team_result["end_date"], date(2025, 1, 7))

        self.assertEqual(
            team_result["stats"],
            {
                "commits": 5,
                "issues_opened": 2,
                "issues_closed": 1,
                "pull_requests": 1,
                "comments": 3,
            },
        )
