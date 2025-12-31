from datetime import date

import pytest

from website.models import Contributor, ContributorStats, OrganisationType, Organization
from website.services.team_weekly_stats import get_weekly_team_stats


@pytest.mark.django_db
def test_no_teams_returns_empty_list():
    result = get_weekly_team_stats(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 7),
    )
    assert result == []


@pytest.mark.django_db
def test_team_with_no_stats_returns_zeros():
    team = Organization.objects.create(
        name="Test Team",
        type=OrganisationType.TEAM.value,
        url="https://example.com/test-team",
    )

    result = get_weekly_team_stats(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 7),
    )

    assert result[0]["stats"]["commits"] == 0
    assert result[0]["stats"]["issues_opened"] == 0


@pytest.mark.django_db
def test_single_team_with_stats():
    # Create a TEAM
    team = Organization.objects.create(
        name="Team A",
        type=OrganisationType.TEAM.value,
        url="https://example.com/test-team",
    )

    # Create a repo under the team
    from website.models import Repo

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
        contributions=0,  # default to 0
    )

    # Add contributor stats for that repo
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

    # Call the service
    result = get_weekly_team_stats(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 7),
    )

    # Assert stats are correctly aggregated
    assert result[0]["stats"]["commits"] == 5
    assert result[0]["stats"]["issues_opened"] == 2
    assert result[0]["stats"]["issues_closed"] == 1
    assert result[0]["stats"]["pull_requests"] == 1
    assert result[0]["stats"]["comments"] == 3
